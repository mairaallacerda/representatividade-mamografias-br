"""Processamento digital de imagens: realce e segmentação de microcalcificações.

As microcalcificações aparecem como pontos pequenos e muito brilhantes sobre o tecido.
O pipeline aplicado ao recorte (crop) de cada lesão é:

1. **Máscara de tecido**: descarta o fundo preto e erode a borda da mama (a transição
   pele/fundo gera falsos pontos no top-hat);
2. **CLAHE** + suavização leve: padroniza o contraste entre scanners diferentes e reduz o
   ruído de compressão JPEG;
3. **Top-hat branco** com elemento estruturante em disco: realça estruturas claras menores
   que o disco (os pontos) e remove o fundo de variação lenta (o tecido);
4. **Limiarização robusta** do top-hat dentro do tecido: mediana + K·MAD, com um piso
   absoluto (sem o piso, um recorte sem calcificações ainda "acharia" pontos no ruído);
   depois, remoção de componentes pequenos (ruído) ou grandes demais;
5. **Características** dos pontos encontrados e do recorte.
"""

from pathlib import Path

import cv2
import numpy as np
from skimage import measure

RAIO_TOPHAT = 7      # px; microcalcificações no DDSM têm ~2–15 px de diâmetro
K_MAD = 8.0          # limiar = mediana + K * MAD do top-hat no tecido
LIMIAR_MIN = 25.0    # piso absoluto do limiar (níveis de cinza, após CLAHE)
FUNDO = 20           # pixels abaixo disso são fundo (fora da mama)
EROSAO_BORDA = 15    # px removidos da borda do tecido
AREA_MIN = 4         # px; abaixo disso é ruído
AREA_MAX = 400       # px; acima disso não é microcalcificação


def le_cinza(caminho: str | Path, reducao: int = 1) -> np.ndarray:
    """Lê a imagem em tons de cinza. ``reducao`` 2/4/8 decodifica o JPEG já reduzido (bem mais rápido)."""
    flags = {1: cv2.IMREAD_GRAYSCALE, 2: cv2.IMREAD_REDUCED_GRAYSCALE_2,
             4: cv2.IMREAD_REDUCED_GRAYSCALE_4, 8: cv2.IMREAD_REDUCED_GRAYSCALE_8}[reducao]
    img = cv2.imread(str(caminho), flags)
    if img is None:
        raise FileNotFoundError(caminho)
    return img


def fracao_binaria(img: np.ndarray, margem: int = 15) -> float:
    """Fração de pixels quase pretos ou quase brancos. Máscaras ≈ 1; mamografias bem menos."""
    return float(((img <= margem) | (img >= 255 - margem)).mean())


def realce(img: np.ndarray) -> np.ndarray:
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)


def mascara_tecido(img: np.ndarray) -> np.ndarray:
    tecido = (img > FUNDO).astype(np.uint8)
    disco = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * EROSAO_BORDA + 1, 2 * EROSAO_BORDA + 1))
    return cv2.erode(tecido, disco, borderType=cv2.BORDER_REPLICATE).astype(bool)


def segmenta_calcificacoes(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Retorna (top-hat, máscara binária dos pontos candidatos a microcalcificação)."""
    tecido = mascara_tecido(img)
    realcada = cv2.GaussianBlur(realce(img), (3, 3), 0)
    disco = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * RAIO_TOPHAT + 1, 2 * RAIO_TOPHAT + 1))
    tophat = cv2.morphologyEx(realcada, cv2.MORPH_TOPHAT, disco).astype(np.float32)
    tophat[~tecido] = 0
    if tecido.sum() < 100:
        return tophat, np.zeros_like(tecido)

    valores = tophat[tecido]
    mediana = np.median(valores)
    mad = np.median(np.abs(valores - mediana))
    limiar = max(mediana + K_MAD * mad, LIMIAR_MIN)

    rotulos = measure.label(tophat > limiar)
    pontos = np.zeros_like(tecido)
    for regiao in measure.regionprops(rotulos):
        if AREA_MIN <= regiao.area <= AREA_MAX:
            pontos[rotulos == regiao.label] = True
    return tophat, pontos


def extrai_caracteristicas(img: np.ndarray) -> dict:
    """Características de um recorte de lesão (valores por recorte)."""
    tophat, pontos = segmenta_calcificacoes(img)
    regioes = measure.regionprops(measure.label(pontos), intensity_image=img)
    areas = np.array([r.area for r in regioes]) if regioes else np.array([0.0])
    excentr = np.array([r.eccentricity for r in regioes]) if regioes else None
    centros = np.array([r.centroid for r in regioes]) if len(regioes) > 1 else None

    # dispersão espacial: distância média de cada ponto ao vizinho mais próximo
    if centros is not None:
        d = np.sqrt(((centros[:, None, :] - centros[None, :, :]) ** 2).sum(-1))
        np.fill_diagonal(d, np.inf)
        dist_vizinho = float(d.min(axis=1).mean())
    else:
        dist_vizinho = np.nan

    tecido = mascara_tecido(img)
    area_tecido = max(int(tecido.sum()), 1)
    return {
        "altura": img.shape[0],
        "largura": img.shape[1],
        "fracao_tecido": area_tecido / img.size,
        "intensidade_media": float(img[tecido].mean()) if tecido.any() else np.nan,
        "contraste": float(img[tecido].std()) if tecido.any() else np.nan,
        "n_pontos": len(regioes),
        "densidade_pontos_por_10k_px": 1e4 * len(regioes) / area_tecido,
        "area_media_ponto": float(areas.mean()),
        "area_cv_ponto": float(areas.std() / areas.mean()) if areas.mean() > 0 else np.nan,  # heterogeneidade
        "excentricidade_media": float(excentr.mean()) if excentr is not None else np.nan,
        "dist_vizinho_media": dist_vizinho,
        "tophat_p99": float(np.percentile(tophat[tecido], 99)) if tecido.any() else np.nan,
    }
