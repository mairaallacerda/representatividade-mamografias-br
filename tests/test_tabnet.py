import pytest
from bs4 import BeautifulSoup

from src.scraping.tabnet import Consulta, classifica_linha, le_tabdados, monta_post, opcoes_do_formulario

FORM = """
<form action="/cgi/tabcgi.exe?sim/cnv/obt10uf.def" method="POST">
  <select name="Linha"><option value="Região">Região</option>
    <option value="Faixa_Etária">Faixa Etária</option></select>
  <select name="Coluna"><option value="Ano_do_Óbito">Ano do Óbito</option></select>
  <select name="Incremento" multiple><option value="Óbitos_p/Residênc">Óbitos p/Residênc</option></select>
  <select name="Arquivos" multiple><option value="obtuf22.dbf">2022</option>
    <option value="obtuf21.dbf">2021</option></select>
  <select name="SSexo" multiple><option value="TODAS_AS_CATEGORIAS__">Todas as categorias</option>
    <option value="1">Masc</option><option value="2">Fem</option></select>
  <select name="SProcedimento" multiple><option value="TODAS_AS_CATEGORIAS__">Todas as categorias</option>
    <option value="10">0204030030 MAMOGRAFIA</option>
    <option value="11">0204030188 MAMOGRAFIA BILATERAL PARA RASTREAMENTO</option></select>
  <select name="listahidden2" multiple></select>
</form>
"""

RESULTADO = """
<table class="tabdados">
  <tr><td>Mortalidade - Brasil Óbitos p/Residênc por Ano do Óbito segundo Faixa Etária</td></tr>
  <tr><th>Região/Unidade da Federação</th><th>2021</th><th>2022</th><th>Total</th></tr>
  <tr><td>Fonte: MS/SVSA/CGIAE - SIM</td></tr>
  <tr><td>TOTAL</td><td>1.000</td><td>-</td><td>1.000</td></tr>
  <tr><td>Região Norte</td><td>1.000</td><td>-</td><td>1.000</td></tr>
  <tr><td>.. Acre</td><td>1.000</td><td>-</td><td>1.000</td></tr>
</table>
"""


@pytest.fixture
def opcoes():
    return opcoes_do_formulario(FORM)


def test_opcoes_do_formulario(opcoes):
    assert opcoes["SSexo"]["Fem"] == "2"
    assert opcoes["Arquivos"] == {"2022": "obtuf22.dbf", "2021": "obtuf21.dbf"}


def test_monta_post(opcoes):
    consulta = Consulta(
        nome="teste", definicao="sim/cnv/obt10uf.def", linha="Faixa Etária", coluna="Ano do Óbito",
        incremento="Óbitos p/Residênc", arquivos=["2021", "2022"],
        filtros={"SSexo": ["Fem"], "SProcedimento": ["0204030188"]},
    )
    dados = monta_post(consulta, opcoes)
    assert ("Linha", "Faixa_Etária") in dados
    assert [v for k, v in dados if k == "Arquivos"] == ["obtuf21.dbf", "obtuf22.dbf"]
    assert ("SSexo", "2") in dados
    assert ("SProcedimento", "11") in dados  # escolhido pelo prefixo (código do procedimento)
    assert not any(k == "listahidden2" for k, _ in dados)


def test_monta_post_periodo_indisponivel(opcoes):
    consulta = Consulta(nome="t", definicao="x", linha="Região", coluna="Ano do Óbito",
                        incremento="Óbitos p/Residênc", arquivos=["1990"])
    with pytest.raises(ValueError, match="1990"):
        monta_post(consulta, opcoes)


def test_le_tabdados_separa_titulo_e_notas():
    tabela = BeautifulSoup(RESULTADO, "lxml").find("table")
    cabecalho, dados, textos = le_tabdados(tabela)
    assert cabecalho == ["Região/Unidade da Federação", "2021", "2022", "Total"]
    assert len(dados) == 3
    assert any(t.startswith("Fonte") for t in textos)


@pytest.mark.parametrize("rotulo, esperado", [
    ("TOTAL", ("Brasil", "brasil")),
    ("Região Norte", ("Norte", "regiao")),
    (".. Acre", ("Acre", "uf")),
    ("15 a 19 anos", ("15 a 19 anos", "categoria")),
])
def test_classifica_linha(rotulo, esperado):
    assert classifica_linha(rotulo) == esperado
