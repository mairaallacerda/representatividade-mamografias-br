"""Exporta as tabelas do painel interativo (painel HTML) para ``dashboards/dados/``.

Modelo em estrela:

- ``dim_localidade``: uma linha por UF, com a região (chave: ``localidade``);
- ``fato_uf_ano``: mamografias (SIA) e óbitos (SIM) por UF e ano. As regiões e o Brasil vêm
  da soma das UFs, pela relação com ``dim_localidade``;
- ``fato_incidencia_uf``: casos novos estimados e taxas (INCA, 2023), por UF;
- tabelas de comparação Brasil × CBIS-DDSM e de desempenho do modelo, já agregadas.

Uso:
    python -m src.visualization.painel_dados
"""

import json
import logging

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src import config
from src.processing.cbis import carrega_cbis

log = logging.getLogger(__name__)

DESTINO = config.ROOT / "dashboards" / "dados"

SIGLAS = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM", "Bahia": "BA", "Ceará": "CE",
    "Distrito Federal": "DF", "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS", "Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
    "Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC", "São Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO",
}
NOMES_DENSIDADE = {1: "1 Adiposa", 2: "2 Predominantemente adiposa", 3: "3 Predominantemente densa", 4: "4 Densa"}


def _le(nome: str) -> pd.DataFrame:
    caminho = config.INTERIM / f"{nome}.csv"
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho} não encontrado — rode os scrapers antes (ver README).")
    return pd.read_csv(caminho)


def _pct(s: pd.Series) -> pd.Series:
    return 100 * s / s.sum()


def dim_localidade() -> pd.DataFrame:
    """Uma linha por UF; região e Brasil são agregações (hierarquia regiao > localidade)."""
    return pd.DataFrame([{"localidade": uf, "regiao": config.UF_PARA_REGIAO[uf], "sigla": SIGLAS[uf],
                          "pais": "Brasil"} for uf in sorted(config.UF_PARA_REGIAO)])


def fato_uf_ano() -> pd.DataFrame:
    partes = {
        "mamografias_rastreamento": _le("datasus_sia_mamografia_rastreamento_uf_ano"),
        "mamografias_diagnosticas": _le("datasus_sia_mamografia_diagnostica_uf_ano"),
        "obitos_cancer_mama": _le("datasus_sim_obitos_mama_uf_ano"),
    }
    df = None
    for nome, p in partes.items():
        p = p.query("nivel == 'uf'")[["localidade", "ano", "valor"]].rename(columns={"valor": nome})
        df = p if df is None else df.merge(p, on=["localidade", "ano"], how="outer")
    return df.sort_values(["ano", "localidade"])


def fato_incidencia_uf() -> pd.DataFrame:
    inc = _le("inca_incidencia").query("nivel == 'uf'")
    return (inc.pivot_table(index="localidade", columns="indicador", values="valor").reset_index()
            [["localidade", "casos_estimados", "taxa_bruta_100mil", "taxa_ajustada_100mil"]])


def taxas_regiao() -> pd.DataFrame:
    """Taxas ajustadas por idade (INCA) por região; não podem ser obtidas somando as UFs."""
    inc = _le("inca_incidencia").query("nivel == 'regiao' and indicador == 'taxa_ajustada_100mil'")
    mort = _le("inca_mortalidade").query("nivel == 'regiao'")
    return (inc.set_index("localidade")[["valor"]].rename(columns={"valor": "incidencia_ajustada_100mil"})
            .join(mort.set_index("localidade")[["valor"]].rename(columns={"valor": "mortalidade_ajustada_100mil"}))
            .rename_axis("regiao").reset_index())


def siscan_regiao() -> pd.DataFrame:
    df = pd.read_csv(config.PROCESSED / "siscan_regiao.csv")
    return df.rename(columns={"% mamas densas": "pct_densas", "% densas padronizada por idade": "pct_densas_padronizada",
                              "w CBIS-DDSM × região": "w_cbis", "AUC": "auc", "IC95% inf": "ic95_inf",
                              "IC95% sup": "ic95_sup"})[["regiao", "pct_densas", "pct_densas_padronizada", "w_cbis",
                                                         "auc", "ic95_inf", "ic95_sup"]]


def siscan_densidade_uf() -> pd.DataFrame:
    df = pd.read_csv(config.PROCESSED / "siscan_densidade_uf.csv")
    return df.rename(columns={"uf": "localidade", "% mamas densas": "pct_densas", "laudos SISCAN": "laudos"})[
        ["localidade", "pct_densas", "laudos"]]


def modelo_vpp_regiao() -> pd.DataFrame:
    df = pd.read_csv(config.PROCESSED / "vpp_regiao.csv")
    return df.rename(columns={"VPP": "vpp", "falsos positivos por câncer detectado": "fp_por_cancer",
                              "falsos positivos/ano": "fp_ano"})[["regiao", "prevalencia", "vpp", "fp_por_cancer",
                                                                  "fp_ano"]]


def obitos_faixa() -> pd.DataFrame:
    df = _le("datasus_sim_obitos_mama_faixa_ano").query("faixa_etaria != 'Idade ignorada'")
    ordem = {f: i for i, f in enumerate(dict.fromkeys(df["faixa_etaria"]))}
    df = df[["faixa_etaria", "ano", "valor"]].rename(columns={"valor": "obitos"})
    df["ordem_faixa"] = df["faixa_etaria"].map(ordem)
    return df


def densidade_faixa() -> pd.DataFrame:
    df = _le("siscan_densidade_faixa").dropna(subset=["densidade_birads_linha"])
    df = df[df["coluna"] != "Ignorado"]
    ordem = {f: i for i, f in enumerate(dict.fromkeys(df["coluna"]))}
    rotulo = (df["coluna"].str.replace("Entre ", "").str.replace(" anos", "").str.replace(" a ", "–")
              .str.replace("Acima de 79", "80+").str.replace("Até 9", "até 9"))
    return pd.DataFrame({
        "faixa_etaria": rotulo, "ordem_faixa": df["coluna"].map(ordem),
        "densidade": df["densidade_birads_linha"].astype(int),
        "densidade_nome": df["densidade_birads_linha"].astype(int).map(NOMES_DENSIDADE),
        "exames": df["exames"],
    })


def comparacao_densidade(cbis: pd.DataFrame) -> pd.DataFrame:
    br = (_le("siscan_densidade_ano").dropna(subset=["densidade_birads_linha"])
          .groupby("densidade_birads_linha")["exames"].sum())
    fontes = {
        "Brasil (SISCAN)": br,
        "CBIS-DDSM": cbis["breast_density"].value_counts(),
        "CBIS-DDSM: massas": cbis.query("abnormality_type == 'mass'")["breast_density"].value_counts(),
        "CBIS-DDSM: calcificações": cbis.query("abnormality_type == 'calcification'")["breast_density"].value_counts(),
    }
    linhas = []
    for fonte, s in fontes.items():
        s = s.reindex([1, 2, 3, 4]).fillna(0)
        for d, n, p in zip(s.index, s.values, _pct(s).values):
            linhas.append({"fonte": fonte, "densidade": int(d), "densidade_nome": NOMES_DENSIDADE[int(d)],
                           "quantidade": n, "percentual": p})
    return pd.DataFrame(linhas)


def comparacao_birads(cbis: pd.DataFrame) -> pd.DataFrame:
    bi = _le("siscan_birads_indicacao")
    bi = bi[bi["linha"].str.match(r"Categoria [0-5]$")].copy()
    bi["birads"] = bi["linha"].str.extract(r"(\d)").astype(int)
    fontes = {
        "Brasil: rastreamento": bi.query("coluna == 'Mamog. Rastreamento'").set_index("birads")["exames"],
        "Brasil: diagnóstica": bi.query("coluna == 'Mamog. Diagnostica'").set_index("birads")["exames"],
        "CBIS-DDSM": cbis["assessment"].value_counts(),
    }
    linhas = []
    for fonte, s in fontes.items():
        s = s.reindex(range(6)).fillna(0)
        for b, n, p in zip(s.index, s.values, _pct(s).values):
            linhas.append({"fonte": fonte, "birads": int(b), "quantidade": n, "percentual": p})
    return pd.DataFrame(linhas)


def birads_densidade_brasil() -> pd.DataFrame:
    bd = _le("siscan_birads_densidade").dropna(subset=["densidade_birads_coluna"])
    bd = bd[bd["linha"].str.match(r"Categoria [0-5]$")]
    tab = bd.pivot_table(index="densidade_birads_coluna", columns="linha", values="exames", aggfunc="sum")
    return pd.DataFrame({
        "densidade": tab.index.astype(int),
        "densidade_nome": tab.index.astype(int).map(NOMES_DENSIDADE),
        "exames": tab.sum(axis=1).values,
        "pct_birads_0": (100 * tab["Categoria 0"] / tab.sum(axis=1)).values,
        "pct_birads_4_5": (100 * (tab["Categoria 4"] + tab["Categoria 5"]) / tab.sum(axis=1)).values,
    })


def modelo_auc_densidade() -> pd.DataFrame:
    pred = pd.read_csv(config.PROCESSED / "cbis_predicoes_teste_calcificacoes.csv").dropna(subset=["breast_density"])
    linhas = [{"densidade": int(d), "densidade_nome": NOMES_DENSIDADE[int(d)], "lesoes_teste": len(g),
               "auc": roc_auc_score(g["maligno"], g["prob"])} for d, g in pred.groupby("breast_density")]
    return pd.DataFrame(linhas)


def modelo_auc_populacao() -> pd.DataFrame:
    df = pd.read_csv(config.PROCESSED / "auc_reponderada.csv")
    return df.rename(columns={"população": "populacao", "AUC": "auc", "IC95% inf": "ic95_inf",
                              "IC95% sup": "ic95_sup", "% densas (3+4)": "pct_densas",
                              "AUC sem densidade 1": "auc_sem_densidade_1"})


def cbis_lesoes(cbis: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "patient_id": cbis["patient_id"],
        "tipo_lesao": cbis["abnormality_type"].map({"mass": "Massa", "calcification": "Calcificação"}),
        "densidade": cbis["breast_density"],
        "birads": cbis["assessment"],
        "patologia": cbis["pathology"].map({"MALIGNANT": "Maligna", "BENIGN": "Benigna",
                                             "BENIGN_WITHOUT_CALLBACK": "Benigna sem retorno"}),
        "maligna": cbis["maligno"].astype(int),
        "conjunto": cbis["origem_split"].map({"train": "Treino", "test": "Teste"}),
    })


def indicadores(t: dict[str, pd.DataFrame]) -> dict:
    """Números de destaque (cartões), usados pelo painel HTML."""
    f22 = t["fato_uf_ano"].query("ano == 2022")
    serie = t["fato_uf_ano"].groupby("ano")[["mamografias_rastreamento", "mamografias_diagnosticas"]].sum().sum(axis=1)
    casos = t["fato_incidencia_uf"]["casos_estimados"].sum()
    mamo22 = f22[["mamografias_rastreamento", "mamografias_diagnosticas"]].sum().sum()
    cbis_mal = 100 * t["cbis_lesoes"]["maligna"].mean()
    dens = t["comparacao_densidade"].pivot(index="densidade", columns="fonte", values="percentual")
    p, q = dens["CBIS-DDSM"] / 100, dens["Brasil (SISCAN)"] / 100
    df_fx = t["densidade_faixa"]
    dens_fx = df_fx.assign(densa=df_fx["densidade"] >= 3).groupby("faixa_etaria").apply(
        lambda g: 100 * g.loc[g["densa"], "exames"].sum() / g["exames"].sum(), include_groups=False)
    bi = t["comparacao_birads"].query("birads >= 4").groupby("fonte")["percentual"].sum()
    return {
        "mamografias_2022": float(mamo22),
        "queda_2020_pct": float(100 * (serie[2020] / serie[2019] - 1)),
        "obitos_2022": float(f22["obitos_cancer_mama"].sum()),
        "casos_estimados_ano": float(casos),
        "cbis_pct_malignas": float(cbis_mal),
        "brasil_casos_por_100_mamografias": float(100 * casos / mamo22),
        "razao_case_mix": float(cbis_mal / (100 * casos / mamo22)),
        "w_cohen_densidade": float(np.sqrt((((p - q) ** 2) / q).sum())),
        "pct_densas_40_44": float(dens_fx["40–44"]),
        "pct_densas_65_69": float(dens_fx["65–69"]),
        "pct_suspeitos_rastreamento": float(bi["Brasil: rastreamento"]),
        "pct_suspeitos_cbis": float(bi["CBIS-DDSM"]),
        "cbis_lesoes": int(len(t["cbis_lesoes"])),
        "cbis_pacientes": int(t["cbis_lesoes"]["patient_id"].nunique()),
    }


def exportar() -> dict[str, pd.DataFrame]:
    cbis = carrega_cbis()
    cbis["breast_density"] = cbis["breast_density"].replace(0, np.nan)
    tabelas = {
        "dim_localidade": dim_localidade(),
        "fato_uf_ano": fato_uf_ano(),
        "fato_incidencia_uf": fato_incidencia_uf(),
        "taxas_regiao": taxas_regiao(),
        "obitos_faixa": obitos_faixa(),
        "densidade_faixa": densidade_faixa(),
        "comparacao_densidade": comparacao_densidade(cbis),
        "comparacao_birads": comparacao_birads(cbis),
        "birads_densidade_brasil": birads_densidade_brasil(),
        "modelo_auc_densidade": modelo_auc_densidade(),
        "modelo_auc_populacao": modelo_auc_populacao(),
        "modelo_vpp_regiao": modelo_vpp_regiao(),
        "siscan_regiao": siscan_regiao(),
        "siscan_densidade_uf": siscan_densidade_uf(),
        "cbis_lesoes": cbis_lesoes(cbis),
    }
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nome, df in tabelas.items():
        # UTF-8 com BOM: o Excel reconhece os acentos automaticamente
        df.to_csv(DESTINO / f"{nome}.csv", index=False, encoding="utf-8-sig")
        log.info("dashboards/dados/%s.csv (%d linhas)", nome, len(df))
    (DESTINO / "indicadores.json").write_text(json.dumps(indicadores(tabelas), indent=2, ensure_ascii=False))
    return tabelas


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    exportar()
