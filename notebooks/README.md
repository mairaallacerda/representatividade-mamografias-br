# Notebooks

Numerados na ordem em que devem ser executados:

| Notebook | Etapa |
|---|---|
| `01_coleta_inca.ipynb` | Scraping das páginas do INCA |
| `02_coleta_tabnet.ipynb` | Scraping do TABNET/DATASUS (mamografias 2018–2022) |
| `03_eda_cbis_ddsm.ipynb` | Análise exploratória dos metadados do CBIS-DDSM |
| `04_tratamento_padronizacao.ipynb` | Limpeza e padronização de categorias |
| `05_comparacao_br_x_cbis.ipynb` | Cruzamento e testes estatísticos |
| `06_associacao_malignidade.ipynb` | Densidade / tipo / BI-RADS × malignidade |
| `07_imagens_calcificacoes.ipynb` | PDI e extração de características (complementar) |

Para importar o código de `src/` dentro de um notebook:

```python
import sys; sys.path.append("..")
from src.processing.cbis import carrega_cbis
```
