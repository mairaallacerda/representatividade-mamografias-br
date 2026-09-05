import pandas as pd

CAMINHO_DICOM_INFO = "CBIS-DDSM/csv/dicom_info.csv"   
PASTA_JPEG_LOCAL = "/home/mairaallacerda/Visão Computacional e Processamento Digital de Imagens em Mamografias/CBIS-DDSM/jpeg"

# ---------------------------------------------------------------
# 1. Carregar o dataset unificado (do script anterior) e o dicom_info
# ---------------------------------------------------------------
df = pd.read_csv("CBIS-DDSM/cbis_ddsm_metadados_unificados.csv")
dicom_info = pd.read_csv(CAMINHO_DICOM_INFO)

# ---------------------------------------------------------------
# 2. Extrair o "case_id" (identificador de pasta) das colunas de
#    caminho original — é o trecho antes da primeira barra.
#    Ex: "Calc-Training_P_00005_RIGHT_CC/1.3.6.../000000.dcm"
#         -> "Calc-Training_P_00005_RIGHT_CC"
# ---------------------------------------------------------------
def extrair_case_id(caminho):
    if pd.isna(caminho):
        return None
    return str(caminho).strip().split("/")[0]

df["case_id_full"] = df["image file path"].apply(extrair_case_id)
df["case_id_derivado"] = df["cropped image file path"].apply(extrair_case_id)

# ---------------------------------------------------------------
# 3. Para cada SeriesDescription, criar um dicionário case_id -> path local
# ---------------------------------------------------------------
def mapa_por_tipo(series_desc):
    subset = dicom_info[dicom_info["SeriesDescription"] == series_desc]
    caminhos = subset["image_path"].str.replace("CBIS-DDSM/jpeg", PASTA_JPEG_LOCAL, regex=False)
    return dict(zip(subset["PatientID"], caminhos))

mapa_full = mapa_por_tipo("full mammogram images")
mapa_cropped = mapa_por_tipo("cropped images")
mapa_mask = mapa_por_tipo("ROI mask images")

df["path_full_jpg"] = df["case_id_full"].map(mapa_full)
df["path_cropped_jpg"] = df["case_id_derivado"].map(mapa_cropped)
df["path_mask_jpg"] = df["case_id_derivado"].map(mapa_mask)

# ---------------------------------------------------------------
# 4. Diagnóstico: quantos registros ficaram sem caminho mapeado?
#    (isso é normal acontecer para uma fração pequena — mas se for
#    muito alta, o dicom_info.csv real pode ter nomes de coluna
#    ligeiramente diferentes: confira com dicom_info.columns antes)
# ---------------------------------------------------------------
print("Total de registros:", len(df))
print("Sem path_full_jpg:", df["path_full_jpg"].isna().sum())
print("Sem path_cropped_jpg:", df["path_cropped_jpg"].isna().sum())
print("Sem path_mask_jpg:", df["path_mask_jpg"].isna().sum())

print("\nExemplo de registros mapeados:")
print(df[["patient_id", "case_id_full", "path_full_jpg", "path_cropped_jpg", "path_mask_jpg"]].head())

df.to_csv("CBIS-DDSM/csv_geraddo/cbis_ddsm_metadados_com_paths_jpg.csv", index=False)
print("\nSalvo em CBIS-DDSM/csv_geraddo/cbis_ddsm_metadados_com_paths_jpg.csv")