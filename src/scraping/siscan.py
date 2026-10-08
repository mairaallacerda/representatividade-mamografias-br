"""Scraper do SISCAN (Sistema de Informação do Câncer): laudos de mamografia no TabnetBD.

O SISCAN usa uma versão mais nova do TABNET ("TabnetBD"), diferente do SIA/SIM:

| Etapa      | SIA/SIM (``tabnet.py``)          | SISCAN (este módulo)                          |
|------------|----------------------------------|-----------------------------------------------|
| Formulário | ``deftohtm.exe?<def>``           | ``dhdat.exe?<def>``                           |
| Envio      | POST ``tabcgi.exe``              | POST ``webtabx.exe`` (montado por JavaScript) |
| Períodos   | campo ``Arquivos``               | campo ``PAno competencia``                    |
| Filtros    | campos ``S...``                  | campos ``S...`` e ``X...``                    |
| Resultado  | ``<table class="tabdados">``     | **dentro de um <script>** (Google Charts)     |

Uso:
    python -m src.scraping.siscan            # coleta (se necessário) e extrai
    python -m src.scraping.siscan --forcar   # refaz todas as consultas
    python -m src.scraping.siscan --offline  # só extrai, a partir do HTML salvo
"""

import argparse
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup

from src import config
from src.scraping.tabnet import _escolhe, opcoes_do_formulario
from src.scraping.utils import baixa_html

log = logging.getLogger(__name__)

TABNET = "http://tabnet.datasus.gov.br/cgi"
DEFINICAO = "siscan/mamografia_residbr.def"   # por local de residência, Brasil
ANOS = [str(a) for a in range(config.ANO_INICIO, config.ANO_FIM + 1)]
SO_MULHERES = {"XSexo": ["Feminino"]}

# Tipo de mama do laudo SISCAN -> categoria de densidade BI-RADS (1 a 4), a mesma escala do CBIS-DDSM
DENSIDADE_BIRADS = {
    "Adiposa": 1,
    "Predominantemente Adiposa": 2,
    "Predominantemente Densa": 3,
    "Densa": 4,
}


@dataclass
class ConsultaSiscan:
    nome: str
    linha: str
    coluna: str
    descricao: str
    filtros: dict[str, list[str]] = field(default_factory=lambda: dict(SO_MULHERES))
    incremento: str = "Exames"
    anos: list[str] = field(default_factory=lambda: list(ANOS))


CONSULTAS = [
    ConsultaSiscan("siscan_densidade_ano", "Tipo mama dir", "Ano competencia",
                   "Mamografias por tipo de mama (densidade), mama direita, por ano"),
    ConsultaSiscan("siscan_densidade_esq_ano", "Tipo mama esq", "Ano competencia",
                   "Mamografias por tipo de mama (densidade), mama esquerda, por ano (validação)"),
    ConsultaSiscan("siscan_densidade_faixa", "Tipo mama dir", "Faixa etária",
                   "Mamografias por tipo de mama (densidade) e faixa etária, 2018–2022"),
    ConsultaSiscan("siscan_densidade_indicacao", "Tipo mama dir", "Ind Clinica",
                   "Mamografias por tipo de mama (densidade) e indicação clínica, 2018–2022"),
    ConsultaSiscan("siscan_birads_ano", "BI-RADS", "Ano competencia",
                   "Mamografias por categoria BI-RADS, por ano"),
    ConsultaSiscan("siscan_birads_indicacao", "BI-RADS", "Ind Clinica",
                   "Mamografias por categoria BI-RADS e indicação clínica, 2018–2022"),
    ConsultaSiscan("siscan_birads_densidade", "BI-RADS", "Tipo mama dir",
                   "Mamografias por categoria BI-RADS e tipo de mama (densidade), 2018–2022"),
]


# 1. Montagem do POST
def campos_ocultos(html: str) -> list[tuple[str, str]]:
    form = BeautifulSoup(html, "lxml").find("form")
    return [(i["name"], i.get("value", "")) for i in form.find_all("input", type="hidden") if i.get("name")]


def monta_post(consulta: ConsultaSiscan, opcoes: dict[str, dict[str, str]],
               ocultos: list[tuple[str, str]]) -> list[tuple[str, str]]:
    dados = [
        ("Linha", _escolhe(opcoes["Linha"], consulta.linha, "Linha")),
        ("Coluna", _escolhe(opcoes["Coluna"], consulta.coluna, "Coluna")),
        ("Incremento", _escolhe(opcoes["Incremento"], consulta.incremento, "Incremento")),
    ]
    periodos = opcoes["PAno competencia"]
    faltando = [a for a in consulta.anos if a not in periodos]
    if faltando:
        raise ValueError(f"Anos indisponíveis no SISCAN: {faltando}")
    dados += [("PAno competencia", periodos[a]) for a in consulta.anos]

    for campo, ops in opcoes.items():
        if campo[:1] not in {"S", "X"}:
            continue
        if campo in consulta.filtros:
            dados += [(campo, _escolhe(ops, r, campo)) for r in consulta.filtros[campo]]
        else:
            dados.append((campo, "TODAS_AS_CATEGORIAS__"))
    return dados + ocultos + [("grafico", "")]


# 2. Leitura do resultado (dados dentro do JavaScript)
def le_google_datatable(html: str) -> tuple[list[str], list[list]]:
    """Extrai colunas e linhas de ``data.addColumn(...)`` / ``data.addRows([...])``.

    Cada célula numérica vem como ``{v: 424656.0 ,f: '424.656'}``; usamos ``v`` (valor bruto).
    """
    colunas = re.findall(r"addColumn\(\s*'(?:string|number)'\s*,\s*'([^']*)'\s*\)", html)
    bloco = re.search(r"addRows\(\s*\[(.*?)\]\s*\)\s*;", html, re.S)
    if not colunas or not bloco:
        texto = BeautifulSoup(html, "lxml").get_text(" ", strip=True)[:300]
        raise ValueError(f"Resultado do SISCAN sem tabela de dados. Resposta: {texto!r}")

    linhas = []
    for rotulo, celulas in re.findall(r'\[\s*"([^"]*)"\s*,(.*?)\]', bloco.group(1), re.S):
        valores = [None if v == "null" else float(v) for v in re.findall(r"\{\s*v:\s*([-\d.]+|null)", celulas)]
        if len(valores) != len(colunas) - 1:
            raise ValueError(f"Linha {rotulo!r} com {len(valores)} valores; esperado {len(colunas) - 1}")
        linhas.append([rotulo.strip(), *valores])
    return [c.strip() for c in colunas], linhas


# 3. Coleta e extração
def coletar(forcar: bool = False) -> None:
    config.RAW_DATASUS.mkdir(parents=True, exist_ok=True)
    metadados_path = config.RAW_DATASUS / "coleta_siscan.json"
    metadados = json.loads(metadados_path.read_text()) if metadados_path.exists() else {}

    pendentes = [c for c in CONSULTAS if forcar or not (config.RAW_DATASUS / f"{c.nome}.html").exists()]
    if not pendentes:
        log.info("Todas as consultas do SISCAN já coletadas (use --forcar para refazer)")
        return

    url_form = f"{TABNET}/dhdat.exe?{DEFINICAO}"
    log.info("Lendo formulário %s", url_form)
    html_form = baixa_html(url_form)
    opcoes, ocultos = opcoes_do_formulario(html_form), campos_ocultos(html_form)

    url = f"{TABNET}/webtabx.exe?{DEFINICAO}"
    for consulta in pendentes:
        dados = monta_post(consulta, opcoes, ocultos)
        log.info("Consultando %s", consulta.nome)
        html = baixa_html(url, metodo="post", dados=dados, pausa=2, codificacao_form="latin-1")
        le_google_datatable(html)  # não salva páginas de erro
        (config.RAW_DATASUS / f"{consulta.nome}.html").write_text(html, encoding="utf-8")
        metadados[consulta.nome] = {
            "url": url, "descricao": consulta.descricao, "post": dados,
            "coletado_em": datetime.now().isoformat(timespec="seconds"),
        }
        metadados_path.write_text(json.dumps(metadados, indent=2, ensure_ascii=False))


def extrair_consulta(consulta: ConsultaSiscan) -> pd.DataFrame:
    html = (config.RAW_DATASUS / f"{consulta.nome}.html").read_text(encoding="utf-8")
    colunas, linhas = le_google_datatable(html)
    df = (pd.DataFrame(linhas, columns=["linha", *colunas[1:]])
          .melt(id_vars="linha", var_name="coluna", value_name="exames"))
    df = df[(df["linha"] != "Total") & (df["coluna"] != "Total")].copy()
    df["exames"] = df["exames"].fillna(0)
    df.insert(0, "var_linha", consulta.linha)
    df.insert(2, "var_coluna", consulta.coluna)
    for var, col in [(consulta.linha, "linha"), (consulta.coluna, "coluna")]:
        if var.startswith("Tipo mama"):
            df[f"densidade_birads_{col}"] = df[col].map(DENSIDADE_BIRADS)
    df["consulta"] = consulta.nome
    df["descricao"] = consulta.descricao
    return df


def validar(df: pd.DataFrame, html: str, nome: str) -> None:
    """O total geral da fonte deve bater com a soma das células extraídas."""
    _, linhas = le_google_datatable(html)
    total_fonte = next(l[-1] for l in linhas if l[0] == "Total")
    if abs(df["exames"].sum() - total_fonte) > 0.5:
        log.warning("[%s] soma extraída %s != total da fonte %s", nome, f"{df['exames'].sum():,.0f}", f"{total_fonte:,.0f}")


def extrair() -> dict[str, pd.DataFrame]:
    config.INTERIM.mkdir(parents=True, exist_ok=True)
    resultados = {}
    for consulta in CONSULTAS:
        df = extrair_consulta(consulta)
        validar(df, (config.RAW_DATASUS / f"{consulta.nome}.html").read_text(encoding="utf-8"), consulta.nome)
        destino = config.INTERIM / f"{consulta.nome}.csv"
        df.to_csv(destino, index=False)
        log.info("Salvo %s (%d linhas)", destino.relative_to(config.ROOT), len(df))
        resultados[consulta.nome] = df
    return resultados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--forcar", action="store_true", help="refaz as consultas mesmo se já existirem")
    parser.add_argument("--offline", action="store_true", help="não acessa a internet; usa o HTML salvo")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not args.offline:
        coletar(forcar=args.forcar)
    extrair()


if __name__ == "__main__":
    main()
