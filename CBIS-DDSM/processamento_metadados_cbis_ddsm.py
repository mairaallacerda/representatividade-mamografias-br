"""
Processamento dos metadados do CBIS-DDSM (massas e calcificações)
-------------------------------------------------------------------
Une os 4 CSVs originais (mass/calc x train/test) em um único DataFrame
padronizado, pronto para análise exploratória e para o cruzamento
posterior com dados epidemiológicos do INCA/DATASUS.
"""

import pandas as pd

# ---------------------------------------------------------------
# 1. Carregar os 4 arquivos originais
# ---------------------------------------------------------------
mass_train = pd.read_csv("CBIS-DDSM/csv/mass_case_description_train_set.csv")
mass_test = pd.read_csv("CBIS-DDSM/csv/mass_case_description_test_set.csv")
calc_train = pd.read_csv("CBIS-DDSM/csv/calc_case_description_train_set.csv")
calc_test = pd.read_csv("CBIS-DDSM/csv/calc_case_description_test_set.csv")

mass_train["abnormality_source"] = "mass"
mass_test["abnormality_source"] = "mass"
calc_train["abnormality_source"] = "calcification"
calc_test["abnormality_source"] = "calcification"

mass_train["split"] = "train"
mass_test["split"] = "test"
calc_train["split"] = "train"
calc_test["split"] = "test"

# ---------------------------------------------------------------
# 2. Padronizar nomes de colunas
#    (o arquivo de calcificação usa "breast density" com espaço;
#    o de massa usa "breast_density" com underline)
# ---------------------------------------------------------------
rename_map = {
    "breast density": "breast_density",
    "left or right breast": "side",
    "image view": "view",
    "abnormality id": "abnormality_id",
    "abnormality type": "abnormality_type",
}
for df in (mass_train, mass_test, calc_train, calc_test):
    df.rename(columns=rename_map, inplace=True)

# ---------------------------------------------------------------
# 3. Colunas específicas de cada tipo de anormalidade
#    (mass shape/margins vs calc type/distribution) viram uma única
#    coluna genérica "descriptor_1" / "descriptor_2", guardando
#    também o nome original em "descriptor_1_name" / "descriptor_2_name"
#    para não perder a informação semântica.
# ---------------------------------------------------------------
mass_train["descriptor_1_name"], mass_test["descriptor_1_name"] = "mass_shape", "mass_shape"
mass_train["descriptor_2_name"], mass_test["descriptor_2_name"] = "mass_margins", "mass_margins"
calc_train["descriptor_1_name"], calc_test["descriptor_1_name"] = "calc_type", "calc_type"
calc_train["descriptor_2_name"], calc_test["descriptor_2_name"] = "calc_distribution", "calc_distribution"

mass_train.rename(columns={"mass shape": "descriptor_1", "mass margins": "descriptor_2"}, inplace=True)
mass_test.rename(columns={"mass shape": "descriptor_1", "mass margins": "descriptor_2"}, inplace=True)
calc_train.rename(columns={"calc type": "descriptor_1", "calc distribution": "descriptor_2"}, inplace=True)
calc_test.rename(columns={"calc type": "descriptor_1", "calc distribution": "descriptor_2"}, inplace=True)

# ---------------------------------------------------------------
# 4. Unir tudo em um único DataFrame
# ---------------------------------------------------------------
colunas_finais = [
    "patient_id", "abnormality_source", "split", "side", "view",
    "abnormality_id", "abnormality_type", "breast_density",
    "descriptor_1_name", "descriptor_1", "descriptor_2_name", "descriptor_2",
    "assessment", "pathology", "subtlety",
    "image file path", "cropped image file path", "ROI mask file path",
]

df = pd.concat(
    [mass_train[colunas_finais], mass_test[colunas_finais],
     calc_train[colunas_finais], calc_test[colunas_finais]],
    ignore_index=True,
)

# Padroniza a coluna pathology em uma versão binária também
# (útil para classificação: benigno x maligno)
df["pathology_binaria"] = df["pathology"].map({
    "MALIGNANT": "MALIGNANT",
    "BENIGN": "BENIGN",
    "BENIGN_WITHOUT_CALLBACK": "BENIGN",
})

print(f"Total de registros (imagem/anormalidade): {len(df)}")
print(f"Total de pacientes únicos: {df['patient_id'].nunique()}")
print()
print("Distribuição por tipo de anormalidade:")
print(df["abnormality_source"].value_counts())
print()
print("Distribuição de pathology (binária):")
print(df["pathology_binaria"].value_counts())
print()
print("Distribuição de breast_density (1-4, escala BI-RADS):")
print(df["breast_density"].value_counts().sort_index())
print()
print("Cruzamento rápido: pathology x abnormality_source")
print(pd.crosstab(df["abnormality_source"], df["pathology_binaria"]))

# ---------------------------------------------------------------
# 5. Salvar o dataset unificado e padronizado
# ---------------------------------------------------------------
df.to_csv("CBIS-DDSM/csv_geraddo/cbis_ddsm_metadados_unificados.csv", index=False)
print("\nSalvo em: CBIS-DDSM/csv_geraddo/cbis_ddsm_metadados_unificados.csv")