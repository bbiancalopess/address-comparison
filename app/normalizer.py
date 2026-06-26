"""Normalização de textos de endereços.

A normalização é a primeira etapa do pipeline. O objetivo é reduzir a
variabilidade superficial dos textos (acentos, maiúsculas, abreviações,
pontuação) para que as etapas seguintes (parsing e similaridade) trabalhem
sobre uma forma canônica.

Exemplos de transformação:

    "Av."   -> "avenida"
    "R."    -> "rua"
    "apto"  -> "apartamento"
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Tabela de abreviações comuns em endereços brasileiros.
# A chave é a forma abreviada (já em minúsculas, sem ponto) e o valor é a
# forma expandida canônica.
# ---------------------------------------------------------------------------
ABBREVIATIONS = {
    # tipos de logradouro
    "av": "avenida",
    "avd": "avenida",
    "ave": "avenida",
    "r": "rua",
    "rod": "rodovia",
    "trav": "travessa",
    "tv": "travessa",
    "al": "alameda",
    "pc": "praca",
    "pca": "praca",
    "estr": "estrada",
    "lrg": "largo",
    # complementos
    "apto": "apartamento",
    "ap": "apartamento",
    "apt": "apartamento",
    "bl": "bloco",
    "bloco": "bloco",
    "cj": "conjunto",
    "conj": "conjunto",
    "qd": "quadra",
    "lt": "lote",
    "sl": "sala",
    "fds": "fundos",
    "cs": "casa",
    "km": "km",
    # marcadores de número
    "n": "numero",
    "no": "numero",
    "nro": "numero",
    "num": "numero",
}

# NOTA: nomes de estados (ex.: "minas gerais" -> "mg") NÃO entram aqui de
# propósito. Eles colidem com nomes de logradouros e cidades ("Rua da Bahia",
# cidade "São Paulo"). A identificação do estado é feita pelo parser, que
# analisa apenas o último segmento do endereço (ver app/parser.py).


def strip_accents(text: str) -> str:
    """Remove acentos preservando as letras base (ç -> c, á -> a)."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _expand_multiword_abbreviations(text: str) -> str:
    """Substitui abreviações de várias palavras (ex.: 'minas gerais' -> 'mg')."""
    for source, target in ABBREVIATIONS.items():
        if " " in source:
            text = re.sub(rf"\b{re.escape(source)}\b", target, text)
    return text


def _expand_token_abbreviations(text: str) -> str:
    """Substitui abreviações de palavra única, token a token."""
    tokens = text.split()
    expanded = [ABBREVIATIONS.get(tok, tok) for tok in tokens]
    return " ".join(expanded)


def normalize(text: str, *, expand_abbreviations: bool = True) -> str:
    """Normaliza um texto de endereço para forma canônica.

    Passos:
        1. lowercase
        2. remoção de acentos
        3. troca de pontuação relevante por espaço (vírgulas, hífens, etc.)
        4. remoção de caracteres especiais restantes
        5. expansão de abreviações
        6. colapso de múltiplos espaços

    O CEP é preservado: dígitos e o separador "-" entre dígitos não são
    descartados de forma a destruir o número.
    """
    if text is None:
        return ""

    text = text.lower()
    text = strip_accents(text)

    # Pontos em abreviações ("av." -> "av ") e separadores viram espaço.
    text = text.replace(".", " ")
    text = re.sub(r"[,/;]", " ", text)

    # Hífen: mantém quando está entre dígitos (CEP 30130-100), senão vira espaço.
    text = re.sub(r"(?<!\d)-(?!\d)", " ", text)
    text = re.sub(r"\s*-\s*", " ", text)  # "MG - " e variações soltas

    # Remove qualquer caractere que não seja letra, dígito, espaço ou hífen/#.
    text = re.sub(r"[^a-z0-9\s#-]", " ", text)
    text = text.replace("#", " numero ")

    if expand_abbreviations:
        text = _expand_multiword_abbreviations(text)
        text = _expand_token_abbreviations(text)

    # Colapsa múltiplos espaços.
    text = re.sub(r"\s+", " ", text).strip()
    return text


if __name__ == "__main__":  # pequena demonstração manual
    exemplos = [
        "Av. Afonso Pena, 1000, Centro, Belo Horizonte - MG",
        "R. da Bahia, nº 500, Belo Horizonte - Minas Gerais",
        "Avenida Paulista 1001 Sao Paulo - SP, CEP 01310-100",
    ]
    for ex in exemplos:
        print(f"{ex!r}\n  -> {normalize(ex)!r}\n")
