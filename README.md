# bootstrap-curva

Serviço de bootstrapping da curva zero-cupom para títulos públicos federais pré-fixados (LTN e NTN-F), com base nos arquivos de preços e feriados publicados pela ANBIMA.

---

## Pré-requisitos

- Python 3.10 ou superior
- [pipenv](https://pipenv.pypa.io/en/latest/)

---

## Instalação

Abra o seu terminal (por exemplo, Git Bash) e clone o repositório. Em seguida, instale as dependências:

```bash
git clone https://github.com/EdilsonRogerioCuambe/bootstrap-curva.git
cd bootstrap-curva
python -m pipenv install
```

---

## Como usar

Coloque os arquivos da ANBIMA na pasta `data/`:

| Arquivo | Fonte |
|---|---|
| TXT de preços (LTN, NTN-F) | [Ferramenta ANBIMA](https://www.anbima.com.br/pt_br/informar/ferramenta/precos-e-indices/taxas-titulos-publicos.htm) → selecione a data → download `.txt` |
| Feriados nacionais | [Download direto `.xls`](https://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls) |

Execute o bootstrapping informando o caminho dos arquivos e a data de referência:

```bash
python -m pipenv run python -m src.bootstrap.bootstrap \
  --prices  data/precos_20260601.txt \
  --holidays data/feriados_nacionais.xls \
  --date    2026-06-01
```

---

## Testes

Para garantir que tudo está funcionando perfeitamente (incluindo a validação de re-precificação), rode os testes automatizados com o seguinte comando:

```bash
python -m pipenv run pytest tests/ -v
```

---

## Arquitetura

```
bootstrap-curva/
├── data/                   # arquivos ANBIMA (não versionados no repositório geral)
├── src/
│   └── bootstrap/
│       ├── calendar.py     # leitura de feriados e contagem de dias úteis (base 252)
│       ├── parser.py       # leitura e interpretação do TXT ANBIMA
│       ├── cashflows.py    # geração de fluxos de caixa por título
│       ├── matrix.py       # organização das datas e montagem da matriz de fluxos
│       ├── solver.py       # resolução do sistema para obter a curva final
│       └── bootstrap.py    # orquestrador que conecta todos os passos
└── tests/
    ├── test_calendar.py
    ├── test_cashflows.py
    ├── test_matrix.py
    ├── test_solver.py
    └── test_bootstrap.py   # teste de integração principal
```

### Módulos Principais

**`calendar.py`** — Lê o arquivo de feriados da ANBIMA (suportando arquivos texto e planilhas `.xls`) e conta dias úteis entre duas datas usando a convenção de mercado. Converte o resultado para anos na base 252.

**`parser.py`** — Analisa o TXT de preços disponibilizado pela ANBIMA, filtra os títulos de interesse (LTNs e NTN-Fs), converte as datas e os valores financeiros e devolve os registros ordenados pelo vencimento.

**`cashflows.py`** — Gera a lista cronológica de pagamentos de cada título. Uma LTN produz um único fluxo no vencimento. Uma NTN-F produz os devidos pagamentos de cupons semestrais e o principal no vencimento.

**`matrix.py`** — Coleta todas as datas únicas de pagamento do conjunto de títulos e organiza uma estrutura matricial onde as linhas representam os títulos e as colunas as datas de pagamento, facilitando o cruzamento dos dados.

**`solver.py`** — Recebe a matriz de pagamentos e os preços de mercado para calcular os fatores de desconto de cada vértice temporal. Em seguida, converte esses fatores em taxas de juros spot (taxa anualizada). Também executa uma verificação final exigindo precisão quase exata.

**`bootstrap.py`** — Chama todos os módulos em sequência, processa as informações e devolve o resultado final estruturado como um dicionário Python simples e legível.

---

## Saída esperada (Exemplo)

```json
{
  "data_base": "2026-06-01",
  "erro_reprecificacao": 0.0,
  "curva": [
    {
      "data": "2026-07-01",
      "du": 21,
      "prazo_anos": 0.083333,
      "fator_desconto": 0.988866,
      "taxa_spot": 0.143798
    },
    {
      "data": "2026-10-01",
      "du": 86,
      "prazo_anos": 0.34127,
      "fator_desconto": 0.956259,
      "taxa_spot": 0.140034
    },
    {
      "data": "2027-01-01",
      "du": 148,
      "prazo_anos": 0.587302,
      "fator_desconto": 0.925696,
      "taxa_spot": 0.140498
    }
  ]
}
```

---

## Convenções de Mercado Aplicadas

| Convenção | Descrição |
|---|---|
| **Base de dias** | 252 dias úteis por ano |
| **Contagem de DU** | Contagem exata do intervalo útil considerando os feriados nacionais |
| **Datas de cupom NTN-F** | 1º de janeiro e 1º de julho de cada ano |
