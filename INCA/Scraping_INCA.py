import re
import io
import requests
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0 (compatível com navegador comum)"}


# ---------------------------------------------------------------
# 1. INCIDÊNCIA — página com 1 tabela HTML
# ---------------------------------------------------------------
def scrape_incidencia():
    url = "https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/dados-e-numeros/incidencia"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    tabelas = pd.read_html(io.StringIO(resp.text), encoding="utf-8", thousands=".", decimal=",")
    df = tabelas[0]
    df.columns = ["regiao_uf", "n_casos", "taxa_bruta", "taxa_ajustada"]
    df["indicador"] = "incidencia"
    df["ano"] = 2023
    df["fonte"] = url
    return df


# ---------------------------------------------------------------
# 2. MAMOGRAFIAS NO SUS — página com VÁRIAS tabelas.
#    Selecionamos automaticamente a tabela certa verificando se a
#    primeira coluna contém as 5 regiões do Brasil + "Brasil"/"Total".
# ---------------------------------------------------------------
def _identificar_tabela_regional(tabelas):
    regioes_esperadas = {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}
    candidatas = []
    for t in tabelas:
        primeira_coluna = set(t.iloc[:, 0].astype(str).str.strip())
        # aceita tanto "Norte" quanto "Região Norte" como variações
        primeira_coluna_normalizada = {c.replace("Região ", "") for c in primeira_coluna}
        if regioes_esperadas.issubset(primeira_coluna_normalizada):
            candidatas.append(t)
    return candidatas


def scrape_mamografias_sus():
    url = "https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/dados-e-numeros/mamografias-no-sus"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    tabelas = pd.read_html(io.StringIO(resp.text), encoding="utf-8", thousands=".", decimal=",")
    candidatas = _identificar_tabela_regional(tabelas)

    print(f"[mamografias_sus] {len(tabelas)} tabelas encontradas na página, "
          f"{len(candidatas)} identificadas como tabelas regionais de interesse.")

    # A Tabela 1 (procedimento x região, 2022) é a primeira candidata regional
    # simples o suficiente para consolidar diretamente. As tabelas 2-5 têm
    # estrutura mais rica (por ano ou por faixa etária) — trate cada uma
    # separadamente conforme a necessidade da sua análise.
    if not candidatas:
        raise ValueError("Nenhuma tabela regional identificada — confira se o "
                          "layout da página mudou.")

    tabela1 = candidatas[0].copy()
    tabela1.columns = ["regiao", "mamografia_diagnostica", "mamografia_rastreamento", "total"]
    tabela1 = tabela1[tabela1["regiao"] != "Brasil"]  # remove a linha de total
    tabela1["indicador"] = "mamografias_realizadas"
    tabela1["ano"] = 2022
    tabela1["fonte"] = url
    return tabela1


# ---------------------------------------------------------------
# 3. MORTALIDADE — SEM tabela HTML, números embutidos em texto corrido.
#    Extraído via regex a partir do texto da página.
# ---------------------------------------------------------------
def scrape_mortalidade():
    url = "https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/dados-e-numeros/mortalidade"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.encoding = "utf-8"
    texto = resp.text

    resultado = {}

    # Padrão 1: "Sudeste e Sul têm as maiores taxas (12,43 e 12,69 ...)"
    m_duplo = re.search(r"Sudeste e Sul.*?\((\d{1,2},\d{2}) e (\d{1,2},\d{2})", texto)
    if m_duplo:
        resultado["Sudeste"] = float(m_duplo.group(1).replace(",", "."))
        resultado["Sul"] = float(m_duplo.group(2).replace(",", "."))

    # Padrão 2: "Nordeste (10,75 óbitos...)", "Centro-Oeste (10,90 óbitos...)" etc.
    for regiao, valor in re.findall(
        r"(Nordeste|Centro-Oeste|Norte)\s*\((\d{1,2},\d{2})\s*óbitos", texto
    ):
        resultado[regiao] = float(valor.replace(",", "."))

    if not resultado:
        raise ValueError("Nenhum valor de mortalidade encontrado — confira se o "
                          "texto da página mudou de redação.")

    df = pd.DataFrame(list(resultado.items()), columns=["regiao_uf", "valor"])
    df["indicador"] = "taxa_mortalidade_ajustada"
    df["ano"] = 2021
    df["fonte"] = url
    return df


# ---------------------------------------------------------------
# 4. Consolidar tudo em uma única base epidemiológica
# ---------------------------------------------------------------
if __name__ == "__main__":
    df_incidencia = scrape_incidencia()
    df_mamografias = scrape_mamografias_sus()
    df_mortalidade = scrape_mortalidade()

    print("\nIncidência:", df_incidencia.shape)
    print(df_incidencia.head())
    print("\nMamografias no SUS:", df_mamografias.shape)
    print(df_mamografias.head())
    print("\nMortalidade:", df_mortalidade.shape)
    print(df_mortalidade)


    df_incidencia.to_csv("INCA/csv_gerado/inca_incidencia.csv", index=False)
    df_mamografias.to_csv("INCA/csv_gerado/inca_mamografias_sus.csv", index=False)
    df_mortalidade.to_csv("INCA/csv_gerado/inca_mortalidade.csv", index=False)
    print("\nArquivos salvos: inca_incidencia.csv, inca_mamografias_sus.csv, inca_mortalidade.csv")