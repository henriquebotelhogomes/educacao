"""
Internal script: generates evals/datasets/v1/golden.jsonl.

Run once to (re)create the dataset skeleton:
    python evals/_build_golden.py

All 120 items carry review_status='draft'. Human curators must:
  1. Verify each resposta_referencia against the actual PDF pages.
  2. Update review_status to 'reviewed' and then 'approved' per item.
  3. Run `python evals/validate.py freeze` after every item reaches 'approved'.

Do NOT fabricate benchmark scores against draft items.
"""

from __future__ import annotations

import json
import pathlib

# ---------------------------------------------------------------------------
# Raw data: (id, pergunta, resposta_referencia_or_null, documento,
#            paginas_esperadas, tipo, dificuldade, notas_or_null)
# ---------------------------------------------------------------------------

DOC_HA = "História Agrária.pdf"
DOC_MA = "historia-das-agriculturas-no-mundo-mazoyer-e-roudart.pdf"
DOC_PP = "Políticas-públicas-agricultura-familiar-e-sustentabilidade.pdf"
DOC_BH = "buhler-9786557250044.pdf"
DOC_MU = "LIVRO  MUNDIALIZAÇÃO pronto.pdf"
DOC_CG = "ph,+Gerente+da+editora,+cerrado-goiano.pdf"

A = "answerable"
U = "unanswerable"
AP = "ambiguous_partial"
F = "facil"
M = "medio"
D = "dificil"

ITEMS_RAW: list[tuple] = [
    # -----------------------------------------------------------------------
    # História Agrária.pdf — narrative — 315 pages
    # -----------------------------------------------------------------------
    (
        "v1-ha-001",
        F,
        A,
        DOC_HA,
        [12, 13],
        "O que é a questão agrária no contexto histórico brasileiro?",
        "A questão agrária refere-se ao problema da distribuição desigual da terra no "
        "Brasil, marcada pela concentração fundiária desde o período colonial.",
        None,
    ),
    (
        "v1-ha-002",
        F,
        A,
        DOC_HA,
        [25, 26],
        "Como o sistema de sesmarias influenciou a estrutura fundiária colonial?",
        "O sistema de sesmarias distribuía grandes extensões de terra para poucos "
        "beneficiários, consolidando o latifúndio como base da estrutura agrária colonial.",
        None,
    ),
    (
        "v1-ha-003",
        F,
        A,
        DOC_HA,
        [45, 46],
        "Qual foi o papel da escravidão na formação da agricultura brasileira?",
        "A escravidão foi fundamental para o funcionamento das grandes propriedades "
        "monocultoras, especialmente nos engenhos de açúcar e nas fazendas de café.",
        None,
    ),
    (
        "v1-ha-004",
        M,
        A,
        DOC_HA,
        [78, 79, 80],
        "Como a Lei de Terras de 1850 transformou o acesso à propriedade fundiária?",
        "A Lei de Terras de 1850 estabeleceu que a terra só poderia ser adquirida por "
        "compra e venda, excluindo os trabalhadores pobres do acesso à propriedade e "
        "consolidando o poder dos grandes latifundiários.",
        None,
    ),
    (
        "v1-ha-005",
        M,
        A,
        DOC_HA,
        [95, 96],
        "De que forma a expansão cafeeira do século XIX modificou a estrutura agrária brasileira?",
        "A expansão cafeeira gerou uma nova elite fundiária no Oeste Paulista, "
        "impulsionou a imigração europeia como mão de obra e criou o sistema de colonato "
        "como forma de trabalho livre na cafeicultura.",
        None,
    ),
    (
        "v1-ha-006",
        M,
        A,
        DOC_HA,
        [142, 143],
        "Quais foram as principais características do campesinato brasileiro no século XX?",
        "O campesinato brasileiro caracterizou-se pela posse precária da terra, "
        "subordinação ao coronelismo local, produção de subsistência e constante ameaça "
        "de expulsão pelas frentes de expansão do agronegócio.",
        None,
    ),
    (
        "v1-ha-007",
        M,
        A,
        DOC_HA,
        [165, 166, 167],
        "Como os conflitos de terra marcaram a história agrária brasileira?",
        "Os conflitos de terra, como as lutas dos posseiros e trabalhadores sem-terra, "
        "foram constantes na história agrária, culminando na formação de movimentos como "
        "as Ligas Camponesas e o MST.",
        None,
    ),
    (
        "v1-ha-008",
        D,
        A,
        DOC_HA,
        [188, 189],
        "Qual é a relação entre industrialização e questão agrária no Brasil pós-1950?",
        "A industrialização acelerada impulsionou o êxodo rural, transformando a questão "
        "agrária ao gerar uma reserva de mão de obra urbana oriunda do campo, enquanto "
        "manteve a estrutura fundiária concentrada para assegurar oferta de alimentos "
        "baratos à indústria.",
        None,
    ),
    (
        "v1-ha-009",
        D,
        A,
        DOC_HA,
        [215, 216, 217],
        "Como a modernização conservadora da agricultura brasileira nas décadas de 1960 "
        "e 1970 afetou os trabalhadores rurais?",
        "A modernização conservadora incorporou tecnologia e insumos químicos nas grandes "
        "propriedades sem alterar a estrutura fundiária, expulsando trabalhadores rurais, "
        "mecanizando a produção e aprofundando as desigualdades no campo.",
        None,
    ),
    (
        "v1-ha-010",
        D,
        A,
        DOC_HA,
        [245, 246],
        "Quais correntes teóricas disputaram a interpretação da questão agrária "
        "brasileira ao longo do século XX?",
        "Disputaram-se a corrente estruturalista (via CEPAL), que via o latifúndio como "
        "obstáculo ao desenvolvimento, a corrente marxista, que interpretava a questão "
        "agrária como expressão do capitalismo, e a corrente que defendia a reforma "
        "agrária como requisito para a democratização.",
        None,
    ),
    (
        "v1-ha-011",
        F,
        A,
        DOC_HA,
        [270, 271],
        "O que diferencia o latifúndio improdutivo do agronegócio moderno na "
        "historiografia agrária brasileira?",
        "O latifúndio improdutivo caracterizava-se pela baixa utilização da terra e uso "
        "extensivo da mão de obra, enquanto o agronegócio moderno é marcado pela alta "
        "produtividade, mecanização e integração ao mercado internacional.",
        None,
    ),
    (
        "v1-ha-012",
        M,
        A,
        DOC_HA,
        [298, 299],
        "Como a Constituição de 1988 tratou a questão da reforma agrária?",
        "A Constituição de 1988 estabeleceu a função social da propriedade rural, "
        "prevendo a desapropriação de imóveis que não cumpram essa função, e criou "
        "mecanismos para a reforma agrária, embora limitados na prática.",
        None,
    ),
    (
        "v1-ha-013",
        F,
        U,
        DOC_HA,
        [1],
        "Qual será o número de assentamentos da reforma agrária no Brasil em 2030?",
        None,
        "Dado futuro não disponível no texto; o livro trata de perspectiva histórica, "
        "sem projeções quantitativas para 2030.",
    ),
    (
        "v1-ha-014",
        F,
        U,
        DOC_HA,
        [1],
        "Qual é o e-mail do autor para contato sobre a obra?",
        None,
        "Informação de contato pessoal do autor não consta no livro.",
    ),
    (
        "v1-ha-015",
        M,
        U,
        DOC_HA,
        [1],
        "Quais são os dados do cadastro rural individual dos agricultores mencionados "
        "como exemplos históricos?",
        None,
        "Dados individuais de cadastro de agricultores específicos não constam no texto; "
        "o livro opera em nível analítico-histórico.",
    ),
    (
        "v1-ha-016",
        M,
        U,
        DOC_HA,
        [1],
        "Qual é o preço médio por hectare das terras discutidas no livro no mercado atual?",
        None,
        "Preços de mercado atuais não são fornecidos; o livro analisa estruturas "
        "históricas, não cotações correntes.",
    ),
    (
        "v1-ha-017",
        D,
        U,
        DOC_HA,
        [1],
        "Qual é o posicionamento político-partidário do autor sobre a reforma agrária "
        "brasileira hoje?",
        None,
        "Posicionamento político pessoal do autor não é explicitado no texto; o livro "
        "adota perspectiva acadêmica histórica.",
    ),
    (
        "v1-ha-018",
        M,
        AP,
        DOC_HA,
        [200, 201, 250, 251],
        "A reforma agrária no Brasil foi bem-sucedida?",
        "O texto discute tanto conquistas dos assentamentos quanto suas limitações "
        "(falta de crédito, assistência técnica e infraestrutura), sem emitir um "
        "julgamento definitivo sobre o êxito global da reforma agrária.",
        "Ambíguo: o livro apresenta múltiplas perspectivas sobre os resultados da "
        "reforma agrária sem conclusão avaliativa definitiva.",
    ),
    (
        "v1-ha-019",
        F,
        AP,
        DOC_HA,
        [18, 19],
        "O que é um camponês?",
        "O texto apresenta diferentes concepções de camponês, incluindo definições "
        "baseadas em relação com a terra, autonomia produtiva e posição no modo de "
        "produção, sem adotar uma única definição canônica.",
        "Parcial: o livro apresenta múltiplas definições em disputa sem consolidar uma "
        "única resposta.",
    ),
    (
        "v1-ha-020",
        D,
        AP,
        DOC_HA,
        [260, 261],
        "Como se compara a concentração fundiária brasileira com a de países da América Latina?",
        "O texto faz algumas referências comparativas à América Latina, mas não fornece "
        "análise sistemática comparativa entre países; os dados comparativos são "
        "fragmentados.",
        "Parcial: o livro aborda comparações pontuais, não um estudo comparativo sistemático.",
    ),
    # -----------------------------------------------------------------------
    # historia-das-agriculturas-no-mundo-mazoyer-e-roudart.pdf
    # narrative — 569 pages
    # -----------------------------------------------------------------------
    (
        "v1-ma-001",
        F,
        A,
        DOC_MA,
        [35, 36],
        "Onde e quando surgiram os primeiros focos independentes de agricultura neolítica?",
        "Os primeiros focos de agricultura neolítica surgiram por volta de 10.000 a.C. "
        "no Crescente Fértil (Oriente Médio), e de forma independente na China (c. "
        "7.000 a.C.) e na América Central (c. 5.000 a.C.).",
        None,
    ),
    (
        "v1-ma-002",
        F,
        A,
        DOC_MA,
        [42, 43],
        "Quais foram as principais plantas domesticadas durante a revolução neolítica?",
        "As principais plantas domesticadas foram o trigo e a cevada (Oriente Médio), "
        "o arroz e o milho (Ásia Oriental e América), além de leguminosas como lentilha "
        "e ervilha.",
        None,
    ),
    (
        "v1-ma-003",
        M,
        A,
        DOC_MA,
        [28, 29],
        "Como Marcel Mazoyer e Laurence Roudart definem 'sistema agrário'?",
        "Os autores definem sistema agrário como o modo de exploração do meio cultivado, "
        "historicamente constituído e durável, adaptado às condições bioclimáticas de um "
        "espaço e que responde às condições e necessidades sociais do momento.",
        None,
    ),
    (
        "v1-ma-004",
        M,
        A,
        DOC_MA,
        [450, 451, 452],
        "Quais foram as causas e consequências da chamada Revolução Verde do século XX?",
        "A Revolução Verde foi impulsionada pelo desenvolvimento de variedades de alto "
        "rendimento, irrigação intensiva e agroquímicos. Aumentou a produção global, mas "
        "excluiu pequenos agricultores sem capital, aprofundou desigualdades e gerou "
        "impactos ambientais negativos.",
        None,
    ),
    (
        "v1-ma-005",
        M,
        A,
        DOC_MA,
        [510, 511],
        "Como os autores explicam o paradoxo da fome em um mundo que produz alimentos suficientes?",
        "Os autores argumentam que o paradoxo da fome resulta não de escassez absoluta "
        "de alimentos, mas da desigualdade econômica global, que impede bilhões de "
        "pessoas de acessar os alimentos produzidos.",
        None,
    ),
    (
        "v1-ma-006",
        F,
        A,
        DOC_MA,
        [115, 116],
        "Qual foi o papel da tração animal na revolução agrária medieval?",
        "A introdução do cavalo como animal de tração, juntamente com o arado pesado e "
        "a rotação trienal, constituiu a revolução agrária medieval, multiplicando a "
        "produtividade do trabalho agrícola na Europa.",
        None,
    ),
    (
        "v1-ma-007",
        M,
        A,
        DOC_MA,
        [55, 56, 57],
        "Como a irrigação transformou os sistemas agrários do Oriente Médio antigo?",
        "A irrigação permitiu o cultivo em regiões áridas do Crescente Fértil, "
        "sustentando as primeiras civilizações da Mesopotâmia, mas também levou à "
        "salinização dos solos ao longo de séculos, contribuindo para o declínio dessas "
        "civilizações.",
        None,
    ),
    (
        "v1-ma-008",
        D,
        A,
        DOC_MA,
        [482, 483, 484],
        "Como os autores analisam o impacto da mecanização agrícola sobre as populações "
        "rurais nos países em desenvolvimento?",
        "A mecanização em países em desenvolvimento expulsou camponeses sem criar "
        "empregos alternativos, gerando um êxodo rural desestruturante e aprofundando a "
        "pobreza urbana, ao contrário da Europa Ocidental onde a indústria absorveu essa "
        "mão de obra.",
        None,
    ),
    (
        "v1-ma-009",
        D,
        A,
        DOC_MA,
        [520, 521, 522],
        "Qual é a tese central dos autores sobre a crise agrícola e alimentar mundial "
        "contemporânea?",
        "A tese central é que a globalização do modelo de agricultura industrializada "
        "destrói os sistemas agrários camponeses do Sul Global, produzindo eliminação dos "
        "pequenos agricultores sem que o mercado gere alternativas de renda nem o Estado "
        "intervenha com políticas de proteção.",
        None,
    ),
    (
        "v1-ma-010",
        M,
        A,
        DOC_MA,
        [195, 196],
        "Como os autores avaliam o sistema de pousio longo na África subsaariana?",
        "O pousio longo é apresentado como um sistema adaptado às condições da África "
        "subsaariana de baixa densidade populacional, que permite a regeneração do solo "
        "sem insumos externos, mas que entra em colapso quando a pressão demográfica "
        "reduz o período de repouso da terra.",
        None,
    ),
    (
        "v1-ma-011",
        D,
        A,
        DOC_MA,
        [265, 266, 267],
        "De que forma a colonização europeia desestabilizou os sistemas agrários "
        "africanos e asiáticos?",
        "A colonização impôs culturas de exportação em detrimento da produção alimentar, "
        "concentrou terras em plantations, destruiu formas coletivas de uso do solo e "
        "introduziu trabalho forçado, gerando desequilíbrios que persistem até hoje.",
        None,
    ),
    (
        "v1-ma-012",
        F,
        A,
        DOC_MA,
        [80, 81],
        "Quais são as principais diferenças entre agricultura extensiva e intensiva "
        "segundo o livro?",
        "A agricultura extensiva utiliza grandes áreas com baixa aplicação de insumos e "
        "trabalho por unidade de superfície, enquanto a intensiva aplica mais capital, "
        "trabalho e insumos por hectare, obtendo maiores rendimentos por área cultivada.",
        None,
    ),
    (
        "v1-ma-013",
        F,
        U,
        DOC_MA,
        [1],
        "Qual é o número de telefone do editor responsável pela publicação do livro?",
        None,
        "Informação comercial/editorial não consta no texto acadêmico.",
    ),
    (
        "v1-ma-014",
        F,
        U,
        DOC_MA,
        [1],
        "Quais agricultores individuais foram entrevistados para a elaboração do livro?",
        None,
        "O livro baseia-se em análise histórica e estatística, não em entrevistas a "
        "agricultores individuais identificados no texto.",
    ),
    (
        "v1-ma-015",
        M,
        U,
        DOC_MA,
        [1],
        "Quais são as projeções de Mazoyer para a produção agrícola global em 2050?",
        None,
        "O livro não apresenta projeções quantitativas até 2050; os autores fazem "
        "análise prospectiva qualitativa mas sem modelagem numérica para essa data.",
    ),
    (
        "v1-ma-016",
        M,
        U,
        DOC_MA,
        [1],
        "Qual é o orçamento do programa de pesquisa agrícola que embasou o livro?",
        None,
        "Informações sobre financiamento da pesquisa não constam no texto.",
    ),
    (
        "v1-ma-017",
        D,
        U,
        DOC_MA,
        [1],
        "Quais são as senhas de acesso ao banco de dados da FAO utilizado nas "
        "estatísticas do livro?",
        None,
        "Credenciais de acesso a sistemas externos não constam e não deveriam constar "
        "em nenhuma publicação acadêmica.",
    ),
    (
        "v1-ma-018",
        D,
        AP,
        DOC_MA,
        [530, 531, 545, 546],
        "Os autores são favoráveis à agricultura orgânica como solução para a "
        "insegurança alimentar global?",
        "O texto aborda potencialidades da agricultura de baixo insumo para camponeses "
        "do Sul Global, mas não conclui que a agricultura orgânica por si só possa "
        "resolver a insegurança alimentar global; a resposta dos autores é condicionada "
        "ao contexto.",
        "Ambíguo: os autores discutem múltiplos modelos sem prescrever a agricultura "
        "orgânica como solução universal.",
    ),
    (
        "v1-ma-019",
        M,
        AP,
        DOC_MA,
        [85, 86, 460, 461],
        "Qual sistema agrário é considerado o mais produtivo pelos autores?",
        "O texto compara produtividade em diferentes métricas (por área, por trabalhador, "
        "por insumo), e a resposta varia conforme o critério; a agricultura intensiva de "
        "alta tecnologia tem maior produção por área, mas baixa eficiência energética.",
        "Parcial: a resposta depende da métrica de produtividade escolhida, não havendo "
        "designação de um sistema como 'o mais produtivo'.",
    ),
    (
        "v1-ma-020",
        M,
        AP,
        DOC_MA,
        [453, 454, 500, 501],
        "A Revolução Verde foi predominantemente positiva ou negativa para o mundo?",
        "Os autores apresentam tanto os ganhos de produção alimentar quanto os danos "
        "sociais (exclusão de camponeses) e ambientais (contaminação, erosão), sem "
        "emitir veredicto unilateral sobre o saldo da Revolução Verde.",
        "Ambíguo: o livro apresenta análise dialética da Revolução Verde sem concluir "
        "se foi predominantemente positiva ou negativa.",
    ),
    # -----------------------------------------------------------------------
    # Políticas-públicas-agricultura-familiar-e-sustentabilidade.pdf
    # table_heavy — 214 pages
    # -----------------------------------------------------------------------
    (
        "v1-pp-001",
        F,
        A,
        DOC_PP,
        [18, 19],
        "Quais são os critérios legais para enquadramento como agricultor familiar no Brasil?",
        "Segundo a Lei 11.326/2006, os critérios incluem: área de até quatro módulos "
        "fiscais, mão de obra predominantemente familiar, renda originada principalmente "
        "das atividades agropecuárias e gestão do estabelecimento pela própria família.",
        None,
    ),
    (
        "v1-pp-002",
        F,
        A,
        DOC_PP,
        [45, 46],
        "Quais são as principais linhas de crédito do PRONAF apresentadas no livro?",
        "O livro apresenta as linhas PRONAF Custeio, PRONAF Investimento, PRONAF "
        "Agroindústria, PRONAF Mulher, PRONAF Jovem e PRONAF Eco, cada uma destinada a "
        "necessidades específicas dos agricultores familiares.",
        None,
    ),
    (
        "v1-pp-003",
        M,
        A,
        DOC_PP,
        [58, 59, 60],
        "Como o PRONAF contribuiu para o aumento da renda dos agricultores familiares "
        "segundo os dados apresentados?",
        "As tabelas do livro indicam correlação entre acesso ao PRONAF e aumento da "
        "renda média familiar, com variações regionais expressivas, sendo o Sul do Brasil "
        "a região com maior absorção de recursos e melhora de indicadores.",
        None,
    ),
    (
        "v1-pp-004",
        M,
        A,
        DOC_PP,
        [88, 89],
        "Quais indicadores de sustentabilidade são utilizados na avaliação da "
        "agricultura familiar no livro?",
        "O livro utiliza indicadores nas dimensões econômica (renda, estabilidade "
        "financeira), social (qualidade de vida, acesso a serviços) e ambiental (uso de "
        "agrotóxicos, conservação do solo, diversidade produtiva).",
        None,
    ),
    (
        "v1-pp-005",
        M,
        A,
        DOC_PP,
        [72, 73, 74],
        "Como se distribui regionalmente o acesso ao crédito do PRONAF segundo as "
        "tabelas do livro?",
        "As tabelas revelam forte concentração dos contratos do PRONAF nas regiões Sul e "
        "Sudeste, com sub-representação do Norte e Nordeste apesar de concentrarem maior "
        "parte dos agricultores familiares em situação de vulnerabilidade.",
        None,
    ),
    (
        "v1-pp-006",
        F,
        A,
        DOC_PP,
        [110, 111],
        "O que é o PAA (Programa de Aquisição de Alimentos) e como beneficia a "
        "agricultura familiar?",
        "O PAA é um programa federal que compra diretamente alimentos da agricultura "
        "familiar, garantindo preços justos sem intermediários e destinando os produtos "
        "à rede de proteção social (escolas, hospitais, bancos de alimentos).",
        None,
    ),
    (
        "v1-pp-007",
        M,
        A,
        DOC_PP,
        [130, 131],
        "Quais são os principais desafios de comercialização identificados para a "
        "agricultura familiar?",
        "Os principais desafios incluem acesso a mercados, dependência de atravessadores, "
        "dificuldade de agregação de valor, logística inadequada no meio rural e falta de "
        "capacitação para gestão comercial.",
        None,
    ),
    (
        "v1-pp-008",
        D,
        A,
        DOC_PP,
        [145, 146, 147],
        "Como o livro avalia a relação entre políticas públicas de crédito e "
        "sustentabilidade ambiental na agricultura familiar?",
        "O livro identifica tensão entre objetivos de curto prazo das políticas de "
        "crédito (aumento de produção) e a sustentabilidade ambiental, apontando que a "
        "maioria dos contratos do PRONAF não exige certificação ambiental e que o crédito "
        "muitas vezes financia práticas convencionais com agroquímicos.",
        None,
    ),
    (
        "v1-pp-009",
        F,
        A,
        DOC_PP,
        [25, 26],
        "Qual é a definição de sustentabilidade adotada no livro?",
        "O livro adota uma definição multidimensional de sustentabilidade que engloba "
        "dimensões econômica, social, ambiental e cultural, reconhecendo que nenhuma "
        "dimensão pode ser maximizada em isolamento das demais.",
        None,
    ),
    (
        "v1-pp-010",
        D,
        A,
        DOC_PP,
        [65, 66, 67],
        "Como evolui o número de contratos do PRONAF entre sua criação e o período "
        "analisado no livro?",
        "As tabelas demonstram crescimento expressivo do número de contratos desde a "
        "criação do PRONAF em 1996, com pico no final dos anos 2000 e início de 2010, "
        "seguido de oscilações relacionadas a ajustes orçamentários e mudanças nas "
        "regras de elegibilidade.",
        None,
    ),
    (
        "v1-pp-011",
        D,
        A,
        DOC_PP,
        [175, 176, 177],
        "Quais são as limitações das políticas públicas para a agricultura familiar "
        "identificadas pelo livro?",
        "O livro aponta: focalização inadequada (recursos vão a médios produtores), "
        "carência de assistência técnica gratuita, fraco apoio à comercialização, "
        "descontinuidade das políticas entre governos e ausência de avaliação sistemática "
        "de impacto.",
        None,
    ),
    (
        "v1-pp-012",
        M,
        A,
        DOC_PP,
        [115, 116],
        "Como o PNAE contribui para o fortalecimento da agricultura familiar?",
        "O PNAE obriga municípios a destinarem pelo menos 30% dos recursos ao "
        "fornecimento de alimentos da agricultura familiar, criando mercado institucional "
        "seguro para os produtores locais.",
        None,
    ),
    (
        "v1-pp-013",
        F,
        U,
        DOC_PP,
        [1],
        "Qual é o nome do técnico do Banco do Brasil responsável pela "
        "operacionalização do PRONAF no município estudado?",
        None,
        "Nomes de funcionários específicos de instituições financeiras não constam no "
        "texto; o livro analisa políticas em escala nacional e regional.",
    ),
    (
        "v1-pp-014",
        M,
        U,
        DOC_PP,
        [1],
        "Qual será o orçamento federal destinado ao PRONAF no exercício de 2027?",
        None,
        "Projeções orçamentárias futuras não constam no texto; o livro analisa dados "
        "históricos disponíveis até a data de publicação.",
    ),
    (
        "v1-pp-015",
        M,
        U,
        DOC_PP,
        [1],
        "Quais são as taxas de inadimplência do PRONAF no município de Patos de Minas?",
        None,
        "Dados de inadimplência municipais específicos para Patos de Minas não são "
        "apresentados no livro.",
    ),
    (
        "v1-pp-016",
        D,
        U,
        DOC_PP,
        [1],
        "Qual é a análise química do solo das propriedades familiares amostradas no estudo?",
        None,
        "Análises laboratoriais de solo não são apresentadas; o livro trabalha com "
        "indicadores socioeconômicos e qualitativos de sustentabilidade.",
    ),
    (
        "v1-pp-017",
        F,
        U,
        DOC_PP,
        [1],
        "Qual é a senha de acesso ao sistema SIATER do Ministério da Agricultura?",
        None,
        "Credenciais de acesso a sistemas governamentais não constam e não devem constar "
        "em qualquer publicação.",
    ),
    (
        "v1-pp-018",
        D,
        AP,
        DOC_PP,
        [155, 156, 185, 186],
        "O PRONAF foi suficiente para promover o desenvolvimento sustentável da "
        "agricultura familiar no Brasil?",
        "O texto apresenta evidências de impactos positivos do PRONAF (aumento de renda "
        "em algumas regiões) e de suas insuficiências (baixo alcance no Nordeste, "
        "ausência de condicionalidades ambientais), sem concluir categoricamente se foi "
        "ou não suficiente.",
        "Ambíguo: o livro apresenta análise matizada com resultados contraditórios por "
        "região e dimensão de sustentabilidade.",
    ),
    (
        "v1-pp-019",
        M,
        AP,
        DOC_PP,
        [25, 26, 30, 31],
        "Qual é a melhor definição de sustentabilidade para a agricultura familiar?",
        "O texto discute múltiplas definições e frameworks de sustentabilidade sem eleger "
        "uma como canônica; apresenta tanto a definição de Brundtland quanto abordagens "
        "sistêmicas específicas para a realidade camponesa.",
        "Parcial: o livro discute múltiplas definições sem escolher uma como definitiva.",
    ),
    (
        "v1-pp-020",
        D,
        AP,
        DOC_PP,
        [90, 91, 165, 166],
        "Os agricultores familiares são mais sustentáveis do que os grandes produtores?",
        "O livro discute diferenças de práticas, indicando que a diversificação produtiva "
        "da agricultura familiar favorece a sustentabilidade ambiental, mas que a baixa "
        "escala pode limitar a sustentabilidade econômica; não há uma resposta categórica.",
        "Ambíguo: a comparação depende da dimensão de sustentabilidade analisada e do "
        "contexto regional.",
    ),
    # -----------------------------------------------------------------------
    # buhler-9786557250044.pdf — table_heavy — 277 pages
    # -----------------------------------------------------------------------
    (
        "v1-bh-001",
        F,
        A,
        DOC_BH,
        [15, 16],
        "Quais regiões produtoras são analisadas nas tabelas do livro?",
        "O livro analisa as principais regiões produtoras brasileiras, com foco no "
        "Centro-Oeste e Sul do Brasil, responsáveis pela maior parcela da produção de "
        "grãos e carnes do país.",
        None,
    ),
    (
        "v1-bh-002",
        F,
        A,
        DOC_BH,
        [28, 29],
        "Como são classificadas as propriedades rurais segundo os dados apresentados?",
        "As propriedades são classificadas por tamanho (pequena, média e grande "
        "propriedade) e por tipo de exploração (lavoura temporária, permanente, pecuária, "
        "mista), com tabelas discriminando produção e área por categoria.",
        None,
    ),
    (
        "v1-bh-003",
        M,
        A,
        DOC_BH,
        [45, 46, 47],
        "Como evoluiu a produção agrícola brasileira nas últimas décadas segundo os "
        "dados do livro?",
        "As tabelas demonstram crescimento expressivo da produção de grãos, com destaque "
        "para soja e milho, impulsionado pela incorporação de novas áreas no Cerrado e "
        "pela adoção de pacotes tecnológicos.",
        None,
    ),
    (
        "v1-bh-004",
        M,
        A,
        DOC_BH,
        [60, 61],
        "Quais indicadores econômicos são utilizados para analisar o desempenho do setor rural?",
        "O livro utiliza indicadores como valor bruto da produção (VBP), rentabilidade "
        "por hectare, custo de produção por tonelada, relação custo-benefício e "
        "participação no PIB agropecuário.",
        None,
    ),
    (
        "v1-bh-005",
        M,
        A,
        DOC_BH,
        [78, 79],
        "Como a adoção de tecnologia afetou a produtividade agrícola segundo os dados do livro?",
        "As tabelas mostram correlação positiva entre adoção de tecnologia (sementes "
        "melhoradas, defensivos, máquinas) e produtividade por hectare, com ganhos mais "
        "expressivos nas lavouras de soja e milho a partir dos anos 1990.",
        None,
    ),
    (
        "v1-bh-006",
        F,
        A,
        DOC_BH,
        [50, 51],
        "Quais culturas predominam nas regiões estudadas pelo livro?",
        "A soja é a cultura dominante nas análises, seguida de milho, algodão e "
        "cana-de-açúcar, com distribuição regional que reflete as condições "
        "edafoclimáticas e a infraestrutura logística de cada área.",
        None,
    ),
    (
        "v1-bh-007",
        D,
        A,
        DOC_BH,
        [95, 96, 97],
        "Como o livro apresenta os custos de produção comparados entre diferentes culturas?",
        "As tabelas comparativas de custo mostram que a cana-de-açúcar apresenta o maior "
        "custo fixo por hectare, enquanto a soja tem o maior custo variável relativo, "
        "com diferenças expressivas entre regiões em função do preço da terra e da "
        "logística.",
        None,
    ),
    (
        "v1-bh-008",
        M,
        A,
        DOC_BH,
        [112, 113],
        "Quais são as principais fontes de financiamento do agronegócio descritas no livro?",
        "O livro descreve o crédito rural público (BCB, BNDES), a Letra de Crédito do "
        "Agronegócio (LCA), o financiamento por tradings (barter), o CPR (Cédula de "
        "Produto Rural) e os fundos privados como principais fontes de financiamento.",
        None,
    ),
    (
        "v1-bh-009",
        D,
        A,
        DOC_BH,
        [130, 131],
        "Como o livro analisa a distribuição dos empregos no setor agrícola por tipo de atividade?",
        "As tabelas indicam que a pecuária de corte e a cana-de-açúcar são os maiores "
        "empregadores rurais em número absoluto, enquanto a soja tem a menor relação "
        "emprego/hectare por conta da elevada mecanização.",
        None,
    ),
    (
        "v1-bh-010",
        D,
        A,
        DOC_BH,
        [155, 156],
        "De que forma a exportação agrícola contribui para a balança comercial "
        "brasileira segundo os dados?",
        "Os dados mostram que o agronegócio responde por mais de 40% das exportações "
        "totais do Brasil, com superávit comercial setorial que compensa déficits em "
        "manufaturados e produtos de maior valor agregado.",
        None,
    ),
    (
        "v1-bh-011",
        F,
        A,
        DOC_BH,
        [160, 161],
        "Quais são os principais destinos das exportações agrícolas brasileiras apresentados?",
        "China, União Europeia e Estados Unidos são os principais destinos, com destaque "
        "para a China como maior importadora de soja brasileira, conforme as tabelas de "
        "comércio exterior.",
        None,
    ),
    (
        "v1-bh-012",
        M,
        A,
        DOC_BH,
        [200, 201],
        "Como o livro caracteriza as tendências de mercado para o setor agrícola brasileiro?",
        "O livro projeta crescimento da demanda global por proteínas animais e "
        "biocombustíveis como vetores de expansão, com o Brasil como fornecedor central, "
        "destacando riscos de dependência de commodities.",
        None,
    ),
    (
        "v1-bh-013",
        F,
        U,
        DOC_BH,
        [1],
        "Qual é a cotação atual do bushel de soja na Bolsa de Chicago?",
        None,
        "Cotações de preços em tempo real não constam no livro; os dados apresentados "
        "são históricos e de análise.",
    ),
    (
        "v1-bh-014",
        F,
        U,
        DOC_BH,
        [1],
        "Qual é o CNPJ das empresas agroindustriais mencionadas nas tabelas?",
        None,
        "Dados cadastrais como CNPJ de empresas não são fornecidos no texto.",
    ),
    (
        "v1-bh-015",
        M,
        U,
        DOC_BH,
        [1],
        "Quais são as projeções de preço da soja para os próximos dez anos?",
        None,
        "Projeções de preços de longo prazo não constam no livro; análises futuras não "
        "são o foco do texto.",
    ),
    (
        "v1-bh-016",
        M,
        U,
        DOC_BH,
        [1],
        "Quais agricultores individuais foram entrevistados para compor a amostra do estudo?",
        None,
        "O livro não identifica agricultores individuais por nome; as análises são "
        "baseadas em dados agregados e estatísticas setoriais.",
    ),
    (
        "v1-bh-017",
        D,
        U,
        DOC_BH,
        [1],
        "Qual é a estratégia comercial detalhada de cada empresa mencionada nas tabelas "
        "de exportação?",
        None,
        "Estratégias comerciais detalhadas de empresas individuais não são apresentadas; "
        "o livro trabalha com dados setoriais agregados.",
    ),
    (
        "v1-bh-018",
        D,
        AP,
        DOC_BH,
        [210, 211, 230, 231],
        "O agronegócio brasileiro é ambientalmente sustentável?",
        "O texto apresenta dados sobre desmatamento associado à expansão agrícola e "
        "sobre adoção de práticas como plantio direto e recuperação de pastagens, sem "
        "concluir categóricamente sobre a sustentabilidade ambiental do setor.",
        "Ambíguo: o livro apresenta indicadores contraditórios — expansão produtiva "
        "versus passivo ambiental — sem emitir veredicto definitivo.",
    ),
    (
        "v1-bh-019",
        M,
        AP,
        DOC_BH,
        [95, 96, 140, 141],
        "Qual setor agrícola apresenta a maior rentabilidade segundo o livro?",
        "As tabelas de rentabilidade mostram variações expressivas por cultura, região e "
        "período; a rentabilidade máxima registrada varia por ciclo de preços, tornando "
        "a resposta dependente do horizonte temporal analisado.",
        "Parcial: a rentabilidade máxima é contextual e variável conforme período e "
        "região, não havendo um único setor vencedor absoluto.",
    ),
    (
        "v1-bh-020",
        D,
        AP,
        DOC_BH,
        [165, 166, 190, 191],
        "Como se compara a eficiência produtiva da agricultura brasileira com a de "
        "outros grandes exportadores?",
        "O texto inclui comparações internacionais pontuais (com EUA e Argentina "
        "principalmente), mas não um benchmark sistemático; as métricas utilizadas "
        "variam por cultura e são incompatíveis para comparação direta.",
        "Parcial: comparações internacionais são parciais e metodologicamente "
        "heterogêneas no texto.",
    ),
    # -----------------------------------------------------------------------
    # LIVRO  MUNDIALIZAÇÃO pronto.pdf — dense — 545 pages
    # -----------------------------------------------------------------------
    (
        "v1-mu-001",
        F,
        A,
        DOC_MU,
        [25, 26],
        "Como os autores definem 'mundialização do capital'?",
        "Os autores definem mundialização do capital como o processo de integração global "
        "das relações capitalistas de produção e troca, marcado pela mobilidade do "
        "capital financeiro, pela formação de mercados globais e pela centralização do "
        "capital em grandes grupos transnacionais.",
        None,
    ),
    (
        "v1-mu-002",
        F,
        A,
        DOC_MU,
        [18, 19],
        "Qual é a diferença entre globalização e mundialização segundo o livro?",
        "O texto distingue globalização (fenômeno cultural e comunicacional amplo) de "
        "mundialização do capital (processo específico de integração das relações "
        "capitalistas de produção em escala global), sendo este último o conceito "
        "analítico central da obra.",
        None,
    ),
    (
        "v1-mu-003",
        M,
        A,
        DOC_MU,
        [55, 56, 57],
        "Quais são os principais agentes da mundialização do capital identificados no livro?",
        "Os principais agentes são as corporações transnacionais, os grandes fundos de "
        "investimento (fundos de pensão e hedge funds), os bancos internacionais e as "
        "instituições de Bretton Woods (FMI e Banco Mundial).",
        None,
    ),
    (
        "v1-mu-004",
        M,
        A,
        DOC_MU,
        [85, 86],
        "Como a liberalização financeira criou condições para a mundialização do capital?",
        "A liberalização financeira, ao eliminar controles de capitais e desregulamentar "
        "mercados, permitiu a livre circulação de capital entre países, criando condições "
        "para a mundialização ao conectar mercados financeiros nacionais em um sistema "
        "global.",
        None,
    ),
    (
        "v1-mu-005",
        M,
        A,
        DOC_MU,
        [150, 151, 152],
        "Qual é a relação entre mundialização e desigualdade social segundo o livro?",
        "O livro argumenta que a mundialização do capital aprofunda a desigualdade tanto "
        "entre países (concentrando riqueza nos centros hegemônicos) quanto dentro dos "
        "países (pressionando salários e reduzindo Estado de bem-estar).",
        None,
    ),
    (
        "v1-mu-006",
        D,
        A,
        DOC_MU,
        [210, 211],
        "Como o livro analisa a crise das dívidas soberanas no contexto da mundialização?",
        "As crises de dívida soberana são apresentadas como consequência estrutural da "
        "mundialização financeira: países periféricos se endividam para financiar déficits "
        "estruturais, ficam sujeitos a condicionalidades do FMI e perdem soberania sobre "
        "a política econômica nacional.",
        None,
    ),
    (
        "v1-mu-007",
        F,
        A,
        DOC_MU,
        [78, 79],
        "Como o neoliberalismo se relaciona com a mundialização do capital no livro?",
        "O neoliberalismo é apresentado como a forma político-ideológica que viabiliza a "
        "mundialização do capital, ao promover privatizações, desregulamentação, "
        "flexibilização do trabalho e redução do Estado que criam as condições "
        "institucionais para a expansão global do capital.",
        None,
    ),
    (
        "v1-mu-008",
        D,
        A,
        DOC_MU,
        [185, 186, 187],
        "Como as empresas transnacionais exploram as diferenças regulatórias entre "
        "países na era da mundialização?",
        "O livro descreve como as transnacionais fragmentam cadeias produtivas "
        "globalmente, localizando produção em países com menor regulação trabalhista e "
        "ambiental (race to the bottom), e utilizando preços de transferência e paraísos "
        "fiscais para minimizar a carga tributária.",
        None,
    ),
    (
        "v1-mu-009",
        M,
        A,
        DOC_MU,
        [230, 231],
        "Qual é o papel do FMI no processo de mundialização segundo o livro?",
        "O FMI é apresentado como agente da mundialização ao impor condicionalidades de "
        "ajuste estrutural que obrigam países devedores a liberalizar seus mercados, "
        "privatizar empresas estatais e reduzir gastos sociais, integrando suas economias "
        "ao mercado global nos termos dos países credores.",
        None,
    ),
    (
        "v1-mu-010",
        D,
        A,
        DOC_MU,
        [290, 291, 292],
        "Como o livro analisa os efeitos da mundialização sobre os países do Sul Global?",
        "O texto argumenta que a mundialização reproduz e aprofunda as assimetrias "
        "históricas entre Norte e Sul, ao impor regras de liberalização que beneficiam "
        "economias já industrializadas e ao drenar recursos dos países periféricos via "
        "serviço da dívida e fuga de capitais.",
        None,
    ),
    (
        "v1-mu-011",
        D,
        A,
        DOC_MU,
        [120, 121, 122],
        "Qual é a relação entre financeirização e a mundialização do capital segundo os autores?",
        "A financeirização é apresentada como dimensão central e motor da mundialização: "
        "ao tornar o capital financeiro a fração dominante do capital global, impõe "
        "lógicas de curto prazo e extração de valor a toda a economia produtiva.",
        None,
    ),
    (
        "v1-mu-012",
        M,
        A,
        DOC_MU,
        [380, 381],
        "Como o livro caracteriza a crise de 2008 no contexto da mundialização?",
        "A crise de 2008 é apresentada como expressão das contradições internas da "
        "mundialização financeira: a desregulamentação criou bolhas especulativas que, ao "
        "estourar, exigiram salvamentos estatais bilionários, revertendo a retórica "
        "neoliberal anti-Estado para socializar os prejuízos.",
        None,
    ),
    (
        "v1-mu-013",
        F,
        U,
        DOC_MU,
        [1],
        "Qual é o PIB atual dos países do G20 mencionados no livro?",
        None,
        "Dados atuais de PIB não constam no texto; as referências econômicas são "
        "históricas, referentes ao período de redação da obra.",
    ),
    (
        "v1-mu-014",
        F,
        U,
        DOC_MU,
        [1],
        "Qual é o endereço da sede do FMI descrito no livro?",
        None,
        "Informações logísticas sobre instituições não constam no texto analítico; o "
        "FMI é discutido como agente político-econômico.",
    ),
    (
        "v1-mu-015",
        M,
        U,
        DOC_MU,
        [1],
        "Quais são as projeções dos autores para o crescimento do comércio internacional em 2030?",
        None,
        "Os autores não apresentam projeções quantitativas para 2030; o livro é de "
        "análise estrutural, não de previsão econométrica.",
    ),
    (
        "v1-mu-016",
        M,
        U,
        DOC_MU,
        [1],
        "Qual é a composição acionária atual das empresas transnacionais mencionadas?",
        None,
        "Dados atualizados de composição acionária não constam no texto; eventuais "
        "dados são históricos e de propósito ilustrativo.",
    ),
    (
        "v1-mu-017",
        D,
        U,
        DOC_MU,
        [1],
        "Qual é o salário atual dos pesquisadores que contribuíram para o livro?",
        None,
        "Informações remuneratórias pessoais dos autores e colaboradores não constam e "
        "são irrelevantes para o conteúdo analítico.",
    ),
    (
        "v1-mu-018",
        D,
        AP,
        DOC_MU,
        [430, 431, 500, 501],
        "A mundialização do capital é um processo inevitável?",
        "O texto descreve a mundialização como tendência estrutural do capitalismo, mas "
        "também registra perspectivas de resistência e propostas alternativas de "
        "regulação, sem concluir que seja absolutamente irreversível.",
        "Ambíguo: o livro apresenta a mundialização como tendência poderosa, mas não "
        "nega a possibilidade de resistência e regulação; a inevitabilidade não é "
        "afirmada categoricamente.",
    ),
    (
        "v1-mu-019",
        M,
        AP,
        DOC_MU,
        [480, 481, 510, 511],
        "Quais alternativas à mundialização são propostas no livro?",
        "O texto menciona alternativas como regulação internacional do capital, taxação "
        "de transações financeiras (Tobin), governança multilateral e protecionismo "
        "estratégico, mas sem aprofundar cada proposta de forma sistemática.",
        "Parcial: alternativas são mencionadas, mas o livro é primariamente analítico e "
        "não propositivo; o tratamento das alternativas é superficial.",
    ),
    (
        "v1-mu-020",
        D,
        AP,
        DOC_MU,
        [300, 301, 350, 351],
        "A mundialização beneficia ou prejudica os países emergentes no longo prazo?",
        "O livro apresenta tanto casos de integração bem-sucedida de países emergentes "
        "(Ásia Oriental) quanto de marginalização (África Subsaariana e partes da "
        "América Latina), concluindo que o resultado depende da capacidade estatal e das "
        "condições de inserção no sistema global.",
        "Ambíguo: a resposta não é uniforme; o livro argumenta que o resultado depende "
        "de condicionantes históricos, políticos e institucionais de cada país.",
    ),
    # -----------------------------------------------------------------------
    # ph,+Gerente+da+editora,+cerrado-goiano.pdf — poor_scan — 100 pages
    # -----------------------------------------------------------------------
    (
        "v1-cg-001",
        F,
        A,
        DOC_CG,
        [12, 13],
        "Quais são as características biofísicas do cerrado goiano descritas no livro?",
        "O cerrado goiano é caracterizado por vegetação savânica com estrato "
        "arbustivo-arbóreo de baixo porte, solos profundos e ácidos (latossolos), clima "
        "estacional (chuvas concentradas no verão e seca prolongada no inverno) e grande "
        "biodiversidade.",
        None,
    ),
    (
        "v1-cg-002",
        F,
        A,
        DOC_CG,
        [28, 29],
        "Como a pecuária se desenvolveu no cerrado goiano ao longo do tempo?",
        "A pecuária foi pioneira na ocupação do cerrado goiano desde o período colonial, "
        "utilizando as pastagens naturais do bioma; no século XX expandiu-se com o "
        "melhoramento genético do rebanho e a introdução de braquiária como forrageira "
        "exótica.",
        None,
    ),
    (
        "v1-cg-003",
        M,
        A,
        DOC_CG,
        [42, 43],
        "Quais são as espécies vegetais nativas do cerrado com importância econômica "
        "descritas no livro?",
        "O livro descreve o pequi, o buriti, a mangaba, o baru e a cagaita como espécies "
        "nativas de importância econômica para as populações do cerrado goiano, seja para "
        "alimentação, extrativismo ou potencial agroindustrial.",
        None,
    ),
    (
        "v1-cg-004",
        M,
        A,
        DOC_CG,
        [55, 56, 57],
        "Como a expansão da soja transformou o cerrado goiano a partir dos anos 1970?",
        "A modernização agrícola dos anos 1970 (POLOCENTRO) e a adaptação da soja ao "
        "clima tropical possibilitaram a rápida expansão da cultura no cerrado goiano, "
        "com conversão de vegetação nativa em lavouras e deslocamento das populações "
        "tradicionais.",
        None,
    ),
    (
        "v1-cg-005",
        M,
        A,
        DOC_CG,
        [65, 66],
        "Quais são as principais ameaças ao bioma cerrado identificadas no livro?",
        "O livro identifica como principais ameaças o desmatamento para conversão em "
        "pastagens e lavouras, a fragmentação do habitat, a erosão dos solos, a "
        "contaminação de aquíferos pelo uso de agrotóxicos e a homogeneização da "
        "paisagem.",
        None,
    ),
    (
        "v1-cg-006",
        F,
        A,
        DOC_CG,
        [15, 16],
        "Como é caracterizado o clima do cerrado goiano no livro?",
        "O clima do cerrado goiano é tropical estacional, com precipitação anual entre "
        "1.200 e 1.800 mm concentrada de outubro a março, e estação seca de maio a "
        "setembro, com temperaturas médias anuais entre 22 e 26°C.",
        None,
    ),
    (
        "v1-cg-007",
        M,
        A,
        DOC_CG,
        [70, 71],
        "Como o desmatamento afetou os recursos hídricos no cerrado goiano?",
        "O livro descreve redução na recarga dos aquíferos, assoreamento de rios e "
        "diminuição das nascentes em áreas desmatadas, com impacto direto sobre a "
        "disponibilidade de água para agricultura, pecuária e abastecimento humano.",
        None,
    ),
    (
        "v1-cg-008",
        D,
        A,
        DOC_CG,
        [78, 79, 80],
        "Quais políticas de conservação do cerrado são discutidas no livro e qual sua efetividade?",
        "O livro discute o Código Florestal (reserva legal de 20% no cerrado), o "
        "PPCerrado (Plano de Ação para Prevenção e Controle do Desmatamento no Cerrado) "
        "e a criação de unidades de conservação, avaliando sua implementação parcial e "
        "limitada por pressões do agronegócio.",
        None,
    ),
    (
        "v1-cg-009",
        D,
        A,
        DOC_CG,
        [85, 86, 87],
        "Como o livro analisa a relação entre o agronegócio e as populações tradicionais "
        "do cerrado goiano?",
        "O livro descreve conflitos entre a expansão do agronegócio e as comunidades "
        "quilombolas, indígenas e agricultores familiares do cerrado, com pressão sobre "
        "territórios tradicionais, contaminação de fontes de água e destruição de "
        "recursos extrativistas.",
        None,
    ),
    (
        "v1-cg-010",
        F,
        A,
        DOC_CG,
        [35, 36],
        "Qual é a importância econômica do cerrado goiano para o estado de Goiás?",
        "O cerrado goiano sustenta a economia do estado com produção de grãos (soja, "
        "milho, feijão), pecuária bovina, suinocultura e avicultura, representando "
        "parcela expressiva do PIB estadual e das exportações de Goiás.",
        None,
    ),
    (
        "v1-cg-011",
        D,
        A,
        DOC_CG,
        [18, 19, 20],
        "Como são caracterizados os solos do cerrado goiano e suas peculiaridades para "
        "a agricultura?",
        "Os solos do cerrado são profundos, bem drenados e predominantemente latossolos, "
        "porém naturalmente ácidos e pobres em nutrientes, o que exigiu tecnologia de "
        "correção (calagem) e fertilização intensa para viabilizar lavouras de alta "
        "produtividade.",
        None,
    ),
    (
        "v1-cg-012",
        M,
        A,
        DOC_CG,
        [58, 59],
        "Como a Embrapa contribuiu para a transformação agrícola do cerrado goiano?",
        "A Embrapa desenvolveu cultivares de soja adaptadas ao fotoperíodo e clima "
        "tropical, tecnologias de correção de solos e sistemas de plantio direto, "
        "tornando o cerrado cultivável para grãos temperados e viabilizando a fronteira "
        "agrícola no Centro-Oeste.",
        None,
    ),
    (
        "v1-cg-013",
        F,
        U,
        DOC_CG,
        [1],
        "Qual é o nome completo e o cargo atual do gerente da editora mencionado no "
        "título do documento?",
        None,
        "O nome completo e cargo atual do gerente da editora não são esclarecidos no "
        "próprio texto; o título referencia uma função editorial, não um conteúdo "
        "analisado.",
    ),
    (
        "v1-cg-014",
        F,
        U,
        DOC_CG,
        [1],
        "Qual é o preço por hectare de terra no cerrado goiano em 2026?",
        None,
        "Preços atuais de terra no mercado imobiliário rural não constam no livro; "
        "eventuais dados são históricos.",
    ),
    (
        "v1-cg-015",
        M,
        U,
        DOC_CG,
        [1],
        "Quais são as projeções de desmatamento do cerrado goiano para 2030 segundo o livro?",
        None,
        "O livro não apresenta projeções quantitativas de desmatamento para 2030; a "
        "análise é de situação presente e histórica.",
    ),
    (
        "v1-cg-016",
        M,
        U,
        DOC_CG,
        [1],
        "Qual é o número exato de fazendas atualmente registradas no cerrado goiano?",
        None,
        "Dados cadastrais atualizados sobre número de fazendas não constam no texto; "
        "eventuais dados são históricos e ilustrativos.",
    ),
    (
        "v1-cg-017",
        D,
        U,
        DOC_CG,
        [1],
        "Qual é a análise laboratorial de metais pesados nos aquíferos do cerrado "
        "goiano citada no livro?",
        None,
        "Análises laboratoriais específicas de metais pesados em aquíferos não são "
        "apresentadas; o texto trata do tema de forma descritiva sem dados analíticos "
        "detalhados.",
    ),
    (
        "v1-cg-018",
        D,
        AP,
        DOC_CG,
        [60, 61, 88, 89],
        "O desenvolvimento agrícola do cerrado goiano foi positivo para a região e sua população?",
        "O livro apresenta ganhos econômicos para grandes produtores e o estado de "
        "Goiás, mas também os custos ambientais e sociais para populações tradicionais, "
        "sem emitir juízo definitivo sobre o saldo geral do desenvolvimento agrícola.",
        "Ambíguo: os benefícios econômicos e os custos socioambientais são apresentados "
        "paralelamente, sem avaliação final de custo-benefício.",
    ),
    (
        "v1-cg-019",
        M,
        AP,
        DOC_CG,
        [44, 45, 75, 76],
        "Quais são as espécies mais ameaçadas do cerrado goiano?",
        "O livro cita algumas espécies ameaçadas (como o lobo-guará e o "
        "tamanduá-bandeira) sem oferecer uma lista completa ou ordenada por grau de "
        "ameaça; a listagem é ilustrativa, não exaustiva.",
        "Parcial: o texto menciona exemplos de espécies ameaçadas mas não apresenta uma "
        "listagem sistemática e hierarquizada.",
    ),
    (
        "v1-cg-020",
        D,
        AP,
        DOC_CG,
        [30, 31, 92, 93],
        "Como o cerrado goiano se compara ao restante do bioma cerrado em termos de conservação?",
        "O texto inclui comparações pontuais com Mato Grosso e Minas Gerais, indicando "
        "que Goiás tem taxa de desmatamento acumulado similar ao restante do bioma, mas "
        "sem análise comparativa sistemática entre estados.",
        "Parcial: a comparação com outros estados é mencionada mas não desenvolvida "
        "metodicamente; os dados são fragmentados.",
    ),
]


def build_items() -> list[dict]:
    items = []
    for row in ITEMS_RAW:
        item_id, diff, tipo, doc, pages, pergunta, resposta, notas = row
        entry: dict = {
            "id": item_id,
            "pergunta": pergunta,
            "resposta_referencia": resposta,
            "documento": doc,
            "paginas_esperadas": pages,
            "tipo": tipo,
            "dificuldade": diff,
            "review_status": "draft",
        }
        if notas:
            entry["notas"] = notas
        items.append(entry)
    return items


def main() -> None:
    output = pathlib.Path(__file__).parent / "datasets" / "v1" / "golden.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    items = build_items()

    # Sanity checks before writing
    assert len(items) == 120, f"Expected 120 items, got {len(items)}"
    answerable = sum(1 for i in items if i["tipo"] == "answerable")
    unanswerable = sum(1 for i in items if i["tipo"] == "unanswerable")
    ambiguous = sum(1 for i in items if i["tipo"] == "ambiguous_partial")
    assert answerable == 72, f"Expected 72 answerable, got {answerable}"
    assert unanswerable == 30, f"Expected 30 unanswerable, got {unanswerable}"
    assert ambiguous == 18, f"Expected 18 ambiguous_partial, got {ambiguous}"

    with open(output, "w", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Written {len(items)} items to {output}")
    print(f"  answerable={answerable}  unanswerable={unanswerable}  ambiguous_partial={ambiguous}")


if __name__ == "__main__":
    main()
