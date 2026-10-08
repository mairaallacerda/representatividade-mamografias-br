"""Leitura e padronização dos metadados do CBIS-DDSM."""

import pandas as pd

from src import config


def _normaliza_colunas(df: pd.DataFrame) -> pd.DataFrame:
    # Os CSVs de massa e calcificação usam grafias diferentes (ex.: "breast_density" x "breast density")
    df = df.copy()
    df.columns = (
        df.columns.str.strip().str.lower().str.replace(r"[\s\-]+", "_", regex=True)
    )
    return df


def carrega_cbis() -> pd.DataFrame:
    """Concatena os 4 CSVs do CBIS-DDSM em um único dataframe."""
    partes = []
    for chave, nome in config.CBIS_FILES.items():
        caminho = config.RAW_CBIS / nome
        if not caminho.exists():
            raise FileNotFoundError(
                f"{caminho} não encontrado. Baixe os metadados do CBIS-DDSM em data/raw/cbis-ddsm/."
            )
        df = _normaliza_colunas(pd.read_csv(caminho))
        tipo, split = chave.split("_")
        df["origem_tipo"] = tipo
        df["origem_split"] = split
        partes.append(df)

    df = pd.concat(partes, ignore_index=True)
    # Agrupa BENIGN_WITHOUT_CALLBACK com BENIGN para a análise de malignidade
    df["maligno"] = df["pathology"].str.upper().eq("MALIGNANT")
    return df


if __name__ == "__main__":
    df = carrega_cbis()
    print(df.shape)
    print(df.head())
