"""Scraper do TABNET/DATASUS (consultas por formulário POST).

O TABNET não expõe os dados por URL: cada consulta é um formulário HTML
(``deftohtm.exe?<arquivo>.def``) enviado por POST para ``tabcgi.exe?<arquivo>.def``.
O scraper:

1. baixa o formulário e lê as opções de cada <select> (os códigos das opções
   mudam entre versões, por isso não são fixados no código);
2. monta o POST com os filtros desejados (procedimento, causa, sexo, anos...);
3. salva o HTML do resultado em ``data/raw/datasus/`` e extrai a tabela.

Consultas realizadas (ver ``CONSULTAS``):
- SIA/SUS: mamografias diagnósticas e de rastreamento por UF e ano (mesma fonte das tabelas do INCA);
- SIM: óbitos de mulheres por câncer de mama por UF x ano e por faixa etária x ano.

Uso:
    python -m src.scraping.tabnet            # coleta (se necessário) e extrai
    python -m src.scraping.tabnet --forcar   # refaz todas as consultas
    python -m src.scraping.tabnet --offline  # só extrai, a partir do HTML salvo
"""

import argparse
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup, Tag

from src import config
from src.scraping.utils import baixa_html, limpa_numero

log = logging.getLogger(__name__)

TABNET = "http://tabnet.datasus.gov.br/cgi"
ANOS = range(config.ANO_INICIO, config.ANO_FIM + 1)


@dataclass
class Consulta:
    """Uma consulta TABNET. Os filtros usam o TEXTO das opções, não os códigos."""

    nome: str
    definicao: str            # ex.: "sim/cnv/obt10uf.def"
    linha: str                # rótulo da variável nas linhas
    coluna: str               # rótulo da variável nas colunas
    incremento: str           # medida (ex.: "Óbitos p/Residênc")
    arquivos: list[str]       # rótulos dos períodos (ex.: "2020" ou "Jan/2020")
    filtros: dict[str, list[str]] = field(default_factory=dict)  # select -> rótulos (prefixo)
    descricao: str = ""


def _meses(anos) -> list[str]:
    abrev = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    return [f"{m}/{a}" for a in anos for m in abrev]


CONSULTAS = [
    Consulta(
        nome="sia_mamografia_diagnostica_uf_ano",
        definicao="sia/cnv/qauf.def",
        linha="Região/Unidade da Federação",
        coluna="Ano processamento",
        incremento="Qtd.apresentada",
        arquivos=_meses(ANOS),
        filtros={"SProcedimento": ["0204030030"]},
        descricao="Mamografias com finalidade diagnóstica (0204030030) apresentadas no SIA/SUS",
    ),
    Consulta(
        nome="sia_mamografia_rastreamento_uf_ano",
        definicao="sia/cnv/qauf.def",
        linha="Região/Unidade da Federação",
        coluna="Ano processamento",
        incremento="Qtd.apresentada",
        arquivos=_meses(ANOS),
        filtros={"SProcedimento": ["0204030188"]},
        descricao="Mamografias bilaterais para rastreamento (0204030188) apresentadas no SIA/SUS",
    ),
    Consulta(
        nome="sim_obitos_mama_uf_ano",
        definicao="sim/cnv/obt10uf.def",
        linha="Região/Unidade da Federação",
        coluna="Ano do Óbito",
        incremento="Óbitos p/Residênc",
        arquivos=[str(a) for a in ANOS],
        filtros={"SCausa_-_CID-BR-10": [". 041 Neoplasia maligna da mama"], "SSexo": ["Fem"]},
        descricao="Óbitos de mulheres por neoplasia maligna da mama (CID-BR-10 041), por residência",
    ),
    Consulta(
        nome="sim_obitos_mama_faixa_ano",
        definicao="sim/cnv/obt10uf.def",
        linha="Faixa Etária",
        coluna="Ano do Óbito",
        incremento="Óbitos p/Residênc",
        arquivos=[str(a) for a in ANOS],
        filtros={"SCausa_-_CID-BR-10": [". 041 Neoplasia maligna da mama"], "SSexo": ["Fem"]},
        descricao="Óbitos de mulheres por neoplasia maligna da mama, por faixa etária",
    ),
]


# 1. Leitura do formulário e montagem do POST
def opcoes_do_formulario(html: str) -> dict[str, dict[str, str]]:
    """{nome_do_select: {rótulo: valor}} para todos os <select> do formulário."""
    form = BeautifulSoup(html, "lxml").find("form")
    if form is None:
        raise ValueError("Formulário não encontrado — a página do TABNET pode estar fora do ar.")
    return {
        sel["name"]: {op.get_text(" ", strip=True): op.get("value", "") for op in sel.find_all("option")}
        for sel in form.find_all("select")
        if sel.get("name")
    }


def _escolhe(opcoes: dict[str, str], rotulo: str, campo: str) -> str:
    """Valor da opção cujo texto é igual ao rótulo (ou começa com ele, ex.: código do procedimento)."""
    if rotulo in opcoes:
        return opcoes[rotulo]
    candidatos = [v for texto, v in opcoes.items() if texto.startswith(rotulo)]
    if len(candidatos) != 1:
        raise ValueError(f"{campo}: {len(candidatos)} opções correspondem a {rotulo!r}")
    return candidatos[0]


def monta_post(consulta: Consulta, opcoes: dict[str, dict[str, str]]) -> list[tuple[str, str]]:
    """Lista de pares (campo, valor) — o TABNET aceita o mesmo campo repetido (seleção múltipla)."""
    dados = [
        ("Linha", _escolhe(opcoes["Linha"], consulta.linha, "Linha")),
        ("Coluna", _escolhe(opcoes["Coluna"], consulta.coluna, "Coluna")),
        ("Incremento", _escolhe(opcoes["Incremento"], consulta.incremento, "Incremento")),
    ]
    faltando = [a for a in consulta.arquivos if a not in opcoes["Arquivos"]]
    if faltando:
        raise ValueError(f"Períodos indisponíveis no TABNET: {faltando}")
    dados += [("Arquivos", opcoes["Arquivos"][a]) for a in consulta.arquivos]

    # todos os outros filtros (S*) vão como "Todas as categorias", exceto os escolhidos
    for campo, ops in opcoes.items():
        if not campo.startswith("S"):
            continue
        if campo in consulta.filtros:
            dados += [(campo, _escolhe(ops, r, campo)) for r in consulta.filtros[campo]]
        else:
            dados.append((campo, "TODAS_AS_CATEGORIAS__"))

    dados += [("formato", "table"), ("mostre", "Mostra")]
    return dados


# 2. Coleta
def coletar(forcar: bool = False) -> None:
    config.RAW_DATASUS.mkdir(parents=True, exist_ok=True)
    metadados_path = config.RAW_DATASUS / "coleta.json"
    metadados = json.loads(metadados_path.read_text()) if metadados_path.exists() else {}
    formularios: dict[str, dict] = {}

    for consulta in CONSULTAS:
        destino = config.RAW_DATASUS / f"{consulta.nome}.html"
        if destino.exists() and not forcar:
            log.info("%s já coletada em %s", consulta.nome, metadados.get(consulta.nome, {}).get("coletado_em", "?"))
            continue

        if consulta.definicao not in formularios:
            url_form = f"{TABNET}/deftohtm.exe?{consulta.definicao}"
            log.info("Lendo formulário %s", url_form)
            formularios[consulta.definicao] = opcoes_do_formulario(baixa_html(url_form))

        dados = monta_post(consulta, formularios[consulta.definicao])
        url = f"{TABNET}/tabcgi.exe?{consulta.definicao}"
        log.info("Consultando %s", consulta.nome)
        html = baixa_html(url, metodo="post", dados=dados, pausa=2, codificacao_form="latin-1")
        tabela_resultado(html)  # não salva páginas de erro do TABNET
        destino.write_text(html, encoding="utf-8")
        metadados[consulta.nome] = {
            "url": url,
            "descricao": consulta.descricao,
            "post": dados,
            "coletado_em": datetime.now().isoformat(timespec="seconds"),
        }
        metadados_path.write_text(json.dumps(metadados, indent=2, ensure_ascii=False))


# 3. Extração da tabela de resultado
def tabela_resultado(html: str) -> Tag:
    soup = BeautifulSoup(html, "lxml")
    tabela = soup.find("table", class_="tabdados") or max(soup.find_all("table"), key=lambda t: len(t.find_all("tr")), default=None)
    if tabela is None or len(tabela.find_all("tr")) < 2:
        erro = soup.get_text(" ", strip=True)[:300]
        raise ValueError(f"Tabela de resultado não encontrada. Resposta do TABNET: {erro!r}")
    return tabela


def le_tabdados(tabela: Tag) -> tuple[list[str], list[list[str]], list[str]]:
    """Separa a tabela "tabdados" em (cabeçalho, linhas de dados, textos de título/notas).

    Além dos dados, a tabela traz em linhas de uma única célula o título da consulta
    (com os filtros aplicados) e as notas da fonte.
    """
    cabecalho, dados, textos = [], [], []
    for tr in tabela.find_all("tr"):
        celulas = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if tr.find("th"):
            cabecalho = celulas
        elif cabecalho and len(celulas) == len(cabecalho):
            dados.append(celulas)
        elif any(celulas):
            textos.append(" ".join(celulas))
    if not cabecalho or not dados:
        raise ValueError("Tabela do TABNET sem cabeçalho ou sem dados.")
    return cabecalho, dados, textos


def classifica_linha(rotulo: str) -> tuple[str, str]:
    """'.. Acre' / 'Região Norte' / 'TOTAL' -> (localidade, nível)."""
    nome = re.sub(r"^[\s.]+", "", rotulo).strip()   # UFs vêm indentadas com ".. "
    nome = re.sub(r"^Região\s+", "", nome)
    if nome.upper() == "TOTAL":
        return "Brasil", "brasil"
    if nome in config.REGIOES_UF:
        return nome, "regiao"
    if nome in config.UF_PARA_REGIAO:
        return nome, "uf"
    return nome, "categoria"


def extrair_consulta(consulta: Consulta) -> pd.DataFrame:
    caminho = config.RAW_DATASUS / f"{consulta.nome}.html"
    cabecalho, linhas, textos = le_tabdados(tabela_resultado(caminho.read_text(encoding="utf-8")))

    registros = []
    for linha in linhas:
        rotulo, nivel = classifica_linha(linha[0])
        for coluna, valor in zip(cabecalho[1:], linha[1:]):
            if coluna == "Total":
                continue
            registros.append({"rotulo_linha": rotulo, "nivel": nivel, "coluna": coluna, "valor": limpa_numero(valor)})
    df = pd.DataFrame(registros)

    if consulta.linha == "Região/Unidade da Federação":
        df = df.rename(columns={"rotulo_linha": "localidade"})
        df["regiao"] = df["localidade"].map(config.UF_PARA_REGIAO).fillna(
            df["localidade"].where(df["nivel"] == "regiao"))
    else:
        df = df.rename(columns={"rotulo_linha": "faixa_etaria"})
        df["localidade"], df["nivel"] = "Brasil", "brasil"
        df = df[df["faixa_etaria"] != "Brasil"]  # linha Total

    df = df.rename(columns={"coluna": "ano"})
    df["ano"] = df["ano"].astype(int)
    df["valor"] = df["valor"].fillna(0)  # "-" no TABNET = zero
    df["consulta"] = consulta.nome
    df["descricao"] = consulta.descricao
    df["fonte"] = next((t for t in textos if t.startswith("Fonte")), "")
    return df


def extrair() -> dict[str, pd.DataFrame]:
    config.INTERIM.mkdir(parents=True, exist_ok=True)
    resultados = {}
    for consulta in CONSULTAS:
        df = extrair_consulta(consulta)
        destino = config.INTERIM / f"datasus_{consulta.nome}.csv"
        df.to_csv(destino, index=False)
        log.info("Salvo %s (%d linhas)", destino.relative_to(config.ROOT), len(df))
        resultados[consulta.nome] = df
    comparar_com_inca(resultados)
    return resultados


def comparar_com_inca(resultados: dict[str, pd.DataFrame]) -> None:
    """Confere os totais do SIA com a tabela 4 do INCA (mesma fonte original).

    O INCA conta só mulheres; o formulário qauf do SIA não tem filtro de sexo,
    então espera-se que o TABNET fique um pouco acima.
    """
    inca_csv = config.INTERIM / "inca_mamografias_sus.csv"
    if not inca_csv.exists():
        log.info("Comparação com o INCA pulada (rode antes: python -m src.scraping.inca)")
        return
    inca = pd.read_csv(inca_csv).query("nivel == 'brasil' and tabela == 4")
    sia = resultados["sia_mamografia_diagnostica_uf_ano"].query("nivel == 'brasil'")
    comp = sia.set_index("ano")["valor"].rename("tabnet").to_frame().join(inca.set_index("ano")["valor"].rename("inca"))
    comp["dif_%"] = (100 * (comp["tabnet"] - comp["inca"]) / comp["inca"]).round(2)
    log.info("Mamografias diagnósticas, Brasil — TABNET x INCA (tabela 4):\n%s", comp.to_string())


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
