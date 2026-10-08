"""Caminhos e URLs centralizados do projeto."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_INCA = RAW / "inca"
RAW_DATASUS = RAW / "datasus"
RAW_CBIS = RAW / "cbis-ddsm"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
FIGURES = ROOT / "reports" / "figures"

# Período de análise dos dados brasileiros
ANO_INICIO = 2018
ANO_FIM = 2022

# Fontes brasileiras — conferir as URLs na etapa de análise da estrutura das páginas
URLS = {
    "inca_dados_numeros": (
        "https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/"
        "controle-do-cancer-de-mama/dados-e-numeros"
    ),
    "tabnet_home": "https://datasus.saude.gov.br/informacoes-de-saude-tabnet/",
    # TODO: preencher com o endpoint tabcgi.exe da consulta de mamografias (SISCAN)
    "tabnet_siscan_mamografia": None,
}

# CSVs de metadados do CBIS-DDSM
CBIS_FILES = {
    "mass_train": "mass_case_description_train_set.csv",
    "mass_test": "mass_case_description_test_set.csv",
    "calc_train": "calc_case_description_train_set.csv",
    "calc_test": "calc_case_description_test_set.csv",
}

REGIOES_UF = {
    "Norte": ["Acre", "Amapá", "Amazonas", "Pará", "Rondônia", "Roraima", "Tocantins"],
    "Nordeste": ["Alagoas", "Bahia", "Ceará", "Maranhão", "Paraíba", "Pernambuco",
                 "Piauí", "Rio Grande do Norte", "Sergipe"],
    "Sudeste": ["Espírito Santo", "Minas Gerais", "Rio de Janeiro", "São Paulo"],
    "Sul": ["Paraná", "Rio Grande do Sul", "Santa Catarina"],
    "Centro-Oeste": ["Distrito Federal", "Goiás", "Mato Grosso", "Mato Grosso do Sul"],
}
UF_PARA_REGIAO = {uf: regiao for regiao, ufs in REGIOES_UF.items() for uf in ufs}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (projeto academico CEFET-MG - Ciencia dos Dados)"
    )
}
