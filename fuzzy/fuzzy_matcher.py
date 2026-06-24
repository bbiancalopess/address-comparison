import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from fuzzy.models import SimilarityFeatures


class FuzzyAddressMatcher:

    def __init__(self):
        # ==============
        # ENTRADAS
        # ==============

        self.street = ctrl.Antecedent(
            np.arange(0, 1.01, 0.01),
            "street"
        )

        self.number = ctrl.Antecedent(
            np.arange(0, 1.01, 0.01),
            "number"
        )

        self.neighborhood = ctrl.Antecedent(
            np.arange(0, 1.01, 0.01),
            "neighborhood"
        )

        self.city = ctrl.Antecedent(
            np.arange(0, 1.01, 0.01),
            "city"
        )

        self.state = ctrl.Antecedent(
            np.arange(0, 1.01, 0.01),
            "state"
        )

        self.zip_code = ctrl.Antecedent(
            np.arange(0, 1.01, 0.01),
            "zip_code"
        )

        # ======================
        # Saída
        # ======================

        self.match = ctrl.Consequent(
            np.arange(0, 101, 1),
            "match"
        )

        self._build_membership_functions()
        self._build_rules()

    def _build_membership_functions(self):
        inputs = [
            self.street,
            self.number,
            self.neighborhood,
            self.city,
            self.state,
            self.zip_code
        ]

        for variable in inputs:
            variable["low"] = fuzz.trimf(variable.universe, [0, 0, 0.5])
            variable["medium"] = fuzz.trimf(variable.universe, [0.25, 0.5, 0.75])
            variable["high"] = fuzz.trimf(variable.universe, [0.5, 1, 1])
        
        self.match["no_match"] = fuzz.trimf(self.match.universe, [0, 0, 40])
        self.match["possible_match"] = fuzz.trimf(self.match.universe, [20, 50, 80])
        self.match["strong_match"] = fuzz.trimf(self.match.universe, [60, 100, 100])
    
    def _build_rules(self):
        rules = [

            # Regra 1
            ctrl.Rule(
                self.street["high"]
                & self.number["high"]
                & self.zip_code["high"],
                self.match["strong_match"]
            ),

            # Regra 2
            ctrl.Rule(
                self.street["high"]
                & self.city["high"]
                & self.state["high"],
                self.match["strong_match"]
            ),

            # Regra 3
            ctrl.Rule(
                self.street["high"]
                & self.neighborhood["high"],
                self.match["strong_match"]
            ),

            # Regra 4
            ctrl.Rule(
                self.street["medium"]
                & self.number["high"],
                self.match["possible_match"]
            ),

            # Regra 5
            ctrl.Rule(
                self.street["medium"]
                & self.city["high"],
                self.match["possible_match"]
            ),

            # Regra 6
            ctrl.Rule(
                self.street["low"],
                self.match["no_match"]
            ),

            # Regra 7
            ctrl.Rule(
                self.city["low"]
                & self.zip_code["low"],
                self.match["no_match"]
            ),

            # Regra 8
            ctrl.Rule(
                self.number["low"]
                & self.street["medium"],
                self.match["possible_match"]
            ),

            # Regra 9
            ctrl.Rule(
                self.street["high"]
                & self.number["medium"]
                & self.city["high"],
                self.match["strong_match"]
            ),

            # Regra 10
            ctrl.Rule(
                self.street["high"]
                & self.number["high"]
                & self.neighborhood["high"]
                & self.city["high"],
                self.match["strong_match"]
            )
        ]

        self.control_system = ctrl.ControlSystem(rules)
    
    def match_addresses(self, features: SimilarityFeatures) -> float:
        simulation = ctrl.ControlSystemSimulation(self.control_system)

        simulation.input["street"] = features.street_name
        simulation.input["number"] = features.number
        simulation.input["neighborhood"] = features.neighborhood
        simulation.input["city"] = features.city
        simulation.input["state"] = features.state
        simulation.input["zip_code"] = features.zip_code

        simulation.compute()

        return float(simulation.output["match"])

    def classify(self, score: float) -> str:
        if score >= 70:
            return "MATCH"
        
        if score >= 40:
            return "POSSIBLE_MATCH"
        
        return "NO_MATCH"