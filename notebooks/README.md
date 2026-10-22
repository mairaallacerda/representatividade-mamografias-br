# Notebooks

A coleta é feita por scripts (`python -m src.scraping.inca`, `.tabnet` e `.siscan`), não por notebooks.
Os notebooks partem dos CSVs em `data/interim/` e dos metadados do CBIS-DDSM em `data/raw/cbis-ddsm/`.

| Notebook | Conteúdo | Depende de |
|---|---|---|
| `01_analise_exploratoria.ipynb` | Mamografias, mortalidade e incidência no Brasil; perfil do CBIS-DDSM; malignidade × densidade/BI-RADS/tipo; composição dos casos Brasil × CBIS | scrapers INCA e TABNET |
| `03_imagens_calcificacoes.ipynb` | Qualidade e ligação das imagens (recuperação das 566 imagens sem tipo); PDI de microcalcificações; características × malignidade e × densidade; modelo por densidade e por prevalência | imagens em `data/raw/cbis-ddsm/jpeg` (~7 min na 1ª execução, depois usa cache) |
| `04_comparacao_birads_densidade.ipynb` | Comparação direta Brasil (SISCAN) × CBIS-DDSM: densidade (geral e por idade), BI-RADS, densidade × dificuldade, AUC do modelo reponderada pela composição brasileira; densidade e BI-RADS por região (padronizada por idade); **resposta à pergunta do trabalho** | scraper SISCAN e previsões salvas pelo notebook 03 |
| `05_quadro_sintese.ipynb` | Quadro-síntese da comparação (CBIS-DDSM × Brasil por dimensão, com veredito) e as comparações lado a lado; **resumo da resposta** | notebooks 01, 03 e 04 e `python -m src.visualization.painel_dados` |

Ordem de execução: 01 → 03 → 04 → `painel_dados` → 05. (O número 02 ficou reservado e não foi usado.)

As figuras são salvas em `reports/figures/`.

Para importar o código de `src/` dentro de um notebook:

```python
import sys; sys.path.append("..")
from src.processing.cbis import carrega_cbis
```
