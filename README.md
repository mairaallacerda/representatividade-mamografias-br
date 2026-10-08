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
| **CBIS-DDSM** ([Kaggle](https://www.kaggle.com/datasets/awsaf49/cbis-ddsm-breast-cancer-image-dataset), versão em JPEG do [TCIA](https://www.cancerimagingarchive.net/collection/cbis-ddsm/)) | Imagens + metadados clínicos: densidade mamária, tipo de anormalidade, tipo/distribuição de calcificação, BI-RADS, patologia | Download direto (CSV + JPEG) |
| **INCA** | Estimativas de incidência, mortalidade, mamografias no SUS 2018–2022 | Web scraping (requests + BeautifulSoup) |
| **DATASUS / TABNET** | Mamografias realizadas (SIA) e óbitos por câncer de mama (SIM), por UF, faixa etária e ano | Web scraping com envio de formulário (requests.post) |
| **DATASUS / SISCAN** | Laudos de mamografia: BI-RADS e densidade (tipo de mama), por faixa etária, indicação e ano | Web scraping de formulário TabnetBD; dados extraídos do JavaScript da resposta |

**Período (dados brasileiros):** mamografias realizadas entre **2018 e 2022**, além das estimativas de incidência mais recentes. O CBIS-DDSM é tratado como base **transversal**.

**Limitação conhecida:** o CBIS-DDSM não traz a idade individual das pacientes, o que restringe comparações diretas por faixa etária.

## Estrutura do repositório

```
.
├── data/
│   ├── raw/            # dados brutos (não versionados)
│   │   ├── inca/
│   │   ├── datasus/
│   │   └── cbis-ddsm/  # CSVs de metadados + jpeg/ (link para as imagens)
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
python -m src.scraping.tabnet    # TABNET: mamografias (SIA) e óbitos por câncer de mama (SIM), 2018–2022
python -m src.scraping.siscan    # SISCAN: laudos de mamografia por BI-RADS e densidade, 2018–2022
```

HTML bruto em `data/raw/`, CSVs em `data/interim/`. Análise de cada fonte e problemas encontrados:
[docs/scraping_inca.md](docs/scraping_inca.md) · [docs/scraping_tabnet.md](docs/scraping_tabnet.md) ·
[docs/scraping_siscan.md](docs/scraping_siscan.md).

Testes:

```bash
python -m pytest
```

### CBIS-DDSM (Kaggle)

O dataset **não é versionado** no repositório: são ~6 GB (10.237 imagens JPEG), acima do que o GitHub
aceita, e a fonte deve ser citada em vez de redistribuída. Cada pessoa baixa a sua cópia.

**1. Baixar** a versão do Kaggle, [CBIS-DDSM: Breast Cancer Image Dataset](https://www.kaggle.com/datasets/awsaf49/cbis-ddsm-breast-cancer-image-dataset).
Dá para baixar o `.zip` pelo navegador ("Download") ou usar a API do Kaggle. A API exige um token pessoal:
gere em *Kaggle → Settings → API → Create New Token* e salve o arquivo em `~/.kaggle/kaggle.json`.

```bash
pip install kaggle
kaggle datasets download -d awsaf49/cbis-ddsm-breast-cancer-image-dataset -p ~/datasets --unzip
```

**2. Colocar no projeto.** O projeto espera esta estrutura:

```
data/raw/cbis-ddsm/
├── mass_case_description_train_set.csv
├── mass_case_description_test_set.csv
├── calc_case_description_train_set.csv
├── calc_case_description_test_set.csv
├── dicom_info.csv          # 1 linha por imagem; liga imagem ↔ lesão
├── meta.csv
└── jpeg/                   # imagens (pasta ou link simbólico)
```

Copie os CSVs da pasta `csv/` do download. Para as imagens, em vez de copiar 6 GB, crie um **link simbólico**
para a pasta `jpeg/` baixada:

```bash
cp ~/datasets/csv/*.csv data/raw/cbis-ddsm/
ln -s ~/datasets/jpeg data/raw/cbis-ddsm/jpeg
```

**3. Conferir:**

```bash
python -c "from src.processing.cbis import carrega_imagens; d = carrega_imagens(); print(d.existe.sum(), 'de', len(d), 'imagens encontradas')"
```

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
