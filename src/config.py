"""Caminhos e URLs centralizados do projeto."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"
RAW = DATA / "raw"
RAW_INCA = RAW / "inca"
RAW_DATASUS = RAW / "datasus"
RAW_CBIS = RAW / "cbis-ddsm"
CBIS_JPEG = RAW_CBIS / "jpeg"  # pode ser um link simbólico para as imagens baixadas do Kaggle (~6 GB)
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
FIGURES = ROOT / "reports" / "figures"

ANO_INICIO = 2018
ANO_FIM = 2022

URLS = {
    "inca_dados_numeros": (
        "https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/"
        "controle-do-cancer-de-mama/dados-e-numeros"
    ),
    "tabnet_home": "https://datasus.saude.gov.br/informacoes-de-saude-tabnet/",
}

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
