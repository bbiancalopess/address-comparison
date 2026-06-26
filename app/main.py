"""Orquestração do pipeline completo de comparação de endereços.

Une todos os módulos:

    normalizer -> parser -> similarity -> fuzzy_engine -> explainability

Expõe a função de alto nível :func:`compare_addresses` e uma demonstração
de linha de comando (CLI) executável com ``python app/main.py``.
"""

from __future__ import annotations

import os
import sys

# Permite executar como script (`python app/main.py`), garantindo que a raiz
# do projeto esteja em sys.path para que `import app...` funcione.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from functools import lru_cache

from app.explainability import build_explanation, classify
from app.fuzzy_engine import FuzzyAddressEngine
from app.parser import AddressComponents, parse_address
from app.similarity import FieldSimilarities, field_similarities


@dataclass
class ComparisonResult:
    """Resultado completo da comparação de dois endereços."""

    score: float
    classification: str
    details: dict
    explanation: str
    components_1: AddressComponents = field(default=None)
    components_2: AddressComponents = field(default=None)
    active_rules: list = field(default_factory=list)
    memberships: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "classification": self.classification,
            "details": self.details,
            "explanation": self.explanation,
        }


@lru_cache(maxsize=1)
def get_engine() -> FuzzyAddressEngine:
    """Cria (uma única vez) o motor fuzzy — sua construção é custosa."""
    return FuzzyAddressEngine()


def compare_addresses(address1: str, address2: str) -> ComparisonResult:
    """Compara dois endereços em texto e retorna o resultado completo."""
    c1 = parse_address(address1)
    c2 = parse_address(address2)

    sims: FieldSimilarities = field_similarities(c1, c2)

    fuzzy = get_engine().infer(
        street=sims.street,
        number=sims.number,
        city=sims.city,
        cep=sims.zip_code,
    )

    explanation = build_explanation(fuzzy.score, sims, fuzzy)

    return ComparisonResult(
        score=fuzzy.score,
        classification=classify(fuzzy.score),
        details=sims.as_dict(),
        explanation=explanation,
        components_1=c1,
        components_2=c2,
        active_rules=fuzzy.active_rules,
        memberships=fuzzy.memberships,
    )


def main(argv: list[str] | None = None) -> None:
    """CLI: ``python app/main.py "<end1>" "<end2>"`` ou demo sem argumentos."""
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) >= 2:
        res = compare_addresses(argv[0], argv[1])
        print(f"Score: {res.score}")
        print(f"Classificação: {res.classification}")
        print(f"Detalhes: {res.details}\n")
        print(res.explanation)
    else:
        print("Argumentos são obrigatórios: <endereço1> <endereço2>")


if __name__ == "__main__":
    main()
