// =====================================================================================
// Consultas do Power Query (linguagem M) para carregar dashboards/dados/*.csv
//
// Como usar (Power BI Desktop):
//   1. Página Inicial > Transformar dados > Gerenciar parâmetros > Novo parâmetro
//        Nome: PastaDados   Tipo: Texto
//        Valor: caminho da pasta dashboards\dados\ TERMINANDO EM "\"
//        ex.: \\wsl.localhost\Ubuntu\home\mairaallacerda\representatividade-mamografias-br\dashboards\dados\
//   2. Nova fonte > Consulta nula > Editor avançado > cole o bloco "CarregarCSV" abaixo
//      e renomeie a consulta para CarregarCSV.
//   3. Para cada tabela: Nova fonte > Consulta nula > cole UMA linha da seção TABELAS
//      e renomeie a consulta com o nome indicado no comentário.
//
// Os tipos são convertidos com a cultura "en-US" porque os CSVs usam ponto decimal.
// Sem isso, um Power BI em português leria 0.73 como 73.
// =====================================================================================

// ----- CarregarCSV -------------------------------------------------------------------
(nome as text) as table =>
let
    Fonte = Csv.Document(
        File.Contents(PastaDados & nome & ".csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    ComCabecalho = Table.PromoteHeaders(Fonte, [PromoteAllScalars = true])
in
    ComCabecalho

// ----- TABELAS (uma consulta para cada linha; o nome da consulta está no comentário) --

// dim_localidade
= Table.TransformColumnTypes(CarregarCSV("dim_localidade"), {{"localidade", type text}, {"regiao", type text}, {"sigla", type text}, {"pais", type text}}, "en-US")

// fato_uf_ano
= Table.TransformColumnTypes(CarregarCSV("fato_uf_ano"), {{"localidade", type text}, {"ano", Int64.Type}, {"mamografias_rastreamento", type number}, {"mamografias_diagnosticas", type number}, {"obitos_cancer_mama", type number}}, "en-US")

// fato_incidencia_uf
= Table.TransformColumnTypes(CarregarCSV("fato_incidencia_uf"), {{"localidade", type text}, {"casos_estimados", type number}, {"taxa_bruta_100mil", type number}, {"taxa_ajustada_100mil", type number}}, "en-US")

// obitos_faixa
= Table.TransformColumnTypes(CarregarCSV("obitos_faixa"), {{"faixa_etaria", type text}, {"ano", Int64.Type}, {"obitos", type number}, {"ordem_faixa", Int64.Type}}, "en-US")

// densidade_faixa
= Table.TransformColumnTypes(CarregarCSV("densidade_faixa"), {{"faixa_etaria", type text}, {"ordem_faixa", Int64.Type}, {"densidade", Int64.Type}, {"densidade_nome", type text}, {"exames", type number}}, "en-US")

// comparacao_densidade
= Table.TransformColumnTypes(CarregarCSV("comparacao_densidade"), {{"fonte", type text}, {"densidade", Int64.Type}, {"densidade_nome", type text}, {"quantidade", type number}, {"percentual", type number}}, "en-US")

// comparacao_birads
= Table.TransformColumnTypes(CarregarCSV("comparacao_birads"), {{"fonte", type text}, {"birads", Int64.Type}, {"quantidade", type number}, {"percentual", type number}}, "en-US")

// birads_densidade_brasil
= Table.TransformColumnTypes(CarregarCSV("birads_densidade_brasil"), {{"densidade", Int64.Type}, {"densidade_nome", type text}, {"exames", type number}, {"pct_birads_0", type number}, {"pct_birads_4_5", type number}}, "en-US")

// modelo_auc_densidade
= Table.TransformColumnTypes(CarregarCSV("modelo_auc_densidade"), {{"densidade", Int64.Type}, {"densidade_nome", type text}, {"lesoes_teste", Int64.Type}, {"auc", type number}}, "en-US")

// modelo_auc_populacao
= Table.TransformColumnTypes(CarregarCSV("modelo_auc_populacao"), {{"populacao", type text}, {"auc", type number}, {"ic95_inf", type number}, {"ic95_sup", type number}, {"pct_densas", type number}, {"auc_sem_densidade_1", type number}}, "en-US")

// cbis_lesoes
= Table.TransformColumnTypes(CarregarCSV("cbis_lesoes"), {{"patient_id", type text}, {"tipo_lesao", type text}, {"densidade", type number}, {"birads", Int64.Type}, {"patologia", type text}, {"maligna", Int64.Type}, {"conjunto", type text}}, "en-US")
