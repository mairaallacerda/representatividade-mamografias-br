"""Testes de associação entre variáveis categóricas."""

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


def cramers_v(tabela: pd.DataFrame) -> float:
    """V de Cramér (0 = sem associação, 1 = associação perfeita), com correção de viés."""
    chi2 = chi2_contingency(tabela, correction=False)[0]
    n = tabela.to_numpy().sum()
    r, k = tabela.shape
    phi2 = max(0.0, chi2 / n - (k - 1) * (r - 1) / (n - 1))
    r_corr = r - (r - 1) ** 2 / (n - 1)
    k_corr = k - (k - 1) ** 2 / (n - 1)
    return float(np.sqrt(phi2 / max(1e-12, min(k_corr - 1, r_corr - 1))))


def teste_associacao(df: pd.DataFrame, var: str, alvo: str = "maligno") -> dict:
    """Qui-quadrado de independência entre ``var`` e ``alvo`` + V de Cramér."""
    tabela = pd.crosstab(df[var], df[alvo])
    chi2, p, gl, esperado = chi2_contingency(tabela)
    return {
        "variavel": var,
        "n": int(tabela.to_numpy().sum()),
        "chi2": round(float(chi2), 1),
        "gl": int(gl),
        "p_valor": float(p),
        "v_cramer": round(cramers_v(tabela), 3),
        "esperado_min": round(float(esperado.min()), 1),  # < 5 invalida a aproximação do qui-quadrado
    }
