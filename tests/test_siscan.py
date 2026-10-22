import pytest

from src.scraping.siscan import ConsultaSiscan, campos_ocultos, densidade_do_filtro, le_google_datatable, monta_post
from src.scraping.tabnet import opcoes_do_formulario

FORM = """
<form name="Form1">
  <select name="Linha"><option value="Tipo mama dir|TP_MAMA_DIR|1|siscan\\tipo.cnv">Tipo mama dir</option>
    <option value="BI-RADS|CO_BIRADS|1|siscan\\birads.cnv">BI-RADS</option></select>
  <select name="Coluna"><option value="Ano competencia|NU_ANO|1|CITO\\ano.cnv">Ano competencia</option></select>
  <select name="Incremento" multiple><option value="Exames|=count(*)">Exames</option></select>
  <select name="PAno competencia" multiple><option value="2022|2022|4">2022</option>
    <option value="2021|2021|4">2021</option></select>
  <select name="SUF de residencia" multiple><option value="TODAS_AS_CATEGORIAS__">Todas as categorias</option></select>
  <select name="XSexo" multiple><option value="TODAS_AS_CATEGORIAS__">Todas as categorias</option>
    <option value="Masculino|M|1">Masculino</option><option value="Feminino|F|1">Feminino</option></select>
  <select name="listahidden1" multiple></select>
  <input type="hidden" name="nomedef" value="siscan/mamografia_residbr.def">
</form>
"""

RESULTADO = """
<script>
  data.addColumn('string','Tipo mama dir');
  data.addColumn('number','2021');
  data.addColumn('number','2022');
  data.addColumn('number',' Total');
  data.addRows([
     [" Total" ,{v: 30.0 ,f: '30'} ,{v: 70.0 ,f: '70'} ,{v: 100.0 ,f: '100'} ]
   , ["Densa" ,{v: 10.0 ,f: '10'} ,{v: 20.0 ,f: '20'} ,{v: 30.0 ,f: '30'} ]
   , ["Adiposa" ,{v: 20.0 ,f: '20'} ,{v: null ,f: '-'} ,{v: 20.0 ,f: '20'} ]
  ]);
</script>
"""


def test_le_google_datatable():
    colunas, linhas = le_google_datatable(RESULTADO)
    assert colunas == ["Tipo mama dir", "2021", "2022", "Total"]
    assert linhas[0] == ["Total", 30.0, 70.0, 100.0]
    assert linhas[2] == ["Adiposa", 20.0, None, 20.0]


def test_le_google_datatable_sem_dados():
    with pytest.raises(ValueError, match="sem tabela"):
        le_google_datatable("<html><body>Nenhum registro</body></html>")


def test_monta_post():
    consulta = ConsultaSiscan("t", "Tipo mama dir", "Ano competencia", "teste", anos=["2021", "2022"])
    dados = monta_post(consulta, opcoes_do_formulario(FORM), campos_ocultos(FORM))
    assert ("Linha", "Tipo mama dir|TP_MAMA_DIR|1|siscan\\tipo.cnv") in dados
    assert [v for k, v in dados if k == "PAno competencia"] == ["2021|2021|4", "2022|2022|4"]
    assert ("XSexo", "Feminino|F|1") in dados                     # filtro padrão: só mulheres
    assert ("SUF de residencia", "TODAS_AS_CATEGORIAS__") in dados
    assert ("nomedef", "siscan/mamografia_residbr.def") in dados  # campo oculto do formulário
    assert not any(k == "listahidden1" for k, _ in dados)


def test_densidade_do_filtro():
    assert densidade_do_filtro(ConsultaSiscan("t", "UF de residencia", "Faixa etária", "teste",
                                              filtros={"XTipo mama dir": ["Densa"]})) == 4
    assert densidade_do_filtro(ConsultaSiscan("t", "UF de residencia", "Faixa etária", "teste")) is None


def test_monta_post_ano_indisponivel():
    consulta = ConsultaSiscan("t", "Tipo mama dir", "Ano competencia", "teste", anos=["2010"])
    with pytest.raises(ValueError, match="2010"):
        monta_post(consulta, opcoes_do_formulario(FORM), campos_ocultos(FORM))
