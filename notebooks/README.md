# Notebooks

A coleta é feita por scripts (`python -m src.scraping.inca` e `python -m src.scraping.tabnet`), não por notebooks.
Os notebooks partem dos CSVs em `data/interim/` e dos metadados do CBIS-DDSM em `data/raw/cbis-ddsm/`.

| Notebook | Conteúdo | Status |
|---|---|---|
| `01_analise_exploratoria.ipynb` | Mamografias, mortalidade e incidência no Brasil; perfil do CBIS-DDSM; malignidade × densidade/BI-RADS/tipo; comparação de composição Brasil × CBIS | pronto |
| `02_comparacao_birads_densidade.ipynb` | Comparação direta das distribuições de BI-RADS e densidade (depende de dados do SISCAN) | a fazer |
| `03_imagens_calcificacoes.ipynb` | PDI e extração de características (complementar) | a fazer |

As figuras são salvas em `reports/figures/`.

Para importar o código de `src/` dentro de um notebook:

```python
import sys; sys.path.append("..")
from src.processing.cbis import carrega_cbis
```
