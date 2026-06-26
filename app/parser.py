"""Parsing (decomposição) de endereços em componentes estruturados.

A partir de um texto livre, este módulo tenta extrair:

    street_type  -> tipo do logradouro (avenida, rua, ...)
    street_name  -> nome do logradouro (afonso pena)
    number       -> número (1000)
    district     -> bairro (centro)
    city         -> cidade (belo horizonte)
    state        -> sigla do estado (mg)
    zip_code     -> CEP (30130100)
    complement   -> complemento (apartamento 302)

A estratégia é **heurística** e combina regex + tokenização + uso de
vírgulas como delimitadores. Endereços brasileiros costumam separar os
campos por vírgula ("Rua X, 100, Bairro, Cidade - UF"); quando não há
vírgulas, o parser recorre a heurísticas posicionais e, por isso, pode ser
menos preciso. Isso é aceitável e esperado num projeto didático.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

from app.normalizer import ABBREVIATIONS

# Tipos de logradouro reconhecidos (forma canônica, expandida).
STREET_TYPES = {
    "avenida",
    "rua",
    "rodovia",
    "travessa",
    "alameda",
    "praca",
    "estrada",
    "largo",
    "viela",
    "via",
    "ladeira",
}

# Marcadores de complemento. Tokens a partir destes vão para `complement`.
COMPLEMENT_MARKERS = {
    "apartamento",
    "bloco",
    "conjunto",
    "quadra",
    "lote",
    "sala",
    "fundos",
    "casa",
    "andar",
    "km",
    "loja",
}

# As 27 unidades federativas.
UFS = {
    "ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mg", "ms",
    "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc",
    "se", "sp", "to",
}

# Nomes completos de estados -> sigla. Usados APENAS para reconhecer o estado
# no último segmento do endereço (não na normalização global, que corromperia
# nomes de ruas/cidades).
STATE_NAMES = {
    "acre": "ac", "alagoas": "al", "amapa": "ap", "amazonas": "am",
    "bahia": "ba", "ceara": "ce", "distrito federal": "df",
    "espirito santo": "es", "goias": "go", "maranhao": "ma",
    "minas gerais": "mg", "mato grosso do sul": "ms", "mato grosso": "mt",
    "para": "pa", "paraiba": "pb", "pernambuco": "pe", "piaui": "pi",
    "parana": "pr", "rio de janeiro": "rj", "rio grande do norte": "rn",
    "rondonia": "ro", "roraima": "rr", "rio grande do sul": "rs",
    "santa catarina": "sc", "sergipe": "se", "sao paulo": "sp",
    "tocantins": "to",
}


@dataclass
class AddressComponents:
    """Estrutura de um endereço decomposto."""

    street_type: str = ""
    street_name: str = ""
    number: str = ""
    district: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    complement: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers de pré-processamento (mantém vírgulas como delimitadores de campo)
# ---------------------------------------------------------------------------
def _strip_accents(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c))


def _preprocess(raw: str) -> str:
    """Lowercase + sem acentos + expansão de abreviações, preservando vírgulas.

    Diferente de `normalizer.normalize`, aqui as vírgulas (e o " - ") são
    mantidas/convertidas em vírgula para servirem de fronteira entre campos.
    """
    text = _strip_accents(raw.lower())

    # Expande nomes longos de estados ("minas gerais" -> "mg").
    for source, target in ABBREVIATIONS.items():
        if " " in source:
            text = re.sub(rf"\b{re.escape(source)}\b", target, text)

    text = text.replace(".", " ")
    text = re.sub(r"[;/]", ",", text)

    # " - " separando cidade/estado vira vírgula; hífen de CEP é preservado.
    text = re.sub(r"\s+-\s+", ",", text)

    # Remove caracteres especiais, exceto vírgula, hífen e #.
    text = re.sub(r"[^a-z0-9\s,#-]", " ", text)
    text = text.replace("#", " numero ")

    # Expande abreviações token a token (preservando vírgulas).
    def expand_segment(seg: str) -> str:
        toks = seg.split()
        return " ".join(ABBREVIATIONS.get(t, t) for t in toks)

    segments = [expand_segment(s) for s in text.split(",")]
    segments = [re.sub(r"\s+", " ", s).strip() for s in segments]
    return ", ".join(s for s in segments if s)


def _extract_zip(text: str) -> tuple[str, str]:
    """Extrai o CEP (8 dígitos, com ou sem hífen) e o remove do texto."""
    match = re.search(r"\b(\d{5})-?(\d{3})\b", text)
    if not match:
        return "", text
    zip_code = match.group(1) + match.group(2)
    text = (text[: match.start()] + " " + text[match.end():])
    text = re.sub(r"\bcep\b", " ", text)
    text = re.sub(r"\s+,", ",", text)
    return zip_code, re.sub(r"\s+", " ", text).strip()


def _extract_state(segments: list[str]) -> tuple[str, list[str]]:
    """Identifica o estado e o remove dos segmentos.

    Estratégia (do mais confiável ao menos):
        1. sigla de UF no fim de algum segmento ("... belo horizonte mg");
        2. um segmento cujo conteúdo é exatamente o nome de um estado
           ("minas gerais") — só vale se sobrar pelo menos a cidade, para não
           confundir cidade homônima (ex.: cidade "São Paulo" sem estado).
    """
    # 1) sigla de UF
    for idx in range(len(segments) - 1, -1, -1):
        toks = segments[idx].split()
        if toks and toks[-1] in UFS:
            state = toks[-1]
            rest = " ".join(toks[:-1]).strip()
            if rest:
                segments[idx] = rest
            else:
                segments.pop(idx)
            return state, segments

    # 2) nome completo do estado num segmento isolado
    if len(segments) >= 2:
        for idx in range(len(segments) - 1, -1, -1):
            if segments[idx] in STATE_NAMES:
                state = STATE_NAMES[segments[idx]]
                segments.pop(idx)
                return state, segments

    return "", segments


def _extract_number(segments: list[str]) -> tuple[str, list[str]]:
    """Extrai o número do logradouro.

    Procura o marcador 'numero' seguido de dígitos ou, na ausência dele, o
    primeiro token puramente numérico. O CEP já foi removido antes, então
    números soltos costumam ser o número da casa.
    """
    # 1) marcador explícito "numero 1000"
    for i, seg in enumerate(segments):
        m = re.search(r"\bnumero\s+(\d+[a-z]?)\b", seg)
        if m:
            segments[i] = re.sub(r"\bnumero\s+\d+[a-z]?\b", " ", seg).strip()
            return m.group(1), segments
        # "numero" perdido sem dígito: limpa
        if re.search(r"\bnumero\b", seg):
            segments[i] = re.sub(r"\bnumero\b", " ", seg).strip()

    # 2) primeiro token numérico isolado
    for i, seg in enumerate(segments):
        toks = seg.split()
        for j, tok in enumerate(toks):
            if re.fullmatch(r"\d+[a-z]?", tok):
                del toks[j]
                segments[i] = " ".join(toks).strip()
                return tok, segments

    return "", segments


def _extract_complement(segments: list[str]) -> tuple[str, list[str]]:
    """Extrai complementos (apartamento, bloco, sala, ...)."""
    complements: list[str] = []
    remaining: list[str] = []
    for seg in segments:
        toks = seg.split()
        # Se o segmento começa com um marcador de complemento, é complemento.
        if toks and toks[0] in COMPLEMENT_MARKERS:
            complements.append(seg)
            continue
        # Marcador no meio do segmento: corta a partir dele.
        cut = next((k for k, t in enumerate(toks) if t in COMPLEMENT_MARKERS), None)
        if cut is not None:
            complements.append(" ".join(toks[cut:]))
            head = " ".join(toks[:cut]).strip()
            if head:
                remaining.append(head)
        else:
            remaining.append(seg)
    return " ".join(complements).strip(), remaining


def parse_address(raw: str) -> AddressComponents:
    """Decompõe um endereço em texto livre em :class:`AddressComponents`."""
    comp = AddressComponents()
    if not raw or not raw.strip():
        return comp

    text = _preprocess(raw)
    comp.zip_code, text = _extract_zip(text)

    segments = [s.strip() for s in text.split(",") if s.strip()]

    comp.state, segments = _extract_state(segments)
    comp.complement, segments = _extract_complement(segments)
    comp.number, segments = _extract_number(segments)
    segments = [s for s in segments if s]

    # Tipo de logradouro: primeira palavra do primeiro segmento, se conhecida.
    if segments:
        first_tokens = segments[0].split()
        if first_tokens and first_tokens[0] in STREET_TYPES:
            comp.street_type = first_tokens[0]
            segments[0] = " ".join(first_tokens[1:]).strip()
            if not segments[0]:
                segments.pop(0)

    # Atribuição posicional dos segmentos restantes.
    segments = [s for s in segments if s]
    comp.street_name, comp.district, comp.city = _assign_segments(segments)

    return comp


def _assign_segments(segments: list[str]) -> tuple[str, str, str]:
    """Distribui os segmentos restantes entre rua, bairro e cidade.

    Convenção brasileira mais comum: [rua, bairro, cidade].
    """
    n = len(segments)
    if n == 0:
        return "", "", ""
    if n == 1:
        # Sem vírgulas suficientes: provavelmente "rua nome cidade" tudo junto.
        # Heurística: as duas últimas palavras tendem a ser a cidade.
        return _split_single_segment(segments[0])
    if n == 2:
        # [rua, cidade] — sem bairro identificável.
        return segments[0], "", segments[1]
    # n >= 3: rua, bairro, cidade (ignora segmentos extras juntando no bairro).
    street = segments[0]
    city = segments[-1]
    district = " ".join(segments[1:-1])
    return street, district, city


def _split_single_segment(seg: str) -> tuple[str, str, str]:
    """Heurística para endereço sem vírgulas: separa rua e cidade.

    Assume que as duas últimas palavras formam a cidade (ex.: 'belo horizonte',
    'sao paulo'). É uma aproximação grosseira, documentada como tal.
    """
    toks = seg.split()
    if len(toks) <= 2:
        return seg, "", ""
    city = " ".join(toks[-2:])
    street = " ".join(toks[:-2])
    return street, "", city


if __name__ == "__main__":  # demonstração
    exemplos = [
        "Av. Afonso Pena, 1000, Centro, Belo Horizonte - MG",
        "R. da Bahia, nº 500, Belo Horizonte - Minas Gerais",
        "Avenida Paulista 1001 Sao Paulo",
        "Rua das Flores, 25, apto 302, Savassi, Belo Horizonte - MG, 30130-100",
    ]
    for ex in exemplos:
        print(ex)
        for k, v in parse_address(ex).as_dict().items():
            print(f"   {k:12s}: {v!r}")
        print()
