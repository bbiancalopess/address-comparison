"""Motor de inferência fuzzy (Mamdani + defuzzificação por centroide).

Este módulo encapsula o Sistema Nebuloso propriamente dito, construído com
scikit-fuzzy. Ele recebe as similaridades por campo (0–100) e produz um
score final de similaridade (0–100).

Variáveis de entrada (Antecedents):
    * street  -> baixa | media | alta
    * number  -> diferente | proximo | igual
    * city    -> baixa | alta
    * cep     -> diferente | parcial | igual

Variável de saída (Consequent):
    * final   -> muito_baixa | baixa | media | alta | muito_alta

Inferência: Mamdani (AND = mínimo, implicação = mínimo, agregação = máximo).
Defuzzificação: centroide.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import skfuzzy as fuzz
import skfuzzy.control as ctrl

from app.rules import RULE_DEFS, build_rules

# Universo de discurso comum a todas as variáveis: 0..100.
UNIVERSE = np.arange(0, 101, 1)


@dataclass
class FuzzyResult:
    """Resultado completo de uma inferência fuzzy."""

    score: float
    # grau de pertinência de cada termo de entrada (para explicação/gráficos)
    memberships: dict
    # regras com força de disparo > 0, ordenadas da mais forte para a mais fraca
    active_rules: list


class FuzzyAddressEngine:
    """Sistema de controle fuzzy para similaridade de endereços."""

    def __init__(self) -> None:
        self._build_variables()
        self._rules = build_rules(self._variables)
        self._system = ctrl.ControlSystem(self._rules)
        # Calibração: por causa da sobreposição das funções de pertinência e da
        # defuzzificação por centroide, o score "cru" satura por volta de ~80
        # (entrada perfeita) e ~16 (entrada nula). Guardamos esses extremos para
        # reescalar o score cru para a faixa intuitiva 0–100 (min-max).
        self._raw_min = self._raw_infer(0, 0, 0, 0)
        self._raw_max = self._raw_infer(100, 100, 100, 100)

    # ------------------------------------------------------------------
    # Construção das variáveis e funções de pertinência
    # ------------------------------------------------------------------
    def _build_variables(self) -> None:
        street = ctrl.Antecedent(UNIVERSE, "street")
        number = ctrl.Antecedent(UNIVERSE, "number")
        city = ctrl.Antecedent(UNIVERSE, "city")
        cep = ctrl.Antecedent(UNIVERSE, "cep")
        final = ctrl.Consequent(UNIVERSE, "final")

        # --- Similaridade da rua ---------------------------------------
        street["baixa"] = fuzz.trimf(UNIVERSE, [0, 0, 50])
        street["media"] = fuzz.trimf(UNIVERSE, [25, 50, 75])
        street["alta"] = fuzz.trimf(UNIVERSE, [50, 100, 100])

        # --- Similaridade do número ------------------------------------
        number["diferente"] = fuzz.trimf(UNIVERSE, [0, 0, 50])
        number["proximo"] = fuzz.trimf(UNIVERSE, [30, 60, 90])
        number["igual"] = fuzz.trimf(UNIVERSE, [70, 100, 100])

        # --- Similaridade da cidade ------------------------------------
        city["baixa"] = fuzz.trimf(UNIVERSE, [0, 0, 60])
        city["alta"] = fuzz.trimf(UNIVERSE, [40, 100, 100])

        # --- Similaridade do CEP ---------------------------------------
        cep["diferente"] = fuzz.trimf(UNIVERSE, [0, 0, 50])
        cep["parcial"] = fuzz.trimf(UNIVERSE, [25, 50, 90])
        cep["igual"] = fuzz.trimf(UNIVERSE, [80, 100, 100])

        # --- Similaridade final (saída) --------------------------------
        final["muito_baixa"] = fuzz.trimf(UNIVERSE, [0, 0, 25])
        final["baixa"] = fuzz.trimf(UNIVERSE, [0, 25, 50])
        final["media"] = fuzz.trimf(UNIVERSE, [25, 50, 75])
        final["alta"] = fuzz.trimf(UNIVERSE, [50, 75, 100])
        final["muito_alta"] = fuzz.trimf(UNIVERSE, [75, 100, 100])

        # Defuzzificação por centroide (padrão Mamdani).
        final.defuzzify_method = "centroid"

        self.street = street
        self.number = number
        self.city = city
        self.cep = cep
        self.final = final
        self._variables = {
            "street": street,
            "number": number,
            "city": city,
            "cep": cep,
            "final": final,
        }

    # ------------------------------------------------------------------
    # Inferência
    # ------------------------------------------------------------------
    def _membership_degrees(self, var: ctrl.Antecedent, value: float) -> dict:
        """Grau de pertinência de `value` em cada termo de `var`."""
        return {
            term: float(fuzz.interp_membership(UNIVERSE, var[term].mf, value))
            for term in var.terms
        }

    def _active_rules(self, degrees: dict) -> list:
        """Calcula a força de disparo de cada regra (AND = mínimo).

        Retorna a lista de regras ativadas (força > 0), cada uma como dict
        com `desc`, `then` e `strength`, ordenada por força decrescente.
        """
        fired = []
        for rule_def in RULE_DEFS:
            strength = min(
                degrees[var_name][term]
                for var_name, term in rule_def["if"].items()
            )
            if strength > 1e-6:
                fired.append(
                    {
                        "desc": rule_def["desc"],
                        "then": rule_def["then"],
                        "strength": round(strength, 3),
                    }
                )
        fired.sort(key=lambda r: r["strength"], reverse=True)
        return fired

    def _raw_infer(self, street: float, number: float, city: float, cep: float) -> float:
        """Executa a inferência e devolve o score cru (sem calibração)."""
        sim = ctrl.ControlSystemSimulation(self._system)
        sim.input["street"] = float(np.clip(street, 0, 100))
        sim.input["number"] = float(np.clip(number, 0, 100))
        sim.input["city"] = float(np.clip(city, 0, 100))
        sim.input["cep"] = float(np.clip(cep, 0, 100))
        sim.compute()
        return float(sim.output["final"])

    def _calibrate(self, raw: float) -> float:
        """Reescala o score cru para 0–100 via min-max dos extremos."""
        span = self._raw_max - self._raw_min
        if span <= 0:
            return raw
        scaled = 100.0 * (raw - self._raw_min) / span
        return float(np.clip(scaled, 0, 100))

    def infer(
        self,
        *,
        street: float,
        number: float,
        city: float,
        cep: float,
    ) -> FuzzyResult:
        """Executa a inferência fuzzy e retorna o score final + diagnóstico."""
        raw = self._raw_infer(street, number, city, cep)
        score = self._calibrate(raw)

        degrees = {
            "street": self._membership_degrees(self.street, street),
            "number": self._membership_degrees(self.number, number),
            "city": self._membership_degrees(self.city, city),
            "cep": self._membership_degrees(self.cep, cep),
        }
        return FuzzyResult(
            score=round(score, 1),
            memberships=degrees,
            active_rules=self._active_rules(degrees),
        )


if __name__ == "__main__":
    engine = FuzzyAddressEngine()
    res = engine.infer(street=95, number=100, city=90, cep=50)
    print("score:", res.score)
    print("regras ativadas:")
    for r in res.active_rules:
        print(f"  [{r['strength']:.2f}] {r['desc']} -> {r['then']}")
