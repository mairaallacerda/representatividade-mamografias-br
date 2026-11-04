# Painel interativo

O painel do projeto é o **`painel.html`**: um arquivo único, que abre direto no navegador, sem servidor e sem
instalar nada. Os dados vão embutidos no próprio arquivo, então ele pode ser copiado ou enviado por e-mail e abre em
qualquer computador. Só precisa de internet para carregar a biblioteca de gráficos (Chart.js) e as fontes.

## Abrir

Dê dois cliques em `painel.html` no Explorador de Arquivos (pelo Windows, a pasta fica em
`\\wsl.localhost\Ubuntu\home\mairaallacerda\representatividade-mamografias-br\dashboards`) ou, no terminal do Ubuntu,
na pasta do projeto:

```bash
explorer.exe dashboards/painel.html
```

## Conteúdo

| Aba | Filtro | Gráficos |
|---|---|---|
| **Brasil** | região | mamografias por finalidade (2018–2022), óbitos, rastreamentos por caso estimado por UF, óbitos por faixa etária |
| **Regiões** | ▶ reproduzir / barra de anos · indicador · indicador do mapa · região em destaque | rastreamento ano a ano, 2018–2022 (mapa por UF e regiões em relação a 2019, animados); indicadores por região (incidência e mortalidade ajustadas, rastreamento por 1.000 mulheres e por caso, óbitos por caso, % mamas densas, AUC estimada), mapa em grade por UF, rastreamento em relação a 2019 (pandemia), VPP do modelo em cada região |
| **Brasil × CBIS-DDSM** | todas as lesões / massas / calcificações | densidade mamária nas duas bases, densidade por idade no Brasil, BI-RADS nas duas bases |
| **Modelo e viés** | — | AUC por densidade, laudos inconclusivos (BI-RADS 0) por densidade, AUC reponderada pela composição brasileira |

O painel acompanha o modo claro/escuro do sistema.

## Atualizar

O painel é gerado a partir de `dados/`, que por sua vez vem dos scrapers e dos notebooks:

```
scrapers + notebooks → dashboards/dados/*.csv → src/visualization/painel_html.py → dashboards/painel.html
```

```bash
python -m src.visualization.painel_dados   # gera dashboards/dados/*.csv e indicadores.json
python -m src.visualization.painel_html    # gera dashboards/painel.html
```

`src/visualization/painel_modelo.html` é o molde (layout, gráficos e JavaScript), com o marcador `__DADOS_JSON__`
no lugar dos dados; `painel_html.py` lê os CSVs e coloca os dados no lugar do marcador. Para mudar a aparência ou
os gráficos, edite o **molde**: o `painel.html` é sobrescrito a cada geração.

## Dados (`dados/`)

```
dim_localidade (1 linha por UF: localidade, regiao, sigla)
   │ 1
   ├──* fato_uf_ano          mamografias (SIA) e óbitos (SIM) por UF × ano, 2018–2022
   └──* fato_incidencia_uf   casos estimados e taxas (INCA, 2023) por UF

Tabelas independentes (já agregadas):
   taxas_regiao              incidência (2023) e mortalidade (2021) ajustadas por idade, por região (INCA)
   modelo_vpp_regiao         VPP do modelo de calcificações com a prevalência de cada região (notebook 02)
   siscan_regiao             % mamas densas (bruta e padronizada por idade), w × CBIS-DDSM e AUC por região (notebook 03)
   siscan_densidade_uf       % mamas densas por UF (SISCAN, notebook 03)
   obitos_faixa              óbitos por faixa etária × ano (SIM)
   densidade_faixa           exames por densidade × faixa etária (SISCAN)
   comparacao_densidade      % por densidade: Brasil × CBIS-DDSM (todas, massas, calcificações)
   comparacao_birads         % por BI-RADS: Brasil rastreamento / diagnóstica × CBIS-DDSM
   birads_densidade_brasil   % BI-RADS 0 e 4–5 por densidade (SISCAN)
   modelo_auc_densidade      AUC do modelo de calcificações por densidade
   modelo_auc_populacao      AUC reponderada por população (Brasil geral e por faixa etária)
   cbis_lesoes               1 linha por lesão do CBIS-DDSM (tipo, densidade, BI-RADS, patologia); não entra no painel
indicadores.json             números-resumo usados nos cartões do painel
```

Região e Brasil **não** estão nas tabelas de fato: são a soma das UFs (via `dim_localidade`), para que os totais
nunca fiquem duplicados.
