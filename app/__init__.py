"""Fuzzy Address Matcher.

Pacote que implementa um comparador inteligente de endereços usando
Sistemas Nebulosos (Fuzzy Logic).

Fluxo geral (pipeline):

    texto -> normalizer -> parser -> similarity -> fuzzy_engine -> explainability

Cada módulo é independente e didático, para apresentação acadêmica.
"""

from app.parser import AddressComponents, parse_address
from app.normalizer import normalize
from app.similarity import field_similarities
from app.fuzzy_engine import FuzzyAddressEngine
from app.explainability import build_explanation
from app.main import compare_addresses, ComparisonResult

__all__ = [
    "AddressComponents",
    "parse_address",
    "normalize",
    "field_similarities",
    "FuzzyAddressEngine",
    "build_explanation",
    "compare_addresses",
    "ComparisonResult",
]
