# Scraping do SISCAN: laudos de mamografia (BI-RADS e densidade)

Código: [`src/scraping/siscan.py`](../src/scraping/siscan.py)

```bash
python -m src.scraping.siscan            # coleta (se necessário) e extrai
python -m src.scraping.siscan --forcar   # refaz todas as consultas
python -m src.scraping.siscan --offline  # só extrai, a partir do HTML salvo
```

O SISCAN é a única fonte pública com o **resultado do laudo** das mamografias do SUS: categoria **BI-RADS** e
**tipo de mama** (a densidade). São as duas variáveis que permitem comparar diretamente o Brasil com o CBIS-DDSM.

## Como o formulário foi encontrado

Foram necessárias quatro etapas de investigação, e cada uma vale como exemplo para o relatório:

1. **Os links não aparecem no HTML "visível".** Na página do SISCAN no site do DATASUS, as consultas ficam num
   `<select>` preenchido por **JavaScript**. Uma ferramenta que só lê o texto da página não encontra nada. No
   código-fonte, os links estão num array JavaScript.
2. **O link publicado está incompleto.** `dhdat.exe?siscan/mamografia_resid` devolve um erro Python do servidor
   (`No such file or directory`). Lendo a função `Atualiza_Variavel()` da página, descobrimos que o JavaScript
   completa o link com a abrangência e a extensão: `mamografia_resid` + `br` + `.def`.
3. **O formulário é de outra versão do TABNET (TabnetBD).** O `<form>` não tem `action`. Uma função JavaScript
   (`OnButton1()`) define o destino na hora do clique: POST para `webtabx.exe`.
4. **O resultado não vem em `<table>`.** Os números estão dentro de um `<script>` que monta uma tabela do Google
   Charts (`data.addColumn(...)`, `data.addRows([...])`). O parser lê esse JavaScript com expressões regulares.

| | SIA/SIM ([`tabnet.py`](../src/scraping/tabnet.py)) | SISCAN (`siscan.py`) |
|---|---|---|
| Formulário | `deftohtm.exe?<def>` | `dhdat.exe?<def>` |
| Envio | POST `tabcgi.exe` | POST `webtabx.exe` |
| Períodos | campo `Arquivos` | campo `PAno competencia` |
| Filtros | `S...` | `S...` e `X...` |
| Resultado | `<table class="tabdados">` | JavaScript (Google Charts) |
| Codificação do POST | ISO-8859-1 | ISO-8859-1 |

As partes comuns (ler as opções do formulário e escolher pelo texto) são reaproveitadas de `tabnet.py`.

## Consultas (mulheres, por residência, Brasil, 2018–2022)

| Arquivo (`data/interim/`) | Linhas × colunas |
|---|---|
| `siscan_densidade_ano.csv` | tipo de mama (direita) × ano |
| `siscan_densidade_esq_ano.csv` | tipo de mama (esquerda) × ano. Validação: deve ser quase igual à direita |
| `siscan_densidade_faixa.csv` | tipo de mama × faixa etária (5 em 5 anos) |
| `siscan_densidade_indicacao.csv` | tipo de mama × indicação (diagnóstica/rastreamento) |
| `siscan_birads_ano.csv` | BI-RADS × ano |
| `siscan_birads_indicacao.csv` | BI-RADS × indicação |
| `siscan_birads_densidade.csv` | BI-RADS × tipo de mama |

**Tipo de mama → densidade BI-RADS** (mesma escala do CBIS-DDSM): Adiposa = 1, Predominantemente adiposa = 2,
Predominantemente densa = 3, Densa = 4. "Implante", "reconstruída" e "ignorado" ficam fora da escala.

## Validação

- Em todas as consultas, a soma das células extraídas é igual ao total geral informado pela fonte.
- Mama direita × esquerda: 15,7 / 34,1 / 34,2 / 16,0 % contra 15,7 / 34,0 / 34,3 / 15,9 %. É o esperado, já que a
  densidade é quase sempre simétrica.

## Limitações

- O SISCAN **não cobre todo o SUS**. Em 2022 registrou cerca de 3,0 milhões de mamografias em mulheres, contra cerca
  de 4,25 milhões no SIA (faturamento). A adesão ao sistema varia entre estados e municípios.
- Quase todos os laudos no SISCAN são de **rastreamento** (≈ 97%). As mamografias diagnósticas registradas são poucas.
- A unidade é o **exame**, não a mulher: a mesma pessoa pode aparecer em vários anos.
