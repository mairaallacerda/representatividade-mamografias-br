# Representatividade de Bases Públicas de Mamografias no Contexto Epidemiológico Brasileiro

Trabalho da disciplina **Ciência dos Dados** — Engenharia de Computação, CEFET-MG Campus Divinópolis.

**Autores:** Maira Beatriz de Almeida Lacerda · João Francisco Teles da Silva

## Pergunta principal

> Em que medida as características dos casos presentes em uma base pública internacional de mamografias (CBIS-DDSM) são compatíveis com o perfil epidemiológico do câncer de mama no Brasil?

**Questões complementares**

- Como os casos do CBIS-DDSM se distribuem segundo densidade mamária, tipo de anormalidade e classificação BI-RADS?
- Essas características estão associadas à malignidade (benigno × maligno)?

**Hipótese:** existem diferenças entre o perfil representado na base internacional e o contexto brasileiro, o que indica uma limitação de representatividade.

## Bases de dados

| Fonte | Conteúdo | Forma de obtenção |
|---|---|---|
| **CBIS-DDSM** ([TCIA](https://www.cancerimagingarchive.net/collection/cbis-ddsm/) / Kaggle) | Imagens + metadados clínicos: densidade mamária, tipo de anormalidade, tipo/distribuição de calcificação, BI-RADS, patologia | Download direto (CSV/DICOM) |
| **INCA** | Estimativas de incidência, mortalidade, "Dados e números 2024" | Web scraping (requests + BeautifulSoup) |
| **DATASUS / TABNET** | Mamografias realizadas (SISCAN), faixa etária, UF, ano | Web scraping com envio de formulário (requests.post / Selenium) |

**Período (dados brasileiros):** mamografias realizadas entre **2018 e 2022**, além das estimativas de incidência mais recentes. O CBIS-DDSM é tratado como base **transversal**.

**Limitação conhecida:** o CBIS-DDSM não traz a idade individual das pacientes, o que restringe comparações diretas por faixa etária.

## Estrutura do repositório

```
.
├── data/
│   ├── raw/            # dados brutos (não versionados)
│   │   ├── inca/
│   │   ├── datasus/
│   │   └── cbis-ddsm/  # CSVs de metadados (e imagens, se baixadas)
│   ├── interim/        # dados intermediários (pós-limpeza parcial)
│   └── processed/      # dados finais, prontos para análise
├── notebooks/          # análises exploratórias (numerados em ordem)
├── src/
│   ├── config.py       # caminhos e URLs centralizados
│   ├── scraping/       # coleta INCA e TABNET/DATASUS
│   ├── processing/     # limpeza, padronização e cruzamento
│   ├── analysis/       # testes estatísticos
│   ├── images/         # PDI e extração de características (OpenCV/scikit-image)
│   └── visualization/  # gráficos padronizados
├── reports/figures/    # figuras geradas para o relatório
├── dashboards/         # painéis de BI (Power BI)
├── docs/               # pré-projeto, proposta e referências
└── tests/
```

## Etapas

1. **Extração** — scraping direcionado do INCA e do TABNET; leitura dos metadados do CBIS-DDSM.
2. **Tratamento** — valores ausentes, limpeza com regex, padronização de categorias (faixas etárias, BI-RADS, densidade), estruturação em `pandas`.
3. **Análise** — exploratória do CBIS-DDSM, comparação com o contexto brasileiro, associação características × malignidade (qui-quadrado, etc.), análise temporal 2018–2022.
4. **Visualização** — Matplotlib/Seaborn, Plotly e painel em Power BI.
5. **Imagens (complementar)** — pré-processamento e extração de características de calcificações; exploração de ML supervisionado para discutir viés.

## Como rodar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Coleta (web scraping)

```bash
python -m src.scraping.inca      # INCA: incidência, mamografias no SUS (2018–2022), mortalidade
```

HTML bruto em `data/raw/inca/`, CSVs em `data/interim/`. Detalhes e problemas encontrados na fonte: [docs/scraping_inca.md](docs/scraping_inca.md).

Testes:

```bash
python -m pytest
```

### CBIS-DDSM

Baixe os CSVs de metadados do CBIS-DDSM e coloque em `data/raw/cbis-ddsm/`:

- `mass_case_description_train_set.csv`, `mass_case_description_test_set.csv`
- `calc_case_description_train_set.csv`, `calc_case_description_test_set.csv`

Depois:

```bash
jupyter lab
```

## Fontes dos dados

- Kaggle – CBIS-DDSM Breast Cancer Image Dataset
- The Cancer Imaging Archive – CBIS-DDSM
- INCA – Fontes de Informação sobre o Controle do Câncer de Mama
- INCA – Controle do câncer de mama no Brasil: dados e números 2024
- DATASUS – Informações de Saúde (TABNET)
