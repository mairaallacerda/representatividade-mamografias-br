"""Funções auxiliares de coleta (requisições e parsing de tabelas HTML)."""

import logging
import re
import time

import requests
from bs4 import Tag

from src import config

log = logging.getLogger(__name__)


def baixa_html(
    url: str,
    metodo: str = "get",
    dados: dict | None = None,
    pausa: float = 1.0,
    tentativas: int = 3,
) -> str:
    """Baixa uma página via GET ou POST (formulários do TABNET), com novas tentativas."""
    for tentativa in range(1, tentativas + 1):
        time.sleep(pausa)  # evita sobrecarregar os servidores públicos
        try:
            resp = requests.request(metodo, url, data=dados, headers=config.HEADERS, timeout=60)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text
        except requests.RequestException as erro:
            log.warning("Falha ao baixar %s (tentativa %d/%d): %s", url, tentativa, tentativas, erro)
            if tentativa == tentativas:
                raise
            pausa *= 2


def limpa_numero(texto: str) -> float | None:
    """Converte '1.234,5' ou '-' (padrão TABNET) em número."""
    texto = texto.strip()
    if texto in {"", "-", "..."}:
        return None
    texto = re.sub(r"[^\d,.-]", "", texto).replace(".", "").replace(",", ".")
    return float(texto) if texto else None


def linhas_da_tabela(tabela: Tag) -> list[list[str]]:
    """Texto das células de uma <table>, linha a linha, sem colunas totalmente vazias."""
    linhas = [
        [cel.get_text(" ", strip=True) for cel in tr.find_all(["th", "td"])]
        for tr in tabela.find_all("tr")
    ]
    linhas = [l for l in linhas if any(l)]
    n_colunas = max(len(l) for l in linhas)
    linhas = [l + [""] * (n_colunas - len(l)) for l in linhas]
    # algumas tabelas do gov.br têm colunas "espaçadoras" vazias
    usadas = [j for j in range(n_colunas) if any(l[j] for l in linhas)]
    return [[l[j] for j in usadas] for l in linhas]
