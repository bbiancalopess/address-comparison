"""Explicabilidade: gera uma justificativa textual do score fuzzy.

A explicação combina:
    * as similaridades por campo (ex.: "o nome da rua teve 94% de correspondência")
    * o termo de saída dominante (ex.: "alta")
    * as regras fuzzy que mais contribuíram (regras ativadas)
"""

from __future__ import annotations

from app.fuzzy_engine import FuzzyResult
from app.similarity import FieldSimilarities

# Faixas de score -> classificação textual exigida pelo enunciado.
CLASSIFICATION_BANDS = [
    (85, "provavelmente iguais"),
    (65, "muito semelhantes"),
    (40, "parecidos"),
    (0, "diferentes"),
]


def classify(score: float) -> str:
    """Mapeia um score (0–100) para a classificação textual."""
    for threshold, label in CLASSIFICATION_BANDS:
        if score >= threshold:
            return label
    return "diferentes"


def _field_phrases(sims: FieldSimilarities) -> list[str]:
    """Frases descritivas por campo, somente para os campos informativos."""
    phrases: list[str] = []

    s = sims.street
    if s >= 90:
        phrases.append(f"o nome da rua é praticamente idêntico ({s:.0f}%)")
    elif s >= 60:
        phrases.append(f"o nome da rua é parecido ({s:.0f}%)")
    else:
        phrases.append(f"o nome da rua difere ({s:.0f}%)")

    n = sims.number
    if n >= 99:
        phrases.append("o número é idêntico")
    elif n >= 60:
        phrases.append(f"o número é próximo ({n:.0f}%)")
    else:
        phrases.append(f"o número é diferente ({n:.0f}%)")

    if sims.city >= 80:
        phrases.append(f"a cidade coincide ({sims.city:.0f}%)")
    else:
        phrases.append(f"a cidade difere ({sims.city:.0f}%)")

    if sims.state >= 80:
        phrases.append("o estado coincide")

    z = sims.zip_code
    if z >= 99:
        phrases.append("o CEP é idêntico")
    elif z >= 50:
        phrases.append(f"o CEP é parcialmente correspondente ({z:.0f}%)")
    elif z > 0:
        phrases.append(f"o CEP difere ({z:.0f}%)")

    return phrases


def build_explanation(
    score: float,
    sims: FieldSimilarities,
    fuzzy: FuzzyResult,
    *,
    max_rules: int = 3,
) -> str:
    """Monta a explicação textual completa do resultado."""
    classification = classify(score)
    phrases = _field_phrases(sims)

    lines = [
        f'A similaridade final foi {score:.1f}/100, classificada como '
        f'"{classification}", porque:',
    ]
    lines += [f"  • {p}" for p in phrases]

    if fuzzy.active_rules:
        lines.append("")
        lines.append("Principais regras fuzzy ativadas:")
        for rule in fuzzy.active_rules[:max_rules]:
            lines.append(
                f"  • SE {rule['desc']} (força {rule['strength']:.2f}) "
                f"ENTÃO similaridade {rule['then']}"
            )

    return "\n".join(lines)
