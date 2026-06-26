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
Mamdani). São fornecidas 20 regras (o enunciado pede no mínimo 15).

**Princípio de projeto — o número é decisivo.** Dois imóveis na mesma rua com
números diferentes são endereços diferentes. Por isso as classes altas
(`alta`, `muito_alta`) só são alcançadas quando o número é `igual`; um número
`proximo` ou `diferente` limita o resultado a `media` ou menos, mesmo que rua,
cidade e CEP coincidam.
"""

from __future__ import annotations

import skfuzzy.control as ctrl

# ---------------------------------------------------------------------------
# Base de conhecimento: 20 regras fuzzy.
# Variáveis de entrada: street, number, city, cep
# Variável de saída:    final
# ---------------------------------------------------------------------------
RULE_DEFS: list[dict] = [
    # --- muito_alta: exige número IGUAL + forte corroboração -------------
    {"if": {"street": "alta", "number": "igual", "cep": "igual"}, "then": "muito_alta",
     "desc": "rua, número e CEP coincidem"},
    {"if": {"street": "alta", "number": "igual", "city": "alta"}, "then": "muito_alta",
     "desc": "rua, número e cidade coincidem"},
    {"if": {"cep": "igual", "number": "igual", "city": "alta"}, "then": "muito_alta",
     "desc": "CEP, número e cidade coincidem"},

    # --- alta: número IGUAL + bom casamento ------------------------------
    {"if": {"street": "alta", "number": "igual"}, "then": "alta",
     "desc": "rua muito parecida e número idêntico"},
    {"if": {"street": "alta", "number": "igual", "cep": "parcial"}, "then": "alta",
     "desc": "rua e número coincidem, CEP parcialmente igual"},
    {"if": {"street": "media", "number": "igual", "city": "alta"}, "then": "alta",
     "desc": "rua razoável, número idêntico e cidade coincide"},

    # --- media: número NÃO idêntico limita o resultado -------------------
    {"if": {"street": "alta", "number": "proximo"}, "then": "media",
     "desc": "rua muito parecida, mas número apenas próximo"},
    {"if": {"street": "alta", "number": "diferente"}, "then": "media",
     "desc": "rua coincide, mas o número é diferente (outro imóvel)"},
    {"if": {"street": "alta", "city": "alta", "number": "diferente"}, "then": "media",
     "desc": "rua e cidade coincidem, mas o número é diferente"},
    {"if": {"cep": "igual", "number": "diferente"}, "then": "media",
     "desc": "mesmo CEP, mas número diferente (mesma via, outro imóvel)"},
    {"if": {"number": "proximo", "city": "alta"}, "then": "media",
     "desc": "número próximo e cidade coincide"},
    {"if": {"street": "media", "number": "proximo"}, "then": "media",
     "desc": "rua razoável e número próximo"},

    # --- baixa -----------------------------------------------------------
    {"if": {"street": "baixa"}, "then": "baixa",
     "desc": "nome de rua pouco parecido"},
    {"if": {"street": "media", "city": "baixa"}, "then": "baixa",
     "desc": "rua razoável, mas cidade diferente"},
    {"if": {"number": "diferente", "street": "media"}, "then": "baixa",
     "desc": "número diferente e rua apenas razoável"},
    {"if": {"cep": "diferente", "street": "media"}, "then": "baixa",
     "desc": "CEP diferente e rua apenas razoável"},
    {"if": {"street": "baixa", "number": "igual"}, "then": "baixa",
     "desc": "número igual, mas rua diferente (provável coincidência)"},

    # --- muito_baixa -----------------------------------------------------
    {"if": {"street": "baixa", "city": "baixa"}, "then": "muito_baixa",
     "desc": "rua e cidade ambas diferentes"},
    {"if": {"street": "baixa", "cep": "diferente"}, "then": "muito_baixa",
     "desc": "rua diferente e CEP diferente"},
    {"if": {"street": "baixa", "number": "diferente", "cep": "diferente"},
     "then": "muito_baixa",
     "desc": "rua, número e CEP todos diferentes"},
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
