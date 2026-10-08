"""Scraper das páginas "Dados e números" do controle do câncer de mama (INCA).

A coleta é feita em duas etapas independentes:

1. ``coletar``: baixa o HTML bruto de cada página para ``data/raw/inca/``.
2. ``extrair``: lê o HTML salvo e gera CSVs em formato longo (tidy) em ``data/interim/``.

Assim é possível reprocessar os dados sem acessar o site de novo.

Uso:
    python -m src.scraping.inca            # baixa (se necessário) e extrai
    python -m src.scraping.inca --forcar   # baixa tudo de novo
    python -m src.scraping.inca --offline  # só extrai, a partir do HTML já salvo
"""

import argparse
import json
import logging
import re
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup, Tag

from src import config
from src.scraping.utils import baixa_html, limpa_numero, linhas_da_tabela

log = logging.getLogger(__name__)

BASE = config.URLS["inca_dados_numeros"]
PAGINAS = {
    "incidencia": f"{BASE}/incidencia",
    "mamografias-no-sus": f"{BASE}/mamografias-no-sus",
    "mortalidade": f"{BASE}/mortalidade",
}

REGIOES = set(config.REGIOES_UF)


# ---------------------------------------------------------------
# 1. Coleta (HTML bruto)
# ---------------------------------------------------------------
def coletar(forcar: bool = False) -> None:
    config.RAW_INCA.mkdir(parents=True, exist_ok=True)
    metadados_path = config.RAW_INCA / "coleta.json"
    metadados = json.loads(metadados_path.read_text()) if metadados_path.exists() else {}

    for nome, url in PAGINAS.items():
        destino = config.RAW_INCA / f"{nome}.html"
        if destino.exists() and not forcar:
            log.info("%s já coletada em %s (use --forcar para baixar de novo)",
                     nome, metadados.get(nome, {}).get("coletado_em", "?"))
            continue
        log.info("Baixando %s", url)
        destino.write_text(baixa_html(url), encoding="utf-8")
        metadados[nome] = {"url": url, "coletado_em": datetime.now().isoformat(timespec="seconds")}

    metadados_path.write_text(json.dumps(metadados, indent=2, ensure_ascii=False))


def _conteudo(nome: str) -> Tag:
    """Corpo principal da página salva (ignora menu, rodapé etc.)."""
    caminho = config.RAW_INCA / f"{nome}.html"
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho} não encontrado. Rode sem --offline para coletar.")
    soup = BeautifulSoup(caminho.read_text(encoding="utf-8"), "lxml")
    return soup.find(id="content-core") or soup


# ---------------------------------------------------------------
# Auxiliares de parsing
# ---------------------------------------------------------------
def titulo_da_tabela(tabela: Tag) -> str:
    """O título ("Tabela N. Número de ...") fica em um parágrafo antes da <table>."""
    for el in tabela.find_all_previous(["p", "h2", "h3", "h4", "strong", "span", "div"], limit=10):
        texto = el.get_text(" ", strip=True)
        if re.match(r"^Tabela\s*\d+\s*\.\s*\S", texto) and len(texto) > 25:
            return re.sub(r"\s+\.", ".", texto)
    return ""


def anos_do_texto(texto: str) -> list[int]:
    """'..., 2018 a 2022' -> [2018, ..., 2022]; '..., 2022' -> [2022]."""
    intervalo = re.search(r"(20\d\d)\s*a\s*(20\d\d)", texto)
    if intervalo:
        inicio, fim = map(int, intervalo.groups())
        return list(range(inicio, fim + 1))
    return [int(a) for a in re.findall(r"\b(20\d\d)\b", texto)]


def classifica_localidade(nome: str) -> tuple[str, str]:
    """Padroniza o nome e diz o nível: ('Norte', 'regiao'), ('Acre', 'uf'), ('Brasil', 'brasil')."""
    nome = re.sub(r"^Região\s+", "", nome.strip())
    if nome in {"Brasil", "Total"}:
        return "Brasil", "brasil"
    if nome in REGIOES:
        return nome, "regiao"
    if nome in config.UF_PARA_REGIAO:
        return nome, "uf"
    raise ValueError(f"Localidade desconhecida: {nome!r} — o layout da página pode ter mudado.")


def tabela_para_longo(tabela: Tag, var_coluna: str) -> pd.DataFrame:
    """Converte a tabela larga (localidade x colunas) para o formato longo.

    ``var_coluna`` é o nome da variável que está nas colunas (ex.: 'ano', 'faixa_etaria').
    A coluna 'Total' é descartada — ela é usada apenas em ``validar``.
    """
    cabecalho, *linhas = linhas_da_tabela(tabela)
    registros = []
    for linha in linhas:
        localidade, nivel = classifica_localidade(linha[0])
        for coluna, valor in zip(cabecalho[1:], linha[1:]):
            if coluna.strip().lower() == "total":
                continue
            registros.append({
                "localidade": localidade,
                "nivel": nivel,
                "regiao": config.UF_PARA_REGIAO.get(localidade, localidade if nivel == "regiao" else None),
                var_coluna: coluna,
                "valor": limpa_numero(valor),
            })
    return pd.DataFrame(registros)


# ---------------------------------------------------------------
# 2. Extração por página
# ---------------------------------------------------------------
def extrair_incidencia() -> pd.DataFrame:
    tabela = _conteudo("incidencia").find("table")
    titulo = titulo_da_tabela(tabela)
    df = tabela_para_longo(tabela, "indicador")
    df["indicador"] = df["indicador"].map({
        "Nº de casos": "casos_estimados",
        "Taxa bruta": "taxa_bruta_100mil",
        "Taxa ajustada": "taxa_ajustada_100mil",
    })
    df["ano"] = anos_do_texto(titulo)[0]
    df["titulo"] = titulo
    df["fonte"] = PAGINAS["incidencia"]
    return df


def extrair_mamografias_sus() -> pd.DataFrame:
    """As 5 tabelas da página, empilhadas em um único dataframe longo.

    - Tabela 1: tipo de procedimento x região, 2022
    - Tabelas 2 e 4: rastreamento / diagnóstica x UF, 2018 a 2022
    - Tabelas 3 e 5: rastreamento / diagnóstica x UF x faixa etária, 2022
    """
    partes = []
    for i, tabela in enumerate(_conteudo("mamografias-no-sus").find_all("table"), start=1):
        titulo = titulo_da_tabela(tabela)
        anos = anos_do_texto(titulo)
        cabecalho = linhas_da_tabela(tabela)[0]

        if all(re.fullmatch(r"20\d\d", c) for c in cabecalho[1:]):
            df = tabela_para_longo(tabela, "ano")
            df["ano"] = df["ano"].astype(int)
            df["faixa_etaria"] = "todas" if "todas as faixas" in titulo else (
                "50 a 69" if "50 a 69" in titulo else None)
        elif "faixa etária" in titulo:
            df = tabela_para_longo(tabela, "faixa_etaria")
            df["ano"] = anos[0]
        else:  # Tabela 1: colunas são os tipos de mamografia
            df = tabela_para_longo(tabela, "tipo_procedimento")
            df["ano"] = anos[0]
            df["faixa_etaria"] = "todas"

        if "rastreamento" in titulo:
            df["tipo_procedimento"] = "Mamografia de rastreamento"
        elif "diagnóstica" in titulo:
            df["tipo_procedimento"] = "Mamografia"
        df["finalidade"] = df["tipo_procedimento"].map({
            "Mamografia": "diagnostica",
            "Mamografia de rastreamento": "rastreamento",
        })
        df["tabela"] = i
        df["titulo"] = titulo
        partes.append(df)

    df = pd.concat(partes, ignore_index=True)
    df["fonte"] = PAGINAS["mamografias-no-sus"]
    colunas = ["tabela", "ano", "localidade", "nivel", "regiao", "finalidade",
               "tipo_procedimento", "faixa_etaria", "valor", "titulo", "fonte"]
    return df[colunas]


def extrair_mortalidade() -> pd.DataFrame:
    """A página de mortalidade não tem tabela: os números estão no texto corrido."""
    texto = _conteudo("mortalidade").get_text(" ", strip=True)
    valores = {}

    # "... foi 11,71 óbitos/100.000 mulheres, em 2021."
    brasil = re.search(r"foi\s+(\d{1,2},\d{2})\s+óbitos/100\.000 mulheres,\s+em\s+(20\d\d)", texto)
    if not brasil:
        raise ValueError("Taxa nacional de mortalidade não encontrada — a redação da página pode ter mudado.")
    valores["Brasil"] = brasil.group(1)
    ano = int(brasil.group(2))

    # "Sudeste e Sul têm as maiores taxas (12,43 e 12,69 óbitos/100.000 ..."
    duplo = re.search(r"Sudeste e Sul[^(]*\((\d{1,2},\d{2}) e (\d{1,2},\d{2})", texto)
    if duplo:
        valores["Sudeste"], valores["Sul"] = duplo.groups()

    # "Nordeste (10,75 óbitos/100.000 mulheres)"
    for regiao, valor in re.findall(r"(Nordeste|Centro-Oeste|Norte)\s*\((\d{1,2},\d{2})\s*óbitos", texto):
        valores[regiao] = valor

    faltando = (REGIOES | {"Brasil"}) - set(valores)
    if faltando:
        log.warning("Mortalidade: regiões não encontradas no texto: %s", sorted(faltando))

    df = pd.DataFrame([
        {"localidade": loc, "nivel": classifica_localidade(loc)[1], "valor": limpa_numero(v)}
        for loc, v in valores.items()
    ])
    df["indicador"] = "taxa_mortalidade_ajustada_100mil"
    df["ano"] = ano
    df["fonte"] = PAGINAS["mortalidade"]
    return df


# ---------------------------------------------------------------
# 3. Validação: soma das UFs = região e soma das regiões = Brasil
# ---------------------------------------------------------------
def validar(df: pd.DataFrame, chaves: list[str], nome: str) -> int:
    """Compara totais declarados pela fonte com as somas das partes. Retorna nº de divergências."""
    divergencias = 0
    base = df.dropna(subset=["valor"])

    soma_uf = base[base["nivel"] == "uf"].groupby(chaves + ["regiao"])["valor"].sum()
    declarado_regiao = base[base["nivel"] == "regiao"].set_index(chaves + ["regiao"])["valor"]
    soma_regiao = base[base["nivel"] == "regiao"].groupby(chaves)["valor"].sum()
    declarado_brasil = base[base["nivel"] == "brasil"].set_index(chaves)["valor"]

    for rotulo, soma, declarado in [("UFs vs região", soma_uf, declarado_regiao),
                                    ("regiões vs Brasil", soma_regiao, declarado_brasil)]:
        comparacao = pd.concat({"soma": soma, "declarado": declarado}, axis=1).dropna()
        erradas = comparacao[(comparacao["soma"] - comparacao["declarado"]).abs() > 0.5]
        for chave, linha in erradas.iterrows():
            log.warning("[%s] %s %s: soma=%s, declarado=%s",
                        nome, rotulo, chave, f"{linha['soma']:,.0f}", f"{linha['declarado']:,.0f}")
        divergencias += len(erradas)
    return divergencias


def extrair() -> dict[str, pd.DataFrame]:
    config.INTERIM.mkdir(parents=True, exist_ok=True)
    resultados = {
        "inca_incidencia": extrair_incidencia(),
        "inca_mamografias_sus": extrair_mamografias_sus(),
        "inca_mortalidade": extrair_mortalidade(),
    }

    validar(resultados["inca_incidencia"].query("indicador == 'casos_estimados'"),
            ["ano"], "incidência")
    validar(resultados["inca_mamografias_sus"],
            ["tabela", "ano", "tipo_procedimento", "faixa_etaria"], "mamografias")

    for nome, df in resultados.items():
        destino = config.INTERIM / f"{nome}.csv"
        df.to_csv(destino, index=False)
        log.info("Salvo %s (%d linhas)", destino.relative_to(config.ROOT), len(df))
    return resultados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--forcar", action="store_true", help="baixa as páginas mesmo se já existirem")
    parser.add_argument("--offline", action="store_true", help="não acessa a internet; usa o HTML salvo")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not args.offline:
        coletar(forcar=args.forcar)
    extrair()


if __name__ == "__main__":
    main()
