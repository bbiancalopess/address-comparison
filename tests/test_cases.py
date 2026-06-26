"""Testes automatizados do Fuzzy Address Matcher.

Cobrem os casos pedidos no enunciado:
    * endereços idênticos
    * abreviações
    * erros de digitação
    * bairros diferentes
    * números diferentes
    * cidades iguais
    * CEP parcialmente igual

Execução:
    pytest -q
"""

from __future__ import annotations

import pytest

from app.explainability import classify
from app.fuzzy_engine import FuzzyAddressEngine
from app.main import compare_addresses
from app.normalizer import normalize
from app.parser import parse_address
from app.similarity import field_similarities


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------
def test_normalize_expande_abreviacoes_e_remove_acentos():
    out = normalize("Av. São João, nº 10 - apto 3")
    assert "avenida" in out
    assert "sao joao" in out
    assert "apartamento" in out
    assert "." not in out and "," not in out


def test_normalize_colapsa_espacos():
    assert normalize("Rua    da    Bahia") == "rua da bahia"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def test_parse_endereco_completo_com_virgulas():
    c = parse_address("Av. Afonso Pena, 1000, Centro, Belo Horizonte - MG")
    assert c.street_type == "avenida"
    assert "afonso pena" in c.street_name
    assert c.number == "1000"
    assert c.district == "centro"
    assert c.city == "belo horizonte"
    assert c.state == "mg"


def test_parse_extrai_cep():
    c = parse_address("Rua das Flores, 25, Savassi, Belo Horizonte - MG, 30130-100")
    assert c.zip_code == "30130100"
    assert c.number == "25"


def test_parse_extrai_complemento():
    c = parse_address("Rua X, 10, apto 302, Centro, Belo Horizonte - MG")
    assert "apartamento" in c.complement
    assert c.number == "10"


# ---------------------------------------------------------------------------
# Similaridade por campo
# ---------------------------------------------------------------------------
def test_numero_identico_e_proximo():
    a = parse_address("Rua A 1000 Cidade X SP")
    b_igual = parse_address("Rua A 1000 Cidade X SP")
    b_proximo = parse_address("Rua A 1001 Cidade X SP")
    b_distante = parse_address("Rua A 50 Cidade X SP")

    assert field_similarities(a, b_igual).number == 100.0
    assert field_similarities(a, b_proximo).number > 95.0
    assert field_similarities(a, b_distante).number < 60.0


def test_cep_parcial():
    a = parse_address("Rua A 10 Cidade X SP 30130-100")
    b = parse_address("Rua A 10 Cidade X SP 30130-999")
    z = field_similarities(a, b).zip_code
    assert 50 < z < 100  # prefixo comum, mas não idêntico


# ---------------------------------------------------------------------------
# Motor fuzzy
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def engine():
    return FuzzyAddressEngine()


def test_fuzzy_tudo_alto_da_score_alto(engine):
    res = engine.infer(street=100, number=100, city=100, cep=100)
    assert res.score > 80
    assert len(res.active_rules) > 0


def test_fuzzy_tudo_baixo_da_score_baixo(engine):
    res = engine.infer(street=5, number=0, city=0, cep=0)
    assert res.score < 35


def test_fuzzy_monotonia_da_rua(engine):
    """Aumentar a similaridade da rua não deve reduzir o score final."""
    baixo = engine.infer(street=20, number=50, city=50, cep=50).score
    alto = engine.infer(street=95, number=50, city=50, cep=50).score
    assert alto >= baixo


# ---------------------------------------------------------------------------
# Pipeline completo (casos do enunciado)
# ---------------------------------------------------------------------------
def test_enderecos_identicos():
    r = compare_addresses(
        "Av Afonso Pena 1000 Centro Belo Horizonte MG",
        "Av Afonso Pena 1000 Centro Belo Horizonte MG",
    )
    assert r.score > 80
    assert r.classification in {"muito semelhantes", "provavelmente iguais"}


def test_abreviacoes_equivalem():
    r = compare_addresses(
        "Av Afonso Pena 1000 Centro Belo Horizonte MG",
        "Avenida Afonso Pena, 1000, Centro, BH - MG",
    )
    assert r.score > 70


def test_erro_de_digitacao():
    r = compare_addresses(
        "Avenida Paulista 1000 Sao Paulo SP",
        "Avenida Paullista 1000 Sao Paulo SP",
    )
    assert r.score > 70


def test_numeros_diferentes_reduzem_score():
    iguais = compare_addresses(
        "Av Amazonas 100 Centro Belo Horizonte MG",
        "Av Amazonas 100 Centro Belo Horizonte MG",
    ).score
    diferentes = compare_addresses(
        "Av Amazonas 100 Centro Belo Horizonte MG",
        "Av Amazonas 9000 Gameleira Belo Horizonte MG",
    ).score
    assert diferentes < iguais


def test_enderecos_totalmente_diferentes():
    r = compare_addresses(
        "Av Brasil 2000 Copacabana Rio de Janeiro RJ",
        "Rua das Flores 25 Savassi Belo Horizonte MG",
    )
    assert r.classification in {"diferentes", "parecidos"}
    assert r.score < 60


# ---------------------------------------------------------------------------
# Classificação
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "score,label",
    [
        (95, "provavelmente iguais"),
        (70, "muito semelhantes"),
        (50, "parecidos"),
        (10, "diferentes"),
    ],
)
def test_classify_bands(score, label):
    assert classify(score) == label


def test_resultado_tem_explicacao_e_detalhes():
    r = compare_addresses("Rua A 10 Centro SP", "Rua A 10 Centro SP")
    assert isinstance(r.explanation, str) and len(r.explanation) > 0
    assert "street_similarity" in r.details
