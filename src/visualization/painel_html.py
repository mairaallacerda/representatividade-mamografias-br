"""Gera o painel HTML interativo (``dashboards/painel.html``) a partir de ``dashboards/dados/``.

O HTML é autocontido: os dados vão embutidos como JSON e os gráficos usam Chart.js (CDN).

Uso:
    python -m src.visualization.painel_dados   # antes, se os dados mudaram
    python -m src.visualization.painel_html
"""

import json
import logging
from pathlib import Path

import pandas as pd

from src import config

log = logging.getLogger(__name__)

DADOS = config.ROOT / "dashboards" / "dados"
MODELO = Path(__file__).with_name("painel_modelo.html")

TABELAS = ["dim_localidade", "fato_uf_ano", "fato_incidencia_uf", "obitos_faixa", "densidade_faixa",
           "comparacao_densidade", "comparacao_birads", "birads_densidade_brasil",
           "modelo_auc_densidade", "modelo_auc_populacao"]


def carrega_dados() -> dict:
    dados = {}
    for nome in TABELAS:
        caminho = DADOS / f"{nome}.csv"
        if not caminho.exists():
            raise FileNotFoundError(f"{caminho} não existe — rode antes: python -m src.visualization.painel_dados")
        dados[nome] = json.loads(pd.read_csv(caminho).to_json(orient="records", force_ascii=False))
    dados["indicadores"] = json.loads((DADOS / "indicadores.json").read_text())
    return dados


def gera(destino: Path | None = None, documento_completo: bool = True) -> Path:
    """``documento_completo=False`` omite doctype/html/head/body (para publicar como Artifact)."""
    destino = destino or config.ROOT / "dashboards" / "painel.html"
    corpo = MODELO.read_text(encoding="utf-8")
    dados = json.dumps(carrega_dados(), ensure_ascii=False).replace("</", "<\\/")
    corpo = corpo.replace("__DADOS_JSON__", dados)
    if documento_completo:
        corpo = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
                 '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                 "</head>\n<body>\n" + corpo + "\n</body>\n</html>\n")
    destino.write_text(corpo, encoding="utf-8")
    log.info("Painel gerado em %s (%.0f KB)", destino, destino.stat().st_size / 1024)
    return destino


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    gera()
