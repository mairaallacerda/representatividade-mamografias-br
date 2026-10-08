"""Leitura e padronização dos metadados do CBIS-DDSM."""

from pathlib import Path

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


def carrega_imagens() -> pd.DataFrame:
    """dicom_info.csv (1 linha por imagem JPEG) com o caminho local de cada arquivo.

    ``tipo_imagem``: 'full mammogram images', 'cropped images' ou 'ROI mask images'.
    ``case_id`` (ex.: 'Calc-Training_P_00005_RIGHT_CC') liga a imagem às lesões de ``carrega_cbis``.
    """
    info = pd.read_csv(config.RAW_CBIS / "dicom_info.csv")
    df = pd.DataFrame({
        "case_id": info["PatientID"],
        "tipo_imagem": info["SeriesDescription"],
        "caminho": info["image_path"].str.replace("CBIS-DDSM/jpeg", str(config.CBIS_JPEG), regex=False),
        "linhas": info["Rows"],
        "colunas": info["Columns"],
    })
    df["existe"] = df["caminho"].map(lambda c: Path(c).exists())
    return df


TIPOS = {"full mammogram images": "full", "cropped images": "recorte", "ROI mask images": "mascara"}


def liga_imagens(lesoes: pd.DataFrame, imagens: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta às lesões as colunas caminho_full, caminho_recorte e caminho_mascara.

    A mamografia completa é identificada pelo caso da imagem (``Calc-Training_P_00005_RIGHT_CC``)
    e o recorte/máscara pelo caso da lesão (``..._RIGHT_CC_1``), ambos tirados dos caminhos
    originais do CSV de lesões.
    """
    df = lesoes.copy()
    df["case_full"] = df["image_file_path"].str.split("/").str[0]
    df["case_roi"] = df["cropped_image_file_path"].str.split("/").str[0]
    for tipo, nome in TIPOS.items():
        mapa = imagens[imagens["tipo_imagem"] == tipo].drop_duplicates("case_id").set_index("case_id")["caminho"]
        chave = "case_full" if nome == "full" else "case_roi"
        df[f"caminho_{nome}"] = df[chave].map(mapa)
    return df


if __name__ == "__main__":
    df = carrega_cbis()
    print(df.shape)
    print(df.head())
