"""
Validação visual: mamografia completa x recorte x máscara ROI
------------------------------------------------------------------
Plota, lado a lado, as três imagens de uma amostra de casos:
  1) mamografia completa (full mammogram)
  2) recorte da anormalidade (cropped)
  3) máscara ROI (ROI mask)

Objetivo: confirmar visualmente que 'cropped' e 'ROI mask' não estão
trocados no CSV original (bug documentado do CBIS-DDSM em algumas
distribuições). Uma máscara ROI correta deve ser predominantemente
preta com uma região branca/binária destacando a anormalidade — bem
diferente de um recorte em tons de cinza da mamografia.

Rode depois de mapear_paths_imagens.py, usando
cbis_ddsm_metadados_com_paths_jpg.csv como entrada.
"""

import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

N_AMOSTRAS = 4  # quantos casos mostrar (aumente/diminua à vontade)

df = pd.read_csv("CBIS-DDSM/csv_geraddo/cbis_ddsm_metadados_com_paths_jpg.csv")

# Mantém só os casos com os 3 caminhos mapeados
completos = df.dropna(subset=["path_full_jpg", "path_cropped_jpg", "path_mask_jpg"])
print(f"Casos com os 3 caminhos mapeados: {len(completos)}")

amostra = completos.sample(min(N_AMOSTRAS, len(completos)), random_state=42)

fig, axes = plt.subplots(len(amostra), 3, figsize=(9, 3 * len(amostra)))
if len(amostra) == 1:
    axes = axes.reshape(1, 3)

colunas = ["path_full_jpg", "path_cropped_jpg", "path_mask_jpg"]
titulos = ["Mamografia completa", "Recorte (cropped)", "Máscara ROI"]

for i, (_, linha) in enumerate(amostra.iterrows()):
    for j, (col, titulo) in enumerate(zip(colunas, titulos)):
        try:
            img = Image.open(linha[col])
            axes[i, j].imshow(img, cmap="gray")
        except (FileNotFoundError, OSError):
            axes[i, j].text(0.5, 0.5, "arquivo não encontrado", ha="center", va="center")
        axes[i, j].set_title(f"{titulo}\n{linha['patient_id']} ({linha['pathology']})", fontsize=9)
        axes[i, j].axis("off")

plt.tight_layout()
plt.savefig("CBIS-DDSM/Imagens/validacao_visual_full_cropped_mask.png", dpi=150, bbox_inches="tight")
print("Painel salvo em CBIS-DDSM/Imagens/validacao_visual_full_cropped_mask.png")

print(
    "\nO que checar visualmente:\n"
    "- A máscara ROI deve ser majoritariamente preta com uma região\n"
    "  branca/binária bem definida (o contorno da anormalidade).\n"
    "- O recorte (cropped) deve parecer um pedaço em tons de cinza da\n"
    "  mamografia, do mesmo jeito que a imagem completa, só que menor.\n"
    "- Se a coluna 'Recorte' parecer binária (preto/branco) e a coluna\n"
    "  'Máscara' parecer uma foto em tons de cinza, as colunas do CSV\n"
    "  original estão trocadas para esse caso — considere usar os\n"
    "  arquivos de metadados corrigidos do IEEE DataPort."
)