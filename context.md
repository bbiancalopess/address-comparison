# Projeto: Comparador Inteligente de Endereços usando Sistemas Nebulosos

Implemente um projeto completo em Python chamado "Fuzzy Address Matcher".

O objetivo do sistema é receber dois endereços em formato texto (strings), decompor os endereços em partes estruturadas e calcular um índice de similaridade usando Sistemas Nebulosos (Fuzzy Logic).

O projeto deve ser didático, modular e adequado para apresentação acadêmica em uma disciplina de Sistemas Nebulosos.

---

# Objetivo do Sistema

O sistema deve:

1. Receber dois endereços em formato string
2. Normalizar os textos
3. Extrair componentes do endereço
4. Comparar os componentes individualmente
5. Aplicar lógica fuzzy para calcular similaridade
6. Produzir:

   * score final de similaridade (0–100)
   * classificação textual:

     * "diferentes"
     * "parecidos"
     * "muito semelhantes"
     * "provavelmente iguais"
   * explicação dos fatores que influenciaram o resultado

---

# Tecnologias Obrigatórias

Use:

* Python 3.11+
* scikit-fuzzy
* rapidfuzz
* pandas
* numpy

Opcional:

* FastAPI
* Streamlit
* pydantic

---

# Estrutura Esperada do Projeto

Crie a seguinte estrutura:

fuzzy_address_matcher/
│
├── app/
│   ├── parser.py
│   ├── normalizer.py
│   ├── similarity.py
│   ├── fuzzy_engine.py
│   ├── rules.py
│   ├── explainability.py
│   ├── api.py
│   └── main.py
│
├── tests/
│   └── test_cases.py
│
├── data/
│   └── sample_addresses.csv
│
├── requirements.txt
└── README.md

---

# Pipeline Completo

## 1. Normalização

Implemente funções para:

* converter para lowercase
* remover acentos
* remover caracteres especiais
* padronizar abreviações

Exemplos:

"Av." → "avenida"
"R." → "rua"
"apto" → "apartamento"

Também tratar:

* múltiplos espaços
* vírgulas
* hífens
* CEP
* complementos

---

# 2. Parsing do Endereço

Transformar o endereço em uma estrutura:

{
"street_type": "",
"street_name": "",
"number": "",
"district": "",
"city": "",
"state": "",
"zip_code": "",
"complement": ""
}

Exemplo:

Entrada:
"Av. Afonso Pena, 1000, Centro, Belo Horizonte - MG"

Saída:
{
"street_type": "avenida",
"street_name": "afonso pena",
"number": "1000",
"district": "centro",
"city": "belo horizonte",
"state": "mg"
}

Use:

* regex
* heurísticas
* tokenização

---

# 3. Similaridade por Campo

Calcule similaridade individual para cada campo usando:

* RapidFuzz
* Levenshtein
* token_sort_ratio
* partial_ratio

Exemplo:

similaridade_rua = 92
similaridade_bairro = 80
similaridade_cidade = 100

---

# 4. Sistema Nebuloso

Implemente um sistema fuzzy usando scikit-fuzzy.

## Variáveis de Entrada

### Similaridade da Rua

Faixas:

* baixa
* média
* alta

### Similaridade do Número

Faixas:

* diferente
* próximo
* igual

### Similaridade da Cidade

Faixas:

* baixa
* alta

### Similaridade do CEP

Faixas:

* diferente
* parcial
* igual

---

# Variável de Saída

similaridade_final

Faixas:

* muito_baixa
* baixa
* média
* alta
* muito_alta

Universo:
0–100

---

# Regras Fuzzy

Implemente regras como:

IF rua IS alta AND numero IS igual THEN similaridade IS muito_alta

IF rua IS alta AND cidade IS alta THEN similaridade IS alta

IF rua IS baixa THEN similaridade IS baixa

IF cep IS igual THEN similaridade IS muito_alta

IF numero IS diferente AND rua IS média THEN similaridade IS média

Crie pelo menos 15 regras fuzzy.

---

# Método de Inferência

Use:

* Mamdani inference
* centroid defuzzification

---

# Explicabilidade

O sistema deve retornar uma explicação textual:

Exemplo:

"A similaridade foi considerada alta porque:

* o nome da rua teve 94% de correspondência
* o número é idêntico
* cidade e estado coincidem
* CEP parcialmente correspondente"

---

# API REST

Implemente API usando FastAPI.

Endpoint:

POST /compare

Body:

{
"address1": "Av Afonso Pena 1000 Centro Belo Horizonte MG",
"address2": "Avenida Afonso Pena, 1000, Centro, BH - MG"
}

Resposta:

{
"score": 91.2,
"classification": "provavelmente iguais",
"details": {
"street_similarity": 95,
"number_similarity": 100,
"city_similarity": 90
},
"explanation": "..."
}

---

# Interface Opcional

Se possível, criar interface Streamlit com:

* dois campos de endereço
* botão comparar
* score visual
* gráfico fuzzy
* regras ativadas

---

# Testes

Crie casos de teste para:

* endereços idênticos
* abreviações
* erros de digitação
* bairros diferentes
* números diferentes
* cidades iguais
* CEP parcialmente igual

---

# Casos Reais para Teste

Use exemplos brasileiros.

Exemplo:

"Rua da Bahia 500 Belo Horizonte MG"

vs

"R. da Bahia, nº 500, Belo Horizonte - Minas Gerais"

Outro:

"Av Paulista 1000 São Paulo"

vs

"Avenida Paulista 1001 Sao Paulo"

---

# README

Crie README detalhado contendo:

* explicação do problema
* conceitos de fuzzy logic usados
* arquitetura
* como executar
* exemplos
* imagens dos gráficos fuzzy
* explicação matemática das funções de pertinência

---

# Requisitos Acadêmicos

O código deve ser:

* bem comentado
* modular
* explicável
* orientado para demonstração acadêmica

Evite código excessivamente complexo.

Priorize clareza e visualização do sistema fuzzy.

---

# Extras Desejáveis

Se possível, implemente:

* gráficos das membership functions
* visualização das regras ativadas
* ajuste de pesos
* comparação em lote via CSV
* benchmark de desempenho
* suporte multilíngue
* fuzzy clustering de endereços

---

# Resultado Esperado

Ao final, gere:

1. Projeto completo
2. Código funcional
3. requirements.txt
4. README.md
5. Exemplos de execução
6. Testes automatizados
7. API pronta para rodar

O projeto deve executar com:

pip install -r requirements.txt

e depois:

uvicorn app.api:app --reload

ou

python app/main.py
