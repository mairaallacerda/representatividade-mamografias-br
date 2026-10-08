# Scraping do TABNET/DATASUS — análise do formulário e decisões

Código: [`src/scraping/tabnet.py`](../src/scraping/tabnet.py)

```bash
python -m src.scraping.tabnet            # coleta (se necessário) e extrai
python -m src.scraping.tabnet --forcar   # refaz todas as consultas
python -m src.scraping.tabnet --offline  # só extrai, a partir do HTML salvo
```

## Análise da estrutura

Diferente do INCA, o TABNET **não expõe os dados por URL com parâmetros (GET)**. Cada base é um
formulário HTML:

| Etapa | URL | Método |
|---|---|---|
| Formulário | `http://tabnet.datasus.gov.br/cgi/deftohtm.exe?<base>.def` | GET |
| Resultado | `http://tabnet.datasus.gov.br/cgi/tabcgi.exe?<base>.def` | **POST** |

Campos principais do formulário (`<select>`):

| Campo | Significado | Exemplo de valor enviado |
|---|---|---|
| `Linha` | variável nas linhas | `Região/Unidade_da_Federação` |
| `Coluna` | variável nas colunas | `Ano_do_Óbito` |
| `Incremento` | medida | `Óbitos_p/Residênc`, `Qtd.apresentada` |
| `Arquivos` | períodos (um arquivo `.dbf` por ano ou mês, seleção múltipla) | `obtuf22.dbf`, `qauf2212.dbf` |
| `S<variável>` | filtros (seleção múltipla) | `SSexo=2` (Fem) |

Os **valores das opções são códigos internos** (ex.: "Fem" → `2`, procedimento 0204030188 → um índice
entre 5.709 opções). Por isso o scraper **lê o formulário antes de cada coleta** e escolhe as opções
pelo texto visível. Nada é fixado no código.

## Problemas encontrados e soluções

| Problema | Sintoma | Solução |
|---|---|---|
| Codificação do POST | O servidor respondia `Tabela de conversao nao encontrada` | O TABNET só entende os campos com acento (`Região/Unidade_da_Federação`) em **ISO-8859-1**. O corpo do POST é codificado com `urlencode(..., encoding="latin-1")` |
| Página de erro salva como dado | O HTML de erro era gravado como se fosse resultado | Antes de salvar, o scraper verifica se há tabela de resultado |
| Estrutura da tabela | A `table.tabdados` mistura o título da consulta e as notas da fonte com os dados | O cabeçalho é a linha com `<th>`; são dados só as linhas com o mesmo nº de colunas; o resto vira metadado (`fonte`) |
| Rótulos | UFs indentadas (`.. Acre`), total em maiúsculas (`TOTAL`), `-` para zero | Normalização em `classifica_linha` e `limpa_numero` |

## Consultas realizadas (2018–2022)

| Arquivo (`data/interim/`) | Base | Filtros | Linhas × colunas |
|---|---|---|---|
| `datasus_sia_mamografia_diagnostica_uf_ano.csv` | SIA (`sia/cnv/qauf.def`) | Procedimento 0204030030 | UF × ano de processamento |
| `datasus_sia_mamografia_rastreamento_uf_ano.csv` | SIA | Procedimento 0204030188 | UF × ano de processamento |
| `datasus_sim_obitos_mama_uf_ano.csv` | SIM (`sim/cnv/obt10uf.def`) | CID-BR-10 041 (mama), sexo feminino | UF × ano do óbito |
| `datasus_sim_obitos_mama_faixa_ano.csv` | SIM | idem | faixa etária × ano do óbito |

O POST exato de cada consulta e a data da coleta ficam em `data/raw/datasus/coleta.json`.

## Validação cruzada com o INCA

As mamografias diagnósticas do SIA são a mesma fonte da Tabela 4 do INCA:

| Ano | TABNET | INCA | Diferença |
|---|---|---|---|
| 2018 | 384.523 | 373.189 | +3,0% |
| 2019 | 384.400 | 373.483 | +2,9% |
| 2020 | 300.447 | 293.650 | +2,3% |
| 2021 | 358.840 | 351.509 | +2,1% |
| 2022 | 386.006 | 382.658 | +0,9% |

O TABNET fica sempre um pouco acima. A explicação mais provável é que o INCA conta **só mulheres**,
enquanto o formulário `qauf` do SIA não tem filtro de sexo. Também pode haver atualizações da base
depois da consulta do INCA (set/2023). A série é coerente com a do INCA, inclusive na queda de 2020.

## Limitações

- O SIA conta **exames apresentados**, não pessoas, e não informa sexo nem idade neste formulário.
- O SIM só tem dados finais até 2024; anos mais recentes são preliminares (ver a coluna `fonte`).
- O TABNET é lento e às vezes fica fora do ar. O scraper faz 3 tentativas com espera crescente.
