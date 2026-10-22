import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.visualization.estilo import virgula_decimal


def test_virgula_decimal_textos():
    fig, ax = plt.subplots()
    textos = {
        "40.8%": "40,8%",
        "AUC 0.74 (IC 0.68–0.79)": "AUC 0,74 (IC 0,68–0,79)",
        "4.251.434 mamografias": "4.251.434 mamografias",  # separador de milhar
        "limiar 0.364": "limiar 0.364",                    # 3 casas: não mexe
        "2018–2022": "2018–2022",
    }
    objetos = {orig: ax.text(0, 0, orig) for orig in textos}
    ax.set_title("VPP 2.5%")
    virgula_decimal(fig)
    assert {orig: t.get_text() for orig, t in objetos.items()} == textos
    assert ax.get_title() == "VPP 2,5%"
    plt.close(fig)


def test_virgula_decimal_eixo():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0.5, 0.9])
    virgula_decimal(fig)
    fig.canvas.draw()
    rotulos = [t.get_text() for t in ax.get_yticklabels() if t.get_text()]
    assert rotulos and all("." not in r for r in rotulos)
    assert any("," in r for r in rotulos)
    plt.close(fig)
