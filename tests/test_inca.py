import pytest
from bs4 import BeautifulSoup

from src.scraping.inca import anos_do_texto, classifica_localidade, tabela_para_longo, titulo_da_tabela
from src.scraping.utils import limpa_numero, linhas_da_tabela

HTML = """
<div id="content-core">
  <p><strong>Tabela 2</strong></p>
  <p>Tabela 2 . Número de mamografias de rastreamento em mulheres de 50 a 69 anos, 2018 a 2019</p>
  <table>
    <tr><td>Região/Unidade da Federação</td><td>2018</td><td></td><td>2019</td></tr>
    <tr><td>Região Norte</td><td>1.000</td><td></td><td>2.000</td></tr>
    <tr><td>Acre</td><td>1.000</td><td></td><td>-</td></tr>
    <tr><td>Total</td><td>1.000</td><td></td><td>2.000</td></tr>
  </table>
</div>
"""


@pytest.fixture
def tabela():
    return BeautifulSoup(HTML, "lxml").find("table")


@pytest.mark.parametrize("texto, esperado", [
    ("1.234.567", 1234567.0),
    ("24,99", 24.99),
    ("-", None),
    ("", None),
])
def test_limpa_numero(texto, esperado):
    assert limpa_numero(texto) == esperado


def test_linhas_da_tabela_remove_coluna_vazia(tabela):
    assert linhas_da_tabela(tabela)[0] == ["Região/Unidade da Federação", "2018", "2019"]


def test_titulo_da_tabela(tabela):
    assert titulo_da_tabela(tabela).startswith("Tabela 2. Número de mamografias")


@pytest.mark.parametrize("texto, esperado", [
    ("Brasil, Regiões e UF, 2018 a 2022", [2018, 2019, 2020, 2021, 2022]),
    ("estimadas para o ano de 2023", [2023]),
])
def test_anos_do_texto(texto, esperado):
    assert anos_do_texto(texto) == esperado


@pytest.mark.parametrize("nome, esperado", [
    ("Região Norte", ("Norte", "regiao")),
    ("Total", ("Brasil", "brasil")),
    ("São Paulo", ("São Paulo", "uf")),
])
def test_classifica_localidade(nome, esperado):
    assert classifica_localidade(nome) == esperado


def test_classifica_localidade_desconhecida():
    with pytest.raises(ValueError):
        classifica_localidade("Atlântida")


def test_tabela_para_longo(tabela):
    df = tabela_para_longo(tabela, "ano")
    assert len(df) == 6
    acre = df[(df["localidade"] == "Acre")].set_index("ano")["valor"]
    assert acre["2018"] == 1000 and acre.isna()["2019"]
    assert set(df.loc[df["localidade"] == "Acre", "regiao"]) == {"Norte"}
