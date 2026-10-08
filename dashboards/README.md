# Painel de BI

Duas versões do painel com os **mesmos dados**:

| Versão | Arquivo | Para quê |
|---|---|---|
| **Power BI** | `powerbi/` (kit de montagem) | Versão prevista no pré-projeto. Montada no Power BI Desktop seguindo o roteiro abaixo |
| **HTML interativo** | `painel.html` | Funciona direto no navegador, sem instalar nada. Bom para apresentar e compartilhar |

Os dados vêm de `dados/`, gerados a partir dos scrapers e dos notebooks:

```bash
python -m src.visualization.painel_dados   # gera dashboards/dados/*.csv e indicadores.json
python -m src.visualization.painel_html    # gera dashboards/painel.html
```

## Modelo de dados

```
dim_localidade (1 linha por UF: localidade, regiao, sigla)
   │ 1
   ├──* fato_uf_ano          mamografias (SIA) e óbitos (SIM) por UF × ano, 2018–2022
   └──* fato_incidencia_uf   casos estimados e taxas (INCA, 2023) por UF

Tabelas independentes (já agregadas):
   obitos_faixa              óbitos por faixa etária × ano (SIM)
   densidade_faixa           exames por densidade × faixa etária (SISCAN)
   comparacao_densidade      % por densidade: Brasil × CBIS-DDSM (todas, massas, calcificações)
   comparacao_birads         % por BI-RADS: Brasil rastreamento / diagnóstica × CBIS-DDSM
   birads_densidade_brasil   % BI-RADS 0 e 4–5 por densidade (SISCAN)
   modelo_auc_densidade      AUC do modelo de calcificações por densidade
   modelo_auc_populacao      AUC reponderada por população (Brasil geral e por faixa etária)
   cbis_lesoes               1 linha por lesão do CBIS-DDSM (tipo, densidade, BI-RADS, patologia)
```

Região e Brasil **não** estão nas tabelas de fato: são a soma das UFs, pela hierarquia `regiao > localidade` de
`dim_localidade`. Assim os totais nunca ficam duplicados.

## Montando no Power BI Desktop

O Power BI Desktop é gratuito e roda no Windows (Microsoft Store → "Power BI Desktop").

### 1. Carregar os dados

1. **Transformar dados → Gerenciar parâmetros → Novo parâmetro**: `PastaDados`, tipo Texto, com o caminho de
   `dashboards\dados\` **terminando em `\`**. Pela rede do WSL, o caminho é:
   `\\wsl.localhost\Ubuntu\home\mairaallacerda\representatividade-mamografias-br\dashboards\dados\`
   (se o Power BI não conseguir abrir esse caminho, copie a pasta `dados` para o Windows e use o caminho da cópia).
2. Crie as consultas de [`powerbi/consultas.pq`](powerbi/consultas.pq): primeiro `CarregarCSV` e depois uma
   consulta por tabela. As instruções estão no topo do arquivo.
3. **Fechar e aplicar.**

> Por que não usar "Obter dados → Texto/CSV" direto? Os CSVs usam **ponto decimal**. Num Power BI em português,
> a importação automática leria `0.73` como `73`. As consultas do kit forçam a cultura `en-US` na conversão de
> tipos.

### 2. Relações (Exibição de modelo)

- `dim_localidade[localidade]` 1 → * `fato_uf_ano[localidade]`
- `dim_localidade[localidade]` 1 → * `fato_incidencia_uf[localidade]`

Em `dim_localidade`, crie a hierarquia **Região → UF** (`regiao`, `localidade`) e, em **Ferramentas de coluna →
Categoria de dados**, marque `sigla` como **Estado ou província** (para o mapa).

Ordenação: em `obitos_faixa` e `densidade_faixa`, selecione `faixa_etaria` → **Classificar por coluna** →
`ordem_faixa`.

### 3. Medidas e tema

- Crie uma tabela vazia `Medidas` (**Inserir dados → Carregar**) e adicione as medidas de
  [`powerbi/medidas.dax`](powerbi/medidas.dax).
- **Exibir → Temas → Procurar temas** → [`powerbi/tema_projeto.json`](powerbi/tema_projeto.json). É a mesma paleta
  das figuras dos notebooks (verde-água = Brasil, azul = CBIS-DDSM, laranja = diagnóstica), validada para
  daltonismo.

### 4. Páginas

**Página 1: Brasil (rastreamento e mortalidade)**

| Visual | Campos |
|---|---|
| 4 cartões | `Mamografias` (filtro ano = 2022), `Óbitos` (ano = 2022), `Casos estimados`, `Variação vs 2019` (ano = 2020) |
| Gráfico de linhas | Eixo X: `fato_uf_ano[ano]`; Valores: `Rastreamentos`, `Mamografias diagnósticas` |
| Mapa coroplético | Local: `dim_localidade[sigla]`; Saturação: `Rastreamentos 2022 por caso estimado` |
| Barras horizontais | Eixo: hierarquia Região → UF; Valores: `Rastreamentos 2022 por caso estimado` |
| Colunas | Eixo: `obitos_faixa[faixa_etaria]`; Valores: soma de `obitos` |
| Segmentações | `fato_uf_ano[ano]`, `dim_localidade[regiao]` |

**Página 2: Brasil × CBIS-DDSM**

| Visual | Campos |
|---|---|
| Colunas clusterizadas | Eixo: `comparacao_densidade[densidade_nome]`; Legenda: `fonte`; Valores: `% da fonte (densidade)`. Filtro do visual: `fonte` = Brasil (SISCAN) e CBIS-DDSM |
| Gráfico de linhas | Eixo: `densidade_faixa[faixa_etaria]`; Valores: `% Mamas densas`; adicione uma **linha constante** em 0,46 (CBIS-DDSM) no painel Analytics |
| Colunas clusterizadas | Eixo: `comparacao_birads[birads]`; Legenda: `fonte`; Valores: `% da fonte (BI-RADS)` |
| 3 cartões | `% Malignas CBIS`, `Casos por 100 mamografias`, `Razão case mix` |

**Página 3: Modelo e viés**

| Visual | Campos |
|---|---|
| Colunas | Eixo: `modelo_auc_densidade[densidade_nome]`; Valores: `AUC por densidade`; linha constante em 0,5 (acaso) |
| Barras horizontais | Eixo: `modelo_auc_populacao[populacao]`; Valores: `AUC`; Dica de ferramenta: `IC 95% (texto)`, `pct_densas` |
| Colunas | Eixo: `birads_densidade_brasil[densidade_nome]`; Valores: `pct_birads_0` (laudos inconclusivos no Brasil) |
| Caixa de texto | Leitura: "a AUC cai com a densidade; no Brasil, a densidade cai com a idade" |

**Página 4: Explorar o CBIS-DDSM**

| Visual | Campos |
|---|---|
| Segmentações | `cbis_lesoes[tipo_lesao]`, `cbis_lesoes[conjunto]` |
| Colunas | Eixo: `cbis_lesoes[densidade]`; Valores: `% Malignas CBIS` |
| Colunas | Eixo: `cbis_lesoes[birads]`; Valores: `% Malignas CBIS` |
| Barras | Eixo: `cbis_lesoes[patologia]`; Valores: `Lesões CBIS` |
| Cartões | `Lesões CBIS`, `Pacientes CBIS` |

Salve como `dashboards/painel_representatividade.pbix`.

### Conferência

Com tudo montado, os cartões devem mostrar (sem filtros extras):

| Medida | Valor esperado |
|---|---|
| Mamografias (2022) | 4.251.434 |
| Óbitos (2022) | 19.103 |
| Casos estimados | 73.610 |
| Variação vs 2019 (2020) | −39,9% |
| % Malignas CBIS | 40,8% |
| Razão case mix | ≈ 23,6 |
