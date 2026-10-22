#!/usr/bin/env bash
# Refaz o projeto inteiro na ordem certa: coleta → notebooks → dados do painel → painel → testes.
#
# Uso:
#   ./rodar_tudo.sh               # coleta só o que ainda não foi baixado e roda tudo
#   ./rodar_tudo.sh --sem-coleta  # não acessa a internet; usa o HTML já salvo em data/raw/
#
# O notebook 02 precisa das imagens do CBIS-DDSM (data/raw/cbis-ddsm/jpeg, ver README). Sem elas, ele é pulado
# e os passos seguintes usam os resultados que ele salvou antes em data/processed/, se existirem.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-.venv/bin/python}"

coleta=""
[[ "${1:-}" == "--sem-coleta" ]] && coleta="--offline"

passo() { printf '\n==> %s\n' "$*"; }
notebook() {
  passo "notebook $1"
  (cd notebooks && "../$PY" -m jupyter nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=1800 "$1")
}

passo "coleta e extração: INCA, TABNET (SIA/SIM) e SISCAN"
for fonte in inca tabnet siscan; do
  "$PY" -m "src.scraping.$fonte" $coleta
done

notebook 01_analise_exploratoria.ipynb

if [[ -n "$(ls -A data/raw/cbis-ddsm/jpeg 2>/dev/null)" ]]; then
  notebook 02_imagens_calcificacoes.ipynb
elif [[ -f data/processed/cbis_predicoes_teste_calcificacoes.csv && -f data/processed/vpp_regiao.csv ]]; then
  passo "notebook 02 pulado: imagens não encontradas; usando os resultados salvos em data/processed/"
else
  echo "Erro: o notebook 02 precisa das imagens do CBIS-DDSM em data/raw/cbis-ddsm/jpeg (ver README)." >&2
  exit 1
fi

notebook 03_comparacao_birads_densidade.ipynb

passo "dados do painel"
"$PY" -m src.visualization.painel_dados

notebook 04_quadro_sintese.ipynb

passo "painel"
"$PY" -m src.visualization.painel_html

passo "testes"
"$PY" -m pytest -q
