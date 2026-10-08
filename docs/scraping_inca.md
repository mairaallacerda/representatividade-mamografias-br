# Scraping do INCA — análise das páginas e decisões

Código: [`src/scraping/inca.py`](../src/scraping/inca.py)

```bash
python -m src.scraping.inca            # baixa (se necessário) e extrai
python -m src.scraping.inca --forcar   # baixa tudo de novo
python -m src.scraping.inca --offline  # só extrai, a partir do HTML salvo
```

## Tipo de scraping

**Direcionado**: um conjunto fixo e conhecido de páginas em
`gov.br/inca/.../controle-do-cancer-de-mama/dados-e-numeros/`. As páginas são **estáticas**
(o HTML já vem com as tabelas, sem JavaScript) e acessadas por **GET**, sem parâmetros na URL.
Por isso, `requests` + `BeautifulSoup` bastam, sem necessidade de Selenium.

## Estrutura de cada página

| Página | O que tem | Como extrair |
|---|---|---|
| `incidencia` | 1 `<table>`: casos estimados, taxa bruta e taxa ajustada por região/UF (estimativa 2023) | `find("table")`; a tabela tem uma coluna vazia "espaçadora", que é removida |
| `mamografias-no-sus` | 5 `<table>` (ver abaixo) | `find_all("table")`; o título de cada tabela está em um `<p>` anterior ("Tabela N. ...") e é usado para descobrir ano, finalidade e faixa etária |
| `mortalidade` | **nenhuma tabela**: os números estão no texto corrido e em figuras | expressões regulares sobre o texto (`re`) |

Tabelas de `mamografias-no-sus` (fonte original: SIA/SUS):

| Tabela | Conteúdo | Período |
|---|---|---|
| 1 | Mamografias por tipo (diagnóstica × rastreamento) e região | 2022 |
| 2 | Rastreamento em mulheres de 50 a 69 anos, por UF | **2018–2022** |
| 3 | Rastreamento por faixa etária e UF | 2022 |
| 4 | Diagnóstica (todas as idades), por UF | **2018–2022** |
| 5 | Diagnóstica por faixa etária e UF | 2022 |

> A versão anterior do script usava só a Tabela 1. As Tabelas 2 e 4 cobrem exatamente o
> período 2018–2022 previsto na proposta.

## Etapas

1. **Coleta**: o HTML bruto é salvo em `data/raw/inca/*.html`, e a data da coleta fica em `coleta.json`.
   Separar a coleta do parsing permite reprocessar sem acessar o site e guarda uma "foto" da fonte.
2. **Extração**: as tabelas largas são convertidas para **formato longo** (uma linha por
   localidade × ano/faixa × valor), com as colunas padronizadas `localidade`, `nivel` (uf/regiao/brasil) e `regiao`.
   Saída em `data/interim/inca_*.csv`.
3. **Validação**: a soma das UFs é comparada com o total da região, e a soma das regiões com o total do Brasil.

## Problemas encontrados na fonte (detectados pela validação)

| Página | Problema | Interpretação |
|---|---|---|
| Incidência | Sudeste declarado = **30.330**; soma das UFs = **39.330** | Erro de digitação na linha da região. O total Brasil (73.610) só fecha com 39.330 |
| Mamografias, Tabela 5 | Brasil, 50 a 59 anos: declarado = **12.301**; soma das regiões = **112.301** | Falta um dígito no total |
| Mamografias, Tabela 5 | Pequenas diferenças UF × região (Sul <30: 63; Sul 40–49: 7; Nordeste >70: 30) | Provável arredondamento ou atualização parcial da fonte |

Os CSVs mantêm os valores **como publicados**. As correções ficam para a etapa de tratamento
(`src/processing/`), usando preferencialmente as somas das UFs.

## Limitações

- O layout é HTML de CMS (Plone/gov.br). Mudanças de redação podem quebrar o regex de mortalidade.
  Nesse caso o script avisa as regiões que não foram encontradas.
- A mortalidade por UF e a série histórica aparecem **apenas como figuras** (imagens), sem dados no HTML.
  Para séries de mortalidade, a fonte adequada é o SIM/DATASUS (TABNET).
