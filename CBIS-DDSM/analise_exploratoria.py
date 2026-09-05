import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")
df = pd.read_csv("CBIS-DDSM/cbis_ddsm_metadados_unificados.csv")

# Trata breast_density == 0 como ausente (fora da escala BI-RADS 1-4)
df["breast_density"] = df["breast_density"].replace(0, np.nan)
df_density = df.dropna(subset=["breast_density"]).copy()
df_density["breast_density"] = df_density["breast_density"].astype(int)

fig, axes = plt.subplots(2, 3, figsize=(18, 11))
fig.suptitle("Análise Exploratória — CBIS-DDSM (massas e calcificações)", fontsize=16, y=1.02)

# 1. Distribuição por tipo de anormalidade
sns.countplot(data=df, x="abnormality_source", hue="abnormality_source",
              palette="Set2", ax=axes[0, 0], legend=False)
axes[0, 0].set_title("Registros por tipo de anormalidade")
axes[0, 0].set_xlabel("")
axes[0, 0].set_ylabel("Nº de registros")

# 2. Pathology (benigno x maligno) por tipo de anormalidade
sns.countplot(data=df, x="abnormality_source", hue="pathology_binaria",
              palette="Set1", ax=axes[0, 1])
axes[0, 1].set_title("Benigno x Maligno, por tipo de anormalidade")
axes[0, 1].set_xlabel("")
axes[0, 1].set_ylabel("Nº de registros")
axes[0, 1].legend(title="Patologia")

# 3. Distribuição de breast_density (escala BI-RADS 1-4)
sns.countplot(data=df_density, x="breast_density", hue="breast_density",
              palette="Blues", ax=axes[0, 2], legend=False)
axes[0, 2].set_title("Densidade mamária (escala BI-RADS)")
axes[0, 2].set_xlabel("Categoria de densidade (1=menos densa, 4=mais densa)")
axes[0, 2].set_ylabel("Nº de registros")

# 4. Proporção de malignidade por categoria de densidade mamária
prop_malign = (
    df_density
      .groupby("breast_density")["pathology_binaria"]
      .apply(lambda s: (s == "MALIGNANT").mean() * 100)
)
sns.barplot(x=prop_malign.index, y=prop_malign.values, hue=prop_malign.index,
            palette="Reds", ax=axes[1, 0], legend=False)
axes[1, 0].set_title("% de casos malignos por densidade mamária")
axes[1, 0].set_xlabel("Categoria de densidade (BI-RADS)")
axes[1, 0].set_ylabel("% maligno")

# 5. Assessment (BI-RADS 0-5) por patologia
sns.boxplot(data=df, x="pathology_binaria", y="assessment",
            hue="pathology_binaria", palette="Set1", ax=axes[1, 1], legend=False)
axes[1, 1].set_title("Escore BI-RADS (assessment) por patologia")
axes[1, 1].set_xlabel("")
axes[1, 1].set_ylabel("Assessment (0-5)")

# 6. Subtlety (sutileza da anormalidade) por patologia
sns.violinplot(data=df, x="pathology_binaria", y="subtlety",
               hue="pathology_binaria", palette="Set2", ax=axes[1, 2], legend=False)
axes[1, 2].set_title("Sutileza da anormalidade por patologia")
axes[1, 2].set_xlabel("")
axes[1, 2].set_ylabel("Subtlety (1=sutil, 5=óbvia)")

plt.tight_layout()
plt.savefig("CBIS-DDSM/Imagens/cbis_ddsm_analise_exploratoria.png", dpi=150, bbox_inches="tight")
print("Painel salvo em CBIS-DDSM/Imagens/cbis_ddsm_analise_exploratoria.png")

# Estatística de apoio para o texto do relatório
print("\n% de casos malignos por categoria de densidade mamária:")
print(prop_malign.round(1))