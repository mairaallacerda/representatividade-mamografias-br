"""
Versão de DIAGNÓSTICO do scraping do INCA
--------------------------------------------
Roda cada etapa isolada, com prints detalhados, e continua mesmo se
uma das 3 páginas falhar -- assim dá pra ver exatamente onde travou.

Rode este script e me mande o que aparecer no console (principalmente
as linhas que começam com "ERRO" ou "AVISO").
"""

import io
import re
import traceback
import requests
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0 (compatível com navegador comum)"}


def diagnosticar_pagina(nome, url):
    """Baixa a página e mostra informações básicas antes de tentar parsear."""
    print(f"\n{'='*60}\n{nome}\n{url}\n{'='*60}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
    except Exception as e:
        print(f"ERRO ao acessar a URL: {e}")
        return None

    print(f"Status HTTP: {resp.status_code}")
    print(f"Tamanho do conteúdo: {len(resp.text)} caracteres")

    if resp.status_code != 200:
        print("AVISO: status diferente de 200 -- a página pode ter bloqueado "
              "o acesso automatizado ou mudado de endereço.")
        return None

    # Conta quantas tabelas existem na página crua (sem tratamento nenhum)
    try:
        tabelas = pd.read_html(io.StringIO(resp.text))
        print(f"Tabelas HTML encontradas (sem parsing especial): {len(tabelas)}")
        for i, t in enumerate(tabelas[:5]):
            print(f"  Tabela {i}: shape={t.shape}, colunas={list(t.columns)[:4]}...")
    except ValueError as e:
        print(f"AVISO: pd.read_html não encontrou NENHUMA tabela nessa página. "
              f"Erro: {e}")
        print("Isso é esperado para a página de Mortalidade (só tem texto).")

    return resp


# ---------------------------------------------------------------
# Roda o diagnóstico nas 3 páginas
# ---------------------------------------------------------------
paginas = {
    "Incidência": "https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/dados-e-numeros/incidencia",
    "Mamografias no SUS": "https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/dados-e-numeros/mamografias-no-sus",
    "Mortalidade": "https://www.gov.br/inca/pt-br/assuntos/gestor-e-profissional-de-saude/controle-do-cancer-de-mama/dados-e-numeros/mortalidade",
}

respostas = {}
for nome, url in paginas.items():
    respostas[nome] = diagnosticar_pagina(nome, url)

# ---------------------------------------------------------------
# Agora tenta rodar a extração de verdade em cada uma, capturando
# qualquer erro sem travar o script inteiro.
# ---------------------------------------------------------------
print(f"\n\n{'='*60}\nTENTANDO EXTRAÇÃO COMPLETA\n{'='*60}")

resultados = {}

# --- Incidência ---
try:
    resp = respostas["Incidência"]
    tabelas = pd.read_html(io.StringIO(resp.text), encoding="utf-8", thousands=".", decimal=",")
    df = tabelas[0]
    df.columns = ["regiao_uf", "n_casos", "taxa_bruta", "taxa_ajustada"]
    resultados["incidencia"] = df
    print(f"\n[OK] Incidência extraída: {df.shape}")
except Exception:
    print("\n[ERRO] Falhou ao extrair Incidência:")
    traceback.print_exc()

# --- Mamografias no SUS ---
try:
    resp = respostas["Mamografias no SUS"]
    tabelas = pd.read_html(io.StringIO(resp.text), encoding="utf-8", thousands=".", decimal=",")
    regioes_esperadas = {"Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"}
    candidatas = []
    for t in tabelas:
        col0 = set(t.iloc[:, 0].astype(str).str.strip())
        col0_norm = {c.replace("Região ", "") for c in col0}
        if regioes_esperadas.issubset(col0_norm):
            candidatas.append(t)
    print(f"\nTabelas regionais candidatas em Mamografias no SUS: {len(candidatas)}")
    if candidatas:
        resultados["mamografias_sus"] = candidatas[0]
        print(f"[OK] Mamografias no SUS extraída: {candidatas[0].shape}")
    else:
        print("[AVISO] Nenhuma tabela com as 5 regiões foi encontrada. "
              "Pode ser que os nomes venham diferentes (ex: com acentos "
              "diferentes ou 'Regiao' sem cedilha). Confira as colunas "
              "impressas acima em 'Tabelas HTML encontradas'.")
except Exception:
    print("\n[ERRO] Falhou ao extrair Mamografias no SUS:")
    traceback.print_exc()

# --- Mortalidade ---
try:
    resp = respostas["Mortalidade"]
    texto = resp.text
    resultado_mort = {}
    m_duplo = re.search(r"Sudeste e Sul.*?\((\d{1,2},\d{2}) e (\d{1,2},\d{2})", texto)
    if m_duplo:
        resultado_mort["Sudeste"] = float(m_duplo.group(1).replace(",", "."))
        resultado_mort["Sul"] = float(m_duplo.group(2).replace(",", "."))
    for regiao, valor in re.findall(
        r"(Nordeste|Centro-Oeste|Norte)\s*\((\d{1,2},\d{2})\s*óbitos", texto
    ):
        resultado_mort[regiao] = float(valor.replace(",", "."))
    print(f"\nRegiões encontradas via regex na Mortalidade: {resultado_mort}")
    if resultado_mort:
        resultados["mortalidade"] = pd.DataFrame(
            list(resultado_mort.items()), columns=["regiao_uf", "valor"]
        )
        print(f"[OK] Mortalidade extraída: {resultados['mortalidade'].shape}")
    else:
        print("[AVISO] O regex não encontrou nada. O texto da página pode "
              "ter mudado de redação -- me mande um trecho do texto real "
              "em torno da palavra 'óbitos' para eu ajustar o regex.")
except Exception:
    print("\n[ERRO] Falhou ao extrair Mortalidade:")
    traceback.print_exc()

# ---------------------------------------------------------------
# Salva o que deu certo
# ---------------------------------------------------------------
print(f"\n\n{'='*60}\nSALVANDO O QUE FUNCIONOU\n{'='*60}")
for nome, df in resultados.items():
    caminho = f"inca_{nome}.csv"
    df.to_csv(caminho, index=False)
    print(f"Salvo: {caminho} ({df.shape[0]} linhas)")

if not resultados:
    print("Nenhum CSV foi salvo -- todas as 3 extrações falharam. "
          "Veja os [ERRO]/[AVISO] acima para saber por quê.")