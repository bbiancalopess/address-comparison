"""Similaridade campo a campo usando RapidFuzz.

Para cada componente do endereço calculamos uma similaridade em [0, 100].
Combinamos diferentes métricas do RapidFuzz porque cada uma captura um tipo
de variação:

    * ratio            -> distância de edição (Levenshtein normalizada)
    * token_sort_ratio -> robusto a ordem das palavras ("bahia rua" ~ "rua bahia")
    * partial_ratio    -> robusto a substrings ("paulista" em "av paulista")

O número e o CEP têm tratamento próprio (comparação dígito a dígito / prefixo),
pois para eles a noção de "parecido" é diferente de texto livre.
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.parser import AddressComponents


@dataclass
class FieldSimilarities:
    """Similaridades individuais por campo (0–100)."""

    street: float = 0.0
    number: float = 0.0
    district: float = 0.0
    city: float = 0.0
    state: float = 0.0
    zip_code: float = 0.0

    def as_dict(self) -> dict:
        return {
            "street_similarity": round(self.street, 1),
            "number_similarity": round(self.number, 1),
            "district_similarity": round(self.district, 1),
            "city_similarity": round(self.city, 1),
            "state_similarity": round(self.state, 1),
            "zip_similarity": round(self.zip_code, 1),
        }


def _text_similarity(a: str, b: str) -> float:
    """Combina métricas do RapidFuzz para texto livre.

    Usa a média ponderada de ratio, token_sort_ratio e partial_ratio,
    favorecendo token_sort_ratio (boa para nomes de rua/cidade).
    """
    a = (a or "").strip()
    b = (b or "").strip()
    if not a and not b:
        return 100.0  # ambos ausentes: considerados equivalentes
    if not a or not b:
        return 0.0

    r = fuzz.ratio(a, b)
    ts = fuzz.token_sort_ratio(a, b)
    pr = fuzz.partial_ratio(a, b)
    return 0.3 * r + 0.5 * ts + 0.2 * pr


def _number_similarity(a: str, b: str) -> float:
    """Similaridade de números de logradouro.

    O número da casa é **decisivo** na identidade de um endereço: dois imóveis
    na mesma rua com números diferentes são lugares diferentes. Por isso a
    similaridade é praticamente binária:

    * iguais (ou ambos "S/N", ausentes) -> 100  (faixa "igual")
    * um ausente                        -> 50   (incerteza, faixa "próximo")
    * diferentes                        -> decai rápido a partir de ~60, de
                                           modo que QUALQUER diferença caia fora
                                           da faixa "igual" (>=70). Off-by-1 fica
                                           em "próximo" (~60); diferenças maiores
                                           caem em "diferente".
    """
    a = (a or "").strip()
    b = (b or "").strip()
    if not a and not b:
        return 100.0
    if not a or not b:
        return 50.0
    if a == b:
        return 100.0

    da = "".join(ch for ch in a if ch.isdigit())
    db = "".join(ch for ch in b if ch.isdigit())
    if da and db:
        diff = abs(int(da) - int(db))
        if diff == 0:
            return 100.0
        # off-by-1 -> 60 ("próximo"); decai até ~0 em diff>=10. Nunca >=70,
        # então um número diferente jamais é tratado como "igual".
        return max(0.0, 60.0 * (1.0 - (diff - 1) / 9.0))
    # números com letras (ex.: "12a"): similaridade textual, mas limitada à
    # faixa "diferente/próximo" para não simular igualdade.
    return min(45.0, float(fuzz.ratio(a, b)))


def _zip_similarity(a: str, b: str) -> float:
    """Similaridade de CEP por prefixo compartilhado.

    O CEP brasileiro é hierárquico (região/sub-região/setor...). Quanto maior
    o prefixo comum, mais próximos geograficamente. 8 dígitos iguais -> 100.
    """
    a = "".join(ch for ch in (a or "") if ch.isdigit())
    b = "".join(ch for ch in (b or "") if ch.isdigit())
    if not a or not b:
        # CEP ausente (em um ou ambos) é NEUTRO, não um forte indício de
        # igualdade: evita que "cep igual" domine quando não há informação.
        return 50.0
    if a == b:
        return 100.0

    common = 0
    for ca, cb in zip(a, b):
        if ca == cb:
            common += 1
        else:
            break
    return 100.0 * common / 8.0


def field_similarities(c1: AddressComponents, c2: AddressComponents) -> FieldSimilarities:
    """Calcula a similaridade de cada campo entre dois endereços parseados."""
    # Rua: combina tipo + nome para não penalizar "av" vs "avenida".
    street_a = f"{c1.street_type} {c1.street_name}".strip()
    street_b = f"{c2.street_type} {c2.street_name}".strip()

    return FieldSimilarities(
        street=_text_similarity(street_a, street_b),
        number=_number_similarity(c1.number, c2.number),
        district=_text_similarity(c1.district, c2.district),
        city=_text_similarity(c1.city, c2.city),
        state=_text_similarity(c1.state, c2.state),
        zip_code=_zip_similarity(c1.zip_code, c2.zip_code),
    )


if __name__ == "__main__":
    from app.parser import parse_address

    a = parse_address("Av Afonso Pena 1000 Centro Belo Horizonte MG")
    b = parse_address("Avenida Afonso Pena, 1000, Centro, BH - MG")
    print(field_similarities(a, b).as_dict())
