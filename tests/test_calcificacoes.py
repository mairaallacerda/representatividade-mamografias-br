import numpy as np
import pytest

from src.images.calcificacoes import extrai_caracteristicas, fracao_binaria, segmenta_calcificacoes


def tecido_com_ruido(seed=0, tamanho=200):
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(110, 4, (tamanho, tamanho)), 0, 255).astype(np.uint8)


def pinta_pontos(img, centros, raio=2, valor=230):
    yy, xx = np.mgrid[: img.shape[0], : img.shape[1]]
    for cy, cx in centros:
        img[(yy - cy) ** 2 + (xx - cx) ** 2 <= raio**2] = valor
    return img


def test_detecta_pontos_brilhantes():
    centros = [(50, 50), (60, 120), (140, 80), (150, 150)]
    img = pinta_pontos(tecido_com_ruido(), centros)
    assert extrai_caracteristicas(img)["n_pontos"] == len(centros)


def test_tecido_sem_calcificacao_nao_tem_pontos():
    # sem o piso absoluto do limiar, o ruído viraria "pontos"
    assert extrai_caracteristicas(tecido_com_ruido(seed=1))["n_pontos"] == 0


def test_ignora_borda_da_mama():
    img = tecido_com_ruido()
    img[:, :60] = 0  # fundo preto à esquerda: a transição gera resposta forte no top-hat
    _, pontos = segmenta_calcificacoes(img)
    assert not pontos[:, :75].any()


def test_estrutura_grande_nao_e_microcalcificacao():
    img = pinta_pontos(tecido_com_ruido(), [(100, 100)], raio=20)
    assert extrai_caracteristicas(img)["n_pontos"] == 0


@pytest.mark.parametrize("img, esperado", [
    (np.where(np.arange(100 * 100).reshape(100, 100) % 7 == 0, 255, 0).astype(np.uint8), 1.0),
    (np.full((50, 50), 128, np.uint8), 0.0),
])
def test_fracao_binaria(img, esperado):
    assert fracao_binaria(img) == pytest.approx(esperado)
