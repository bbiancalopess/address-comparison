"""Base de regras fuzzy (Mamdani) do comparador de endereços.

As regras são definidas como **dados** (lista de dicionários) em vez de
código imperativo. Isso traz duas vantagens didáticas:

    1. A mesma definição gera as `ctrl.Rule` do scikit-fuzzy E permite
       calcular manualmente a "força de disparo" de cada regra para a
       explicabilidade ("quais regras foram ativadas").
    2. Fica fácil ler, auditar e estender a base de conhecimento.

Cada regra tem o formato:

    {"if": {<variavel>: <termo>, ...}, "then": <termo_saida>, "desc": "..."}

O antecedente combina as condições com o operador E (AND = mínimo, padrão
Mamdani). São fornecidas 22 regras (o enunciado pede no mínimo 15).
"""

from __future__ import annotations

import skfuzzy.control as ctrl

# ---------------------------------------------------------------------------
# Base de conhecimento: 22 regras fuzzy.
# Variáveis de entrada: street, number, city, cep
# Variável de saída:    final
# ---------------------------------------------------------------------------
RULE_DEFS: list[dict] = [
    # --- regras "fortes" de igualdade ------------------------------------
    {"if": {"street": "alta", "number": "igual"}, "then": "muito_alta",
     "desc": "rua muito parecida e número idêntico"},
    {"if": {"cep": "igual"}, "then": "muito_alta",
     "desc": "CEP idêntico"},
    {"if": {"street": "alta", "cep": "igual"}, "then": "muito_alta",
     "desc": "rua muito parecida e CEP idêntico"},
    {"if": {"street": "alta", "city": "alta", "number": "igual"}, "then": "muito_alta",
     "desc": "rua, cidade e número coincidem"},

    # --- regras de alta similaridade -------------------------------------
    {"if": {"street": "alta", "city": "alta"}, "then": "alta",
     "desc": "rua muito parecida e cidade coincide"},
    {"if": {"street": "alta", "number": "proximo"}, "then": "alta",
     "desc": "rua muito parecida e número próximo"},
    {"if": {"street": "alta", "cep": "parcial"}, "then": "alta",
     "desc": "rua muito parecida e CEP parcialmente igual"},
    {"if": {"cep": "parcial", "city": "alta"}, "then": "alta",
     "desc": "CEP parcial e cidade coincide"},
    {"if": {"street": "media", "number": "igual", "city": "alta"}, "then": "alta",
     "desc": "rua razoável, número idêntico e cidade coincide"},

    # --- regras de média similaridade ------------------------------------
    {"if": {"street": "media", "city": "alta"}, "then": "media",
     "desc": "rua razoável e cidade coincide"},
    {"if": {"street": "media", "number": "proximo"}, "then": "media",
     "desc": "rua razoável e número próximo"},
    {"if": {"number": "diferente", "street": "media"}, "then": "media",
     "desc": "número diferente mas rua razoável"},
    {"if": {"street": "alta", "number": "diferente"}, "then": "media",
     "desc": "rua muito parecida mas número diferente"},
    {"if": {"street": "alta", "city": "alta", "number": "diferente"}, "then": "media",
     "desc": "rua e cidade coincidem, mas o número é diferente"},
    {"if": {"street": "alta", "city": "baixa"}, "then": "media",
     "desc": "rua parecida mas cidade diferente"},
    {"if": {"cep": "parcial", "street": "media"}, "then": "media",
     "desc": "CEP parcial e rua razoável"},

    # --- regras de baixa similaridade ------------------------------------
    {"if": {"street": "baixa"}, "then": "baixa",
     "desc": "nome de rua pouco parecido"},
    {"if": {"street": "media", "city": "baixa"}, "then": "baixa",
     "desc": "rua razoável mas cidade diferente"},
    {"if": {"street": "baixa", "number": "igual"}, "then": "baixa",
     "desc": "número igual mas rua diferente (provável coincidência)"},
    {"if": {"cep": "diferente", "street": "media"}, "then": "baixa",
     "desc": "CEP diferente e rua apenas razoável"},

    # --- regras de similaridade muito baixa ------------------------------
    {"if": {"street": "baixa", "city": "baixa"}, "then": "muito_baixa",
     "desc": "rua e cidade ambas diferentes"},
    {"if": {"street": "baixa", "cep": "diferente", "number": "diferente"},
     "then": "muito_baixa",
     "desc": "rua, CEP e número todos diferentes"},
]


def build_rules(variables: dict) -> list[ctrl.Rule]:
    """Constrói as `ctrl.Rule` do scikit-fuzzy a partir de :data:`RULE_DEFS`.

    `variables` mapeia o nome de cada variável para o objeto
    Antecedent/Consequent correspondente, ex.::

        {"street": street_antecedent, ..., "final": final_consequent}
    """
    rules: list[ctrl.Rule] = []
    final = variables["final"]
    for rule_def in RULE_DEFS:
        antecedent = None
        for var_name, term in rule_def["if"].items():
            condition = variables[var_name][term]
            antecedent = condition if antecedent is None else (antecedent & condition)
        consequent = final[rule_def["then"]]
        rules.append(ctrl.Rule(antecedent, consequent, label=rule_def["desc"]))
    return rules
