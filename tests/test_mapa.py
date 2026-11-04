import pytest

from src.visualization.mapa import SIGLA_IBGE, aneis


def test_aneis_polygon_e_multipolygon():
    quadrado = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    buraco = [[0.2, 0.2], [0.4, 0.2], [0.4, 0.4], [0.2, 0.2]]
    assert len(aneis({"type": "Polygon", "coordinates": [quadrado, buraco]})) == 1  # buraco ignorado
    multi = aneis({"type": "MultiPolygon", "coordinates": [[quadrado], [quadrado]]})
    assert len(multi) == 2 and multi[0].shape == (5, 2)
    with pytest.raises(ValueError):
        aneis({"type": "Point", "coordinates": [0, 0]})


def test_siglas_cobrem_as_27_ufs():
    assert len(SIGLA_IBGE) == 27 and len(set(SIGLA_IBGE.values())) == 27
