"""Mapa do Brasil por UF (malha oficial do IBGE), desenhado só com matplotlib.

A malha é baixada uma vez da API de malhas do IBGE e guardada em ``data/raw/ibge/``.
"""

import json
import logging

import numpy as np
import requests
from matplotlib.patches import Polygon

from src import config
from src.visualization import estilo

log = logging.getLogger(__name__)

URL = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
PASTA = config.RAW / "ibge"

SIGLA_IBGE = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
    "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS",
    "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
REGIAO_IBGE = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}


def malha(nivel: str = "UF") -> dict:
    """GeoJSON do Brasil dividido por ``nivel`` ("UF" ou "regiao"); baixa só se ainda não estiver salvo."""
    caminho = PASTA / f"malha_{nivel.lower()}.json"
    if not caminho.exists():
        PASTA.mkdir(parents=True, exist_ok=True)
        log.info("Baixando a malha do IBGE (%s)", nivel)
        resposta = requests.get(URL, params={"formato": "application/vnd.geo+json", "qualidade": "minima",
                                             "intrarregiao": nivel}, headers=config.HEADERS, timeout=60)
        resposta.raise_for_status()
        caminho.write_text(resposta.text, encoding="utf-8")
    return json.loads(caminho.read_text(encoding="utf-8"))


def aneis(geometria: dict) -> list[np.ndarray]:
    """Contornos externos de um Polygon ou MultiPolygon do GeoJSON (os buracos são ignorados)."""
    if geometria["type"] == "Polygon":
        return [np.asarray(geometria["coordinates"][0])]
    if geometria["type"] == "MultiPolygon":
        return [np.asarray(p[0]) for p in geometria["coordinates"]]
    raise ValueError(f"geometria não suportada: {geometria['type']}")


def poligonos(nivel: str = "UF") -> dict[str, list[np.ndarray]]:
    """{sigla da UF (ou nome da região): [contornos]}."""
    nomes = SIGLA_IBGE if nivel == "UF" else REGIAO_IBGE
    return {nomes[f["properties"]["codarea"]]: aneis(f["geometry"]) for f in malha(nivel)["features"]}


def desenha(ax, valores: dict[str, float], cmap, norm, contorno_regioes: bool = True) -> None:
    """Pinta cada UF com ``cmap(norm(valor))``; UFs sem valor ficam em cinza claro."""
    for sigla, contornos in poligonos("UF").items():
        v = valores.get(sigla)
        cor = estilo.GRADE if v is None or np.isnan(v) else cmap(norm(v))
        for c in contornos:
            ax.add_patch(Polygon(c, closed=True, facecolor=cor, edgecolor=estilo.FUNDO, linewidth=0.5))
    if contorno_regioes:
        for contornos in poligonos("regiao").values():
            for c in contornos:
                ax.add_patch(Polygon(c, closed=True, fill=False, edgecolor=estilo.TINTA_SECUNDARIA, linewidth=0.9))
    ax.autoscale_view()
    ax.set_aspect(1 / np.cos(np.radians(15)))  # corrige a largura na latitude média do Brasil
    ax.axis("off")
