"""Funções auxiliares de coleta (requisições e parsing de tabelas HTML)."""

import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src import config


def baixa_html(url: str, metodo: str = "get", dados: dict | None = None, pausa: float = 1.0) -> str:
    """Baixa uma página via GET ou POST (formulários do TABNET)."""
    time.sleep(pausa)  # evita sobrecarregar os servidores públicos
    resp = requests.request(metodo, url, data=dados, headers=config.HEADERS, timeout=60)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def limpa_numero(texto: str) -> float | None:
    """Converte '1.234,5' ou '-' (padrão TABNET) em número."""
    texto = texto.strip()
    if texto in {"", "-", "..."}:
        return None
    texto = re.sub(r"[^\d,.-]", "", texto).replace(".", "").replace(",", ".")
    return float(texto) if texto else None


def tabela_html_para_df(html: str, indice: int = 0) -> pd.DataFrame:
    """Extrai a n-ésima <table> do HTML para um dataframe de strings."""
    soup = BeautifulSoup(html, "lxml")
    tabelas = soup.find_all("table")
    if not tabelas:
        raise ValueError("Nenhuma tabela encontrada na página.")
    linhas = [
        [cel.get_text(strip=True) for cel in tr.find_all(["th", "td"])]
        for tr in tabelas[indice].find_all("tr")
    ]
    linhas = [l for l in linhas if l]
    return pd.DataFrame(linhas[1:], columns=linhas[0])
