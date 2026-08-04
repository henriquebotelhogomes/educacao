"""
_build_golden.py — Regenerates evals/datasets/v1/golden.jsonl.

Run to (re)create the dataset:

    python evals/_build_golden.py

Every item carries ``review_status='draft'``.  Answerable and ambiguous items
carry one or more ``evidence_quotes`` copied verbatim from the exact
``paginas_esperadas``; unanswerable items carry no reference answer, no pages and
no evidence, with a ``notas`` rationale.  After editing, always run:

    python evals/validate.py check \\
        --dataset evals/datasets/v1/golden.jsonl \\
        --manifest evals/datasets/v1/manifest.json

which fails if any evidence quote is not present on its expected page.

Human curators must verify each item and only then advance ``review_status``.
Do NOT fabricate benchmark scores against draft items.
"""

from __future__ import annotations

import json
import pathlib
from typing import Optional

DOC_HA = "História Agrária.pdf"
DOC_MA = "historia-das-agriculturas-no-mundo-mazoyer-e-roudart.pdf"
DOC_PP = "Políticas-públicas-agricultura-familiar-e-sustentabilidade.pdf"
DOC_BH = "buhler-9786557250044.pdf"
DOC_MU = "LIVRO  MUNDIALIZAÇÃO pronto.pdf"
DOC_CG = "ph-gerente-editora-cerrado-goiano-poor-scan.pdf"


def item(
    item_id: str,
    tipo: str,
    dificuldade: str,
    documento: str,
    pergunta: str,
    resposta: Optional[str] = None,
    paginas: Optional[list[int]] = None,
    evidence: Optional[list[str]] = None,
    notas: Optional[str] = None,
) -> dict:
    return {
        "id": item_id,
        "pergunta": pergunta,
        "resposta_referencia": resposta,
        "documento": documento,
        "paginas_esperadas": paginas or [],
        "evidence_quotes": evidence or [],
        "tipo": tipo,
        "dificuldade": dificuldade,
        "review_status": "draft",
        "notas": notas,
    }


# ---------------------------------------------------------------------------
# História Agrária.pdf — narrative — 315 pages
# ---------------------------------------------------------------------------
HA_ITEMS: list[dict] = [
    item(
        "v1-ha-001",
        "answerable",
        "facil",
        DOC_HA,
        "Que transformação na produção agrícola da região de Nazaré é indicada "
        "pelos relatos das câmaras municipais no século XIX?",
        "Os relatos apontam a expansão da cultura do café em substituição à da "
        "mandioca, tendência que não se restringiu à Comarca de Nazaré.",
        [20],
        [
            "A ampliação da produção de café em detrimento de outras culturas não "
            "foi exclusividade da Comarca de Nazaré.",
            "a lavoura da mandioca está estacionaria, enquanto a do café progride",
        ],
    ),
    item(
        "v1-ha-002",
        "answerable",
        "medio",
        DOC_HA,
        "Que importância tinha a posse de pessoas escravizadas para a maioria "
        "pobre da Comarca de Nazaré após 1850?",
        "Para a grande maioria dos pobres, os escravizados eram o principal ou "
        "único bem de valor, e mantê-los era uma estratégia de sobrevivência.",
        [30],
        [
            "para a grande maioria dos pobres, a posse de escravizados era o "
            "principal ou único bem de valor que possuíam",
            "Manter essa posse era estratégia de sobrevivência.",
        ],
    ),
    item(
        "v1-ha-003",
        "answerable",
        "medio",
        DOC_HA,
        "Como o texto caracteriza as trajetórias de vida dos negros camponeses?",
        "Elas revelam uma condição humana singular e a dimensão política de que "
        "se revestem suas trajetórias ao longo do tempo.",
        [42],
        [
            "As vidas vividas por negros camponeses, através dos tempos, revelam a "
            "condição humana singular e a dimensão política de que se revestem suas "
            "trajetórias.",
        ],
    ),
    item(
        "v1-ha-004",
        "answerable",
        "facil",
        DOC_HA,
        "Qual é a situação das políticas públicas de saúde na comunidade quilombola de Barriguda?",
        "O texto aponta a inexistência de políticas públicas de saúde na "
        "comunidade quilombola de Barriguda.",
        [70],
        [
            "Na comunidade Quilombola de Barriguda é facilmente visível a "
            "inexistência de políticas públicas para a saúde.",
        ],
    ),
    item(
        "v1-ha-005",
        "answerable",
        "medio",
        DOC_HA,
        "Qual é, segundo os autores citados, um dos efeitos mais danosos da "
        "terceirização para os trabalhadores?",
        "A fragmentação da organização e da luta dos trabalhadores é apontada "
        "como um dos aspectos mais danosos da terceirização.",
        [120],
        [
            "um dos aspectos mais danosos impostos pela terceirização à "
            "organização e luta dos trabalhadores é a sua fragmentação",
        ],
    ),
    item(
        "v1-ha-006",
        "answerable",
        "dificil",
        DOC_HA,
        "Como analistas avaliam a origem do relacionamento nipo-brasileiro "
        "ligado ao complexo Albras-Alunorte?",
        "Muitos analistas indicam que o relacionamento se deu em grande parte por "
        "iniciativa do Japão, cabendo ao Brasil apenas uma função reativa.",
        [140],
        [
            "muitos analistas indicam que esse relacionamento se deu em grande "
            "parte por iniciativa do Japão, cabendo ao Brasil apenas uma função "
            "reativa",
        ],
    ),
    item(
        "v1-ha-007",
        "answerable",
        "medio",
        DOC_HA,
        "Como o trabalhador livre era visto no contexto do relatório de 1837?",
        "Era visto como fonte de progresso, superior ao trabalho escravo e como "
        "mecanismo eficaz na mestiçagem dos povos indígenas.",
        [160],
        [
            "O trabalhador livre era visto como fonte de progresso, superior ao "
            "trabalho escravo, e representava um mecanismo eficaz na mestiçagem dos "
            "povos indígenas.",
        ],
    ),
    item(
        "v1-ha-008",
        "answerable",
        "facil",
        DOC_HA,
        "Quais foram os focos das primeiras lutas das mulheres no Brasil, iniciadas no século XIX?",
        "Enfocaram o acesso ao voto feminino e o reconhecimento dos direitos civis das mulheres.",
        [180],
        [
            "as primeiras lutas das mulheres, iniciadas no século XIX, enfocaram o "
            "acesso ao voto feminino e o reconhecimento dos direitos civis das "
            "mulheres",
        ],
    ),
    item(
        "v1-ha-009",
        "answerable",
        "medio",
        DOC_HA,
        "Qual era o perfil das trabalhadoras domésticas no Brasil em 2011, "
        "segundo os dados apresentados?",
        "A maioria era negra (61,0%) e apenas 44,9% tinham carteira de trabalho assinada.",
        [200],
        [
            "A grande maioria dessas trabalhadoras eram negras (61,0%) e apenas "
            "44,9% do total dessas mulheres tinha carteira do trabalho assinada "
            "(DIEESE, 2013).",
        ],
    ),
    item(
        "v1-ha-010",
        "answerable",
        "dificil",
        DOC_HA,
        "Sob quais condições, segundo o texto, a intensificação agrícola tenderia "
        "a se acelerar em regiões de colonização?",
        "Somente à medida que a terra se tornasse escassa, de difícil acesso à "
        "propriedade ou ao seu usufruto.",
        [265],
        [
            "haveria poucos incentivos para a intensificação em regiões de "
            "colonização, a qual se aceleraria somente à medida que a terra se "
            "tornasse escassa, de difícil acesso à propriedade, ou de seu usufruto",
        ],
    ),
    item(
        "v1-ha-011",
        "answerable",
        "dificil",
        DOC_HA,
        "Qual é a meta das unidades domésticas rurais em relação ao trabalho, aos "
        "recursos e ao produto?",
        "Conseguir o ajuste mais favorável possível entre capacidade de trabalho, "
        "recursos materiais e produto gerado.",
        [285],
        [
            "sua meta é conseguir o ajuste mais favorável que lhes seja possível "
            "entre capacidade de trabalho, recursos materiais e produto gerado",
        ],
    ),
    item(
        "v1-ha-012",
        "answerable",
        "medio",
        DOC_HA,
        "O que os dados indicam sobre a população rural do Nordeste brasileiro entre 2000 e 2010?",
        "O Nordeste, que concentra quase metade da população rural do país, "
        "perdeu mais de 500 mil habitantes em áreas rurais no período.",
        [200],
        [
            "O Nordeste brasileiro, que concentra quase a metade da população "
            "rural do Brasil (14,3 milhões), perdeu mais de 500 mil habitantes em "
            "áreas rurais entre 2000 e 2010.",
        ],
    ),
    item(
        "v1-ha-013",
        "ambiguous_partial",
        "medio",
        DOC_HA,
        "As políticas de imigração europeia adotadas pelo Brasil no século XIX "
        "foram bem-sucedidas em substituir a mão de obra escrava?",
        "O texto observa apenas que as práticas de aquisição de europeus não "
        "haviam logrado êxito, sem oferecer uma avaliação conclusiva do resultado "
        "da política imigratória.",
        [160],
        [
            "era preciso observar as práticas aplicadas na aquisição dos europeus "
            "porque estas não haviam logrado êxitos",
        ],
        notas=(
            "Parcial: o trecho comenta a falta de êxito das práticas de aquisição "
            "de imigrantes europeus, mas não avalia o desfecho geral da política "
            "de imigração, o que impede uma resposta definitiva."
        ),
    ),
    item(
        "v1-ha-014",
        "ambiguous_partial",
        "dificil",
        DOC_HA,
        "A terceirização na Copener reduziu o número de trabalhadores diretos da empresa?",
        "O trecho registra que, em 2010, os trabalhadores diretos passaram de "
        "cerca de 100 para cerca de 600 em razão da primarização, o que responde "
        "apenas parcialmente ao efeito da terceirização sobre o emprego.",
        [120],
        [
            "Em 2010 a Copener passou de aproximadamente 100 para aproximadamente "
            "600 trabalhadores (BSC, 2010).",
        ],
        notas=(
            "Parcial: o dado citado refere-se a um aumento pontual ligado à "
            "'primarização' do plantio e da colheita, e não a uma medida geral do "
            "efeito da terceirização sobre o total de empregos."
        ),
    ),
    item(
        "v1-ha-015",
        "ambiguous_partial",
        "medio",
        DOC_HA,
        "O texto apresenta uma solução concreta e efetivada para os problemas de "
        "saúde das comunidades quilombolas?",
        "Não: registra que a requisição de um Posto de Saúde da Família é feita "
        "desde o fim da década de 1990 sem sucesso, indicando o problema mas não "
        "uma solução concretizada.",
        [70],
        [
            "a requisição do Posto de Saúde da Família (PSF) já está sendo feita "
            "desde o final da década de 1990, porém sem sucesso",
        ],
        notas=(
            "Parcial: o corpus descreve a demanda não atendida e o preconceito "
            "institucional, mas não apresenta uma solução efetivamente implementada."
        ),
    ),
    item(
        "v1-ha-016",
        "unanswerable",
        "facil",
        DOC_HA,
        "Qual é a taxa de juros do PRONAF para o custeio da safra 2025/2026?",
        notas=(
            "Não respondível: a coletânea é historiográfica, sobre conflitos e "
            "resistências no mundo rural, e não traz taxas de juros de programas de "
            "crédito atuais como o PRONAF."
        ),
    ),
    item(
        "v1-ha-017",
        "unanswerable",
        "medio",
        DOC_HA,
        "Quais são os requisitos legais para a certificação de produtos orgânicos "
        "no Brasil segundo a Lei 10.831/2003?",
        notas=(
            "Não respondível: o corpus não trata da legislação de certificação de "
            "produtos orgânicos nem de seus requisitos."
        ),
    ),
    item(
        "v1-ha-018",
        "unanswerable",
        "medio",
        DOC_HA,
        "Qual foi a produção de soja, em toneladas, do estado de Mato Grosso na safra 2020/2021?",
        notas=(
            "Não respondível: o livro não apresenta estatísticas de produção de "
            "soja por estado e safra."
        ),
    ),
    item(
        "v1-ha-019",
        "unanswerable",
        "facil",
        DOC_HA,
        "Como configurar um sistema de irrigação por gotejamento em uma horta comercial?",
        notas=(
            "Não respondível: trata-se de conteúdo técnico-agronômico de manejo, "
            "ausente desta obra de história agrária."
        ),
    ),
    item(
        "v1-ha-020",
        "unanswerable",
        "dificil",
        DOC_HA,
        "Quais políticas de reforma agrária foram implementadas pelo governo "
        "federal brasileiro em 2023?",
        notas=(
            "Não respondível: a obra não cobre o período nem descreve políticas "
            "federais de reforma agrária de 2023."
        ),
    ),
]

# ---------------------------------------------------------------------------
# historia-das-agriculturas-no-mundo — narrative — 569 pages
# ---------------------------------------------------------------------------
MA_ITEMS: list[dict] = [
    item(
        "v1-ma-001",
        "answerable",
        "medio",
        DOC_MA,
        "Qual é o rendimento típico das agriculturas que nunca acederam às "
        "revoluções agrícolas modernas?",
        "São rendimentos inferiores a 1.000 kg de equivalente-cereal por hectare "
        "— o milheto, por exemplo, rende no máximo cerca de 800 kg por hectare.",
        [30],
        [
            "Os rendimentos obtidos nessas condições são inferiores a 1.000 kg de "
            "equivalente-cereal por hectare (por exemplo, o rendimento médio do "
            "milheto no mundo atual é de, quando muito, 800 kg por hectare).",
        ],
    ),
    item(
        "v1-ma-002",
        "answerable",
        "medio",
        DOC_MA,
        "O que os autores designam pelo termo 'valência ecológica'?",
        "A faculdade de uma espécie de ocupar meios variados e também sua aptidão "
        "para povoá-los mais ou menos densamente.",
        [55],
        [
            "Ele designará não apenas a faculdade de uma espécie em ocupar meios "
            "variados, mas ainda sua aptidão em povoá-los mais ou menos densamente.",
        ],
    ),
    item(
        "v1-ma-003",
        "answerable",
        "dificil",
        DOC_MA,
        "Quando um ecossistema está em equilíbrio, segundo o texto?",
        "Quando a matéria orgânica produzida a cada ano pela fotossíntese iguala "
        "a destruída pela respiração e pela decomposição.",
        [80],
        [
            "Um ecossistema está em equilíbrio quando a quantidade de matéria "
            "orgânica produzida a cada ano pela fotossíntese é igual à quantidade "
            "de matéria orgânica destruída pela respiração e pela decomposição do "
            "leito.",
        ],
    ),
    item(
        "v1-ma-004",
        "answerable",
        "medio",
        DOC_MA,
        "Como é feita a repartição das parcelas no afolhamento regulado dos "
        "cultivadores de mandioca perto de Brazzaville?",
        "A cada ano, a folha de pousio mais antiga é subdividida em parcelas "
        "quadrangulares justapostas e repartida entre as famílias para desmate e "
        "cultivo de mandioca.",
        [140],
        [
            "A cada ano, a folha com pousio mais antiga (f10) é subdividida em "
            "parcelas justapostas e quadrangulares e repartidas entre as famílias "
            "para serem desmatadas e cultivadas com a mandioca.",
        ],
    ),
    item(
        "v1-ma-005",
        "answerable",
        "facil",
        DOC_MA,
        "O que se chama de 'folha' em um sistema de cultivo?",
        "O conjunto de parcelas que se encontram, em dado momento, no mesmo "
        "estágio de cultivo ou de pousio.",
        [140],
        [
            "É chamada folha o conjunto de parcelas que se encontram num dado "
            "momento no mesmo estágio de cultivo ou de pousio.",
        ],
    ),
    item(
        "v1-ma-006",
        "answerable",
        "dificil",
        DOC_MA,
        "Como o texto descreve o ritmo histórico vivido pelo Egito faraônico?",
        "As fases de prosperidade alternavam-se com períodos de crise e de decadência.",
        [200],
        [
            "Mas essas fases de prosperidade alternavam-se com períodos de crise e de decadência.",
        ],
    ),
    item(
        "v1-ma-007",
        "answerable",
        "medio",
        DOC_MA,
        "Que medidas o legislador Sólon adotou em Atenas no início do século VI a.C.?",
        "Exonerou os camponeses servos de seus encargos e proibiu a servidão por "
        "dívida e a venda de crianças como escravos.",
        [288],
        [
            "o legislador Sólon exonerou os camponeses servos de seus pesados "
            "encargos e proibiu a servidão por dívida e a venda de crianças como "
            "escravos",
        ],
    ),
    item(
        "v1-ma-008",
        "answerable",
        "medio",
        DOC_MA,
        "Qual era o caráter inicial da colonização grega descrita no texto?",
        "Foi a princípio agrária, exercida em planícies mais extensas, férteis e "
        "menos povoadas que as da Grécia.",
        [288],
        [
            "Essa colonização foi a princípio agrária, exercida nas planícies "
            "geralmente mais extensas, mais férteis e menos superpovoadas que as "
            "da Grécia.",
        ],
    ),
    item(
        "v1-ma-009",
        "answerable",
        "dificil",
        DOC_MA,
        "Em que meses ocorrem geadas na região andina estudada?",
        "Ocorrem todas as noites em junho e julho, podendo ainda ocorrer "
        "esporadicamente em março e novembro.",
        [230],
        [
            "Todas as noites em junho e julho ocorrem geadas, podendo ainda "
            "ocorrer esporadicamente em março e em novembro.",
        ],
    ),
    item(
        "v1-ma-010",
        "answerable",
        "medio",
        DOC_MA,
        "Como a indústria transformou os transportes no contexto da segunda revolução agrícola?",
        "Com as estradas de ferro e os barcos a vapor, revolucionou os "
        "transportes transcontinentais e transoceânicos.",
        [400],
        [
            "Paralelamente, com as estradas de ferro e os barcos a vapor, a "
            "indústria revolucionou os transportes transcontinentais e "
            "transoceânicos.",
        ],
    ),
    item(
        "v1-ma-011",
        "answerable",
        "medio",
        DOC_MA,
        "Quantos calendários agrícolas dos séculos XII e XIII Perrine Mane estudou?",
        "Estudou cento e vinte e sete calendários datados dos séculos XII e XIII "
        "na França e na Itália.",
        [320],
        [
            "Perrine Mane (1983) estuda cento e vinte sete calendários datados dos "
            "séculos XII e XIII na França e na Itália",
        ],
    ),
    item(
        "v1-ma-012",
        "answerable",
        "dificil",
        DOC_MA,
        "Qual é o argumento do texto sobre a agricultura camponesa e a "
        "modernização dos países pobres?",
        "A agricultura camponesa, mais produtiva, será capaz de suportar o custo "
        "da modernização e da industrialização dos países pobres.",
        [540],
        [
            "a agricultura camponesa, nitidamente mais produtiva, será capaz de "
            "suportar o custo da modernização e da industrialização dos países "
            "pobres",
        ],
    ),
    item(
        "v1-ma-013",
        "ambiguous_partial",
        "medio",
        DOC_MA,
        "Os sistemas de cultivo de derrubada-queimada deixaram de existir?",
        "Não totalmente: o texto indica que ainda existem, mas estão hoje "
        "ameaçados pela concorrência de agriculturas mais poderosas.",
        [170],
        [
            "esses sistemas estão hoje ameaçados pela concorrência econômica das "
            "agriculturas mais poderosas",
        ],
        notas=(
            "Parcial: o corpus afirma que tais sistemas persistem, mas coloca sua "
            "sobrevivência como questão aberta e urgente, sem um desfecho."
        ),
    ),
    item(
        "v1-ma-014",
        "ambiguous_partial",
        "dificil",
        DOC_MA,
        "As políticas europeias garantiram a modernização agrícola de forma "
        "homogênea entre os arrendatários?",
        "O texto cita leis que garantiam contratos de arrendamento de longa "
        "duração, mas ressalva que a eficácia foi amplamente condicionada, sem "
        "afirmar homogeneidade.",
        [480],
        [
            "leis garantiam aos arrendatários contratos de locação de terras de "
            "longa duração regularmente renovados",
        ],
        notas=(
            "Parcial: a passagem lista condições que 'amplamente condicionaram' a "
            "eficiência das medidas, de modo que o resultado não é apresentado "
            "como uniforme."
        ),
    ),
    item(
        "v1-ma-015",
        "ambiguous_partial",
        "medio",
        DOC_MA,
        "A religião teve papel na criação das novas regras de vida das primeiras "
        "sociedades agrícolas?",
        "O texto apenas conjectura que a religião emergente pode ter tido um "
        "papel na instauração dessas regras, sem afirmá-lo com certeza.",
        [110],
        [
            "pode-se pensar que a religião emergente teve um papel na instauração "
            "dessas novas regras de vida",
        ],
        notas=(
            "Parcial: a afirmação é apresentada como hipótese ('pode-se pensar'), "
            "não como fato estabelecido."
        ),
    ),
    item(
        "v1-ma-016",
        "unanswerable",
        "facil",
        DOC_MA,
        "Qual é a produtividade média de milho por hectare no Cerrado brasileiro "
        "com transgênicos em 2023?",
        notas=(
            "Não respondível: a obra é uma história global das agriculturas e não "
            "apresenta dados recentes de produtividade brasileira."
        ),
    ),
    item(
        "v1-ma-017",
        "unanswerable",
        "medio",
        DOC_MA,
        "Quais cultivares de trigo são recomendadas para o clima subtropical do sul do Brasil?",
        notas=(
            "Não respondível: o corpus não é um manual agronômico de recomendação de cultivares."
        ),
    ),
    item(
        "v1-ma-018",
        "unanswerable",
        "medio",
        DOC_MA,
        "Qual foi o volume de exportações agrícolas da União Europeia em 2022?",
        notas=(
            "Não respondível: o livro não traz estatísticas de comércio agrícola "
            "recente da União Europeia."
        ),
    ),
    item(
        "v1-ma-019",
        "unanswerable",
        "facil",
        DOC_MA,
        "Como funciona um trator com piloto automático por GPS?",
        notas=(
            "Não respondível: tecnologia de maquinário agrícola atual não é "
            "objeto desta obra histórica."
        ),
    ),
    item(
        "v1-ma-020",
        "unanswerable",
        "dificil",
        DOC_MA,
        "Qual é a taxa interna de retorno de um investimento em irrigação por "
        "pivô central no Matopiba?",
        notas=(
            "Não respondível: o corpus não realiza análise financeira de projetos "
            "de irrigação nessa região."
        ),
    ),
]

# ---------------------------------------------------------------------------
# Políticas-públicas-agricultura-familiar-e-sustentabilidade — table_heavy — 214
# ---------------------------------------------------------------------------
PP_ITEMS: list[dict] = [
    item(
        "v1-pp-001",
        "answerable",
        "facil",
        DOC_PP,
        "Em que período a expressão 'agricultura familiar' ganhou força no contexto brasileiro?",
        "Ganhou força em meados da década de 1990.",
        [20],
        [
            "a expressão agricultura familiar toma força, no contexto brasileiro, "
            "em meados da década de 90 (DENARDI, 2001; SCHNEIDER, 2003).",
        ],
    ),
    item(
        "v1-pp-002",
        "answerable",
        "medio",
        DOC_PP,
        "Qual a participação dos produtos agrícolas no total das importações "
        "brasileiras, segundo o texto?",
        "Apenas 5% do total das importações brasileiras, na média dos últimos "
        "três anos, são de produtos agrícolas.",
        [20],
        [
            "apenas 5% do total das importações brasileiras (na média dos últimos "
            "três anos) são de produtos agrícolas",
        ],
    ),
    item(
        "v1-pp-003",
        "answerable",
        "facil",
        DOC_PP,
        "Qual programa é apontado como marco de entrada da agricultura familiar "
        "na agenda de políticas públicas brasileiras?",
        "O PRONAF é apontado como esse marco de entrada.",
        [70],
        [
            "O PRONAF foi pautado como marco de entrada da agricultura familiar na "
            "agenda de políticas públicas brasileiras (HAWKES et al., 2016).",
        ],
    ),
    item(
        "v1-pp-004",
        "answerable",
        "dificil",
        DOC_PP,
        "O que precede a implementação de uma política pública, segundo o texto sobre o Plano ABC?",
        "A interpretação da política pelos burocratas de nível de rua.",
        [55],
        [
            "O processo de implementação de uma política pública é precedido pela "
            "interpretação dessa política pelos burocratas de nível de rua.",
        ],
    ),
    item(
        "v1-pp-005",
        "answerable",
        "medio",
        DOC_PP,
        "Qual município se destaca com a maior área de lavoura permanente "
        "colhida, segundo a figura apresentada?",
        "O município de Itaguaí, com 1.271 hectares de lavoura permanente colhida.",
        [85],
        [
            "o município de Itaguaí se destaca com uma área de lavoura permanente "
            "colhida de 1.271 hectares",
        ],
    ),
    item(
        "v1-pp-006",
        "answerable",
        "medio",
        DOC_PP,
        "Como Bonnal, Cazella e Maluf (2008) apresentam a agricultura familiar?",
        "Como um modelo propício para a pluriatividade rural e a "
        "multifuncionalidade da agricultura.",
        [85],
        [
            "é apresentada por Bonnal, Cazella e Maluf (2008) como um modelo "
            "propício para a pluriatividade rural e a multifuncionalidade da "
            "agricultura",
        ],
    ),
    item(
        "v1-pp-007",
        "answerable",
        "medio",
        DOC_PP,
        "Quantas variedades de fava crioula foram utilizadas no estudo e de onde foram obtidas?",
        "Dez variedades de fava crioula, obtidas do banco de sementes do "
        "Laboratório de Sementes do IFPB, Campus Picuí.",
        [100],
        [
            "Utilizou-se dez variedades de favas (Phaseulos lunatus L.) crioulas, "
            "que foram obtidas do banco de sementes do Laboratório de Sementes do "
            "IFPB, Campus Picuí.",
        ],
    ),
    item(
        "v1-pp-008",
        "answerable",
        "facil",
        DOC_PP,
        "Qual é o perfil de estado civil dos assentados do assentamento Fortuna 1?",
        "14% são solteiros, 38% são separados e 48% são casados.",
        [110],
        [
            "Dos assentados do assentamento Fortuna 1, 14% são solteiros, 38% são "
            "separados e 48% casados.",
        ],
    ),
    item(
        "v1-pp-009",
        "answerable",
        "medio",
        DOC_PP,
        "Quando o direito ao voto feminino foi conquistado no Reino Unido, segundo o texto?",
        "Em 1918.",
        [165],
        [
            "O direito ao voto foi conquistado no Reino Unido em 1918 (PINTO, 2009).",
        ],
    ),
    item(
        "v1-pp-010",
        "answerable",
        "dificil",
        DOC_PP,
        "Que episódio envolvendo a feminista Emily Davison é relatado no texto?",
        "Em 1913, na corrida de cavalos em Derby, ela se atirou à frente do "
        "cavalo do Rei e morreu.",
        [165],
        [
            "Em 1913, na famosa corrida de cavalo em Derby, a feminista Emily "
            "Davison atirou-se à frente do cavalo do Rei, morrendo.",
        ],
    ),
    item(
        "v1-pp-011",
        "answerable",
        "facil",
        DOC_PP,
        "Que tipo de ação o MST promove, segundo o texto?",
        "Ações educativas de cuidado com o solo e com as plantações.",
        [205],
        [
            "O MST promove ações educativas de cuidados com o solo e com as plantações.",
        ],
    ),
    item(
        "v1-pp-012",
        "answerable",
        "medio",
        DOC_PP,
        "A que se relaciona a subcategoria 'Processos' na avaliação do PNAE?",
        "Aglutina atributos político-administrativos de implementação e avaliação do PNAE.",
        [70],
        [
            "A subcategoria Processos aglutina atributos político-administrativos "
            "de implementação e avaliação do PNAE.",
        ],
    ),
    item(
        "v1-pp-013",
        "ambiguous_partial",
        "medio",
        DOC_PP,
        "A agroecologia é apenas uma técnica de produção agrícola?",
        "O artigo indica que a agroecologia é mais do que criar ou inovar um "
        "sistema de produção agrícola, mas a definição plena é desenvolvida ao "
        "longo do texto.",
        [195],
        [
            "O artigo indica que a agroecologia é mais do que criar ou inovar um "
            "sistema de produção agrícola.",
        ],
        notas=(
            "Parcial: a passagem afirma que a agroecologia é 'mais do que' um "
            "sistema de produção, mas não esgota a definição, construída ao longo "
            "do artigo."
        ),
    ),
    item(
        "v1-pp-014",
        "ambiguous_partial",
        "dificil",
        DOC_PP,
        "Existe uma definição única de agricultura familiar no texto?",
        "Não: o texto afirma que não há uma conceituação única e que as "
        "apropriações do conceito abrangem diferentes percepções.",
        [85],
        [
            "Notoriamente, não há uma conceituação única, e é importante destacar "
            "que as apropriações destes conceitos abrangem diferentes percepções e "
            "concepções sobre as diferentes formas e práticas da produção rural.",
        ],
        notas=(
            "Parcial: o próprio corpus declara a ausência de conceituação única, "
            "de modo que não há resposta fechada."
        ),
    ),
    item(
        "v1-pp-015",
        "ambiguous_partial",
        "medio",
        DOC_PP,
        "Há consenso entre atores políticos e implementadores do Plano ABC sobre "
        "o que é mudança climática?",
        "Não: o texto indica que não há compartilhamento de significados entre "
        "esses atores, embora o trecho não detalhe todas as razões.",
        [55],
        [
            "Não há um compartilhamento de significados entre os atores políticos "
            "e os implementadores do Plano ABC",
        ],
        notas=(
            "Parcial: a frase é interrompida ('visto que') e apenas assinala a "
            "ausência de significado compartilhado, sem exposição completa."
        ),
    ),
    item(
        "v1-pp-016",
        "unanswerable",
        "facil",
        DOC_PP,
        "Qual é a alíquota do ICMS sobre produtos da agricultura familiar no "
        "estado de São Paulo em 2024?",
        notas=(
            "Não respondível: a coletânea não trata de alíquotas tributárias "
            "estaduais nem de sua vigência atual."
        ),
    ),
    item(
        "v1-pp-017",
        "unanswerable",
        "medio",
        DOC_PP,
        "Quantos hectares de café foram colhidos em Minas Gerais na safra de 2021?",
        notas=(
            "Não respondível: o corpus não apresenta estatísticas de área colhida "
            "de café por estado e safra."
        ),
    ),
    item(
        "v1-pp-018",
        "unanswerable",
        "medio",
        DOC_PP,
        "Quais são os critérios de acesso ao Plano Safra 2024/2025 anunciado pelo governo federal?",
        notas=("Não respondível: trata-se de política posterior e específica, ausente desta obra."),
    ),
    item(
        "v1-pp-019",
        "unanswerable",
        "facil",
        DOC_PP,
        "Como fazer compostagem doméstica de resíduos orgânicos, passo a passo?",
        notas=("Não respondível: o corpus não é um manual prático de compostagem."),
    ),
    item(
        "v1-pp-020",
        "unanswerable",
        "dificil",
        DOC_PP,
        "Qual é o coeficiente de Gini da distribuição de terras no Brasil segundo "
        "o Censo Agropecuário de 2017?",
        notas=(
            "Não respondível: o índice de concentração fundiária do Censo de 2017 "
            "não é apresentado nesta obra."
        ),
    ),
]

# ---------------------------------------------------------------------------
# buhler-9786557250044 — table_heavy — 277 pages
# ---------------------------------------------------------------------------
BH_ITEMS: list[dict] = [
    item(
        "v1-bh-001",
        "answerable",
        "medio",
        DOC_BH,
        "Como o autor caracteriza a inclusão dos pequenos produtores integrados à "
        "produção de soja?",
        "Como uma inclusão discriminatória, marcada por forte subordinação dos "
        "pequenos produtores.",
        [20],
        [
            "tal inclusão é discriminatória e o que se verifica é uma forte "
            "subordinação dos pequenos produtores que estão integrados à produção "
            "de soja",
        ],
    ),
    item(
        "v1-bh-002",
        "answerable",
        "dificil",
        DOC_BH,
        "Por que os produtores de grãos acabam pagando pelo frete mais caro, segundo o texto?",
        "Porque sempre pagam pelo maior frete — modal mais caro e porto mais "
        "distante —, ainda que os grãos sejam retirados por combinação menos "
        "onerosa.",
        [95],
        [
            "eles sempre pagam pelo maior frete (modal mais caro e porto mais "
            "distante), ainda que seus grãos sejam retirados por uma combinação "
            "modal menos onerosa",
        ],
    ),
    item(
        "v1-bh-003",
        "answerable",
        "medio",
        DOC_BH,
        "Que problema a ALL cria para os terminais concorrentes, segundo o texto?",
        "Estabelece concorrência desleal, pois tem o poder de decidir onde será "
        "feita a montagem e a saída das composições com os grãos.",
        [95],
        [
            "a ALL estabelece uma concorrência desleal com as empresas que operam "
            "os demais terminais, pois tem o poder de decidir em qual local será "
            "feita a montagem e saída das composições com os grãos",
        ],
    ),
    item(
        "v1-bh-004",
        "answerable",
        "medio",
        DOC_BH,
        "O que indica a maior concentração do crédito rural nos contratos acima de R$ 300 mil?",
        "Que o crescimento do crédito ocorreu sem transformar o número de "
        "produtores beneficiados nem descentralizar recursos para outras regiões "
        "e cultivos.",
        [110],
        [
            "o crescimento do crédito rural nos últimos anos realizou-se sem "
            "grandes transformações no número de produtores beneficiados e sem "
            "descentralizar os recursos para outras regiões e cultivos agrícolas",
        ],
    ),
    item(
        "v1-bh-005",
        "answerable",
        "medio",
        DOC_BH,
        "Que efeito a adoção de novos sistemas técnicos agrícolas teve sobre o "
        "aproveitamento dos solos?",
        "Aumentou a possibilidade de aproveitar solos menos férteis e ocupar "
        "intensivamente espaços antes desprezados.",
        [65],
        [
            "Aumentou a possibilidade de aproveitamento dos solos menos férteis e "
            "de ocupação intensiva de espaços agrícolas até então desprezados para "
            "tais atividades.",
        ],
    ),
    item(
        "v1-bh-006",
        "answerable",
        "dificil",
        DOC_BH,
        "Qual é a extensão de terras que a família estudada possui atualmente em São Gabriel?",
        "Possui 3.215 hectares em São Gabriel, além de arrendar outros 500 hectares.",
        [155],
        [
            "hoje em São Gabriel, possuem 3.215 ha, além de arrendar outros 500 ha",
        ],
    ),
    item(
        "v1-bh-007",
        "answerable",
        "dificil",
        DOC_BH,
        "Como evoluiu a participação de pessoas físicas uruguaias na posse de "
        "terras entre 2000 e 2011?",
        "Caiu de 90% das terras em 2000 para 54% em 2011.",
        [215],
        [
            "no ano 2000, 90% das terras estavam nas mãos de pessoas físicas de "
            "nacionalidade uruguaia e, em 2011, esta cifra caiu para 54%",
        ],
    ),
    item(
        "v1-bh-008",
        "answerable",
        "medio",
        DOC_BH,
        "Como a soja foi apresentada no discurso empresarial boliviano?",
        "Como uma commodity com 'vantagens comparativas' que levaria o país a uma "
        "inserção internacional efetiva e traria progresso à sociedade.",
        [250],
        [
            "A soja foi apresentada como uma commodity com “vantagens "
            "comparativas” que levaria o país a uma efetiva inserção no comercio "
            "internacional, o que por sua vez traria progresso para o conjunto da "
            "sociedade boliviana.",
        ],
    ),
    item(
        "v1-bh-009",
        "answerable",
        "medio",
        DOC_BH,
        "Quantas entrevistas compõem o corpus de análise do capítulo sobre "
        "prestadores de serviços agrícolas?",
        "Um corpus de 56 entrevistas.",
        [230],
        [
            "A principal fonte de análise deste capítulo consiste em um corpus de 56 entrevistas.",
        ],
    ),
    item(
        "v1-bh-010",
        "answerable",
        "dificil",
        DOC_BH,
        "O que se observa em relação ao paradigma ecológico na região tratada?",
        "Observa-se uma mudança de paradigma ecológico numa região onde a "
        "conservação se restringia a ecossistemas percebidos como virgens.",
        [170],
        [
            "Observa-se nesta ocasião uma mudança de paradigma ecológico",
        ],
    ),
    item(
        "v1-bh-011",
        "answerable",
        "medio",
        DOC_BH,
        "Que pressuposto o texto atribui à visão que separa a produção agrária da "
        "atividade industrial?",
        "O pressuposto de que a produção agrária tem por eixo um processo natural "
        "e que o produto — grãos ou gado — não implica manipulação humana.",
        [35],
        [
            "se trata de uma atividade cujo eixo da produção é um processo natural "
            "e que o produto – grãos ou gado – não implica nenhuma manipulação por "
            "parte do homem",
        ],
    ),
    item(
        "v1-bh-012",
        "answerable",
        "facil",
        DOC_BH,
        "Qual é a moagem média anual por usina das nove unidades administradas "
        "por grandes grupos empresariais?",
        "Uma média de 2,2 milhões de toneladas por ano por usina.",
        [200],
        [
            "o conjunto de 9 unidades administradas por grandes grupos "
            "empresariais moem 19,2 milhões t/ano, o que representa uma média de "
            "2,2 milhões de t/ano por usina",
        ],
    ),
    item(
        "v1-bh-013",
        "ambiguous_partial",
        "dificil",
        DOC_BH,
        "Qual será a magnitude exata da expansão da fronteira agrícola prevista "
        "na Agenda Patriótica 2015 boliviana?",
        "O texto informa que se trata de milhões de hectares, mas que a magnitude "
        "exata ainda não é conhecida.",
        [250],
        [
            "A magnitude dessa expansão ainda não é conhecida, ainda que se saiba "
            "tratar-se de milhões de hectares.",
        ],
        notas=("Parcial: o corpus afirma explicitamente que a magnitude exata não é conhecida."),
    ),
    item(
        "v1-bh-014",
        "ambiguous_partial",
        "medio",
        DOC_BH,
        "O programa Cambio Rural ofereceu crédito barato aos pequenos produtores rurais?",
        "O texto afirma que o programa nunca contou com linhas de crédito barato, "
        "embora avalie seus resultados como díspares e no geral positivos.",
        [140],
        [
            "O programa nunca contou com linhas de crédito barato para produtores, "
            "o que constituía uma necessidade imperiosa do pequeno empresariado "
            "rural na primeira das décadas observadas.",
        ],
        notas=(
            "Parcial: a ausência de crédito barato convive com uma avaliação de "
            "'resultados díspares, mas no geral positivos', o que impede um "
            "julgamento simples."
        ),
    ),
    item(
        "v1-bh-015",
        "ambiguous_partial",
        "medio",
        DOC_BH,
        "É possível saber com precisão quanta terra uruguaia foi comprada por estrangeiros?",
        "Não com precisão: o texto afirma que há grandes compras por companhias "
        "estrangeiras, mas não há registros para o país como um todo.",
        [215],
        [
            "É sabido que ocorrem grandes compras de terra por companhias "
            "estrangeiras, mas não há registros dessas compras para o país como um "
            "todo.",
        ],
        notas=(
            "Parcial: os dados são incompletos porque grande parte das compras é "
            "feita sob a forma de sociedades anônimas."
        ),
    ),
    item(
        "v1-bh-016",
        "unanswerable",
        "facil",
        DOC_BH,
        "Qual é a cotação atual do dólar frente ao real?",
        notas=("Não respondível: o livro não fornece cotações cambiais, muito menos atuais."),
    ),
    item(
        "v1-bh-017",
        "unanswerable",
        "medio",
        DOC_BH,
        "Quantas toneladas de soja o Brasil exportou para a China em 2023?",
        notas=(
            "Não respondível: o corpus não apresenta volumes de exportação de "
            "soja por destino e ano recente."
        ),
    ),
    item(
        "v1-bh-018",
        "unanswerable",
        "medio",
        DOC_BH,
        "Quais são as exigências fitossanitárias para exportar carne bovina "
        "brasileira à União Europeia?",
        notas=(
            "Não respondível: exigências fitossanitárias e regulatórias de "
            "exportação não são tema desta obra."
        ),
    ),
    item(
        "v1-bh-019",
        "unanswerable",
        "facil",
        DOC_BH,
        "Como calcular a dose de calcário para correção da acidez do solo?",
        notas=("Não respondível: procedimento agronômico de correção de solo não é abordado."),
    ),
    item(
        "v1-bh-020",
        "unanswerable",
        "dificil",
        DOC_BH,
        "Qual é a estrutura acionária atualizada da Cargill Brasil em 2024?",
        notas=(
            "Não respondível: o corpus não traz a composição societária atual de empresas do setor."
        ),
    ),
]

# ---------------------------------------------------------------------------
# LIVRO  MUNDIALIZAÇÃO pronto — dense — 545 pages
# ---------------------------------------------------------------------------
MU_ITEMS: list[dict] = [
    item(
        "v1-mu-001",
        "answerable",
        "medio",
        DOC_MU,
        "Que posição o Brasil ocupava no comércio mundial agrícola, segundo a notícia citada?",
        "Havia ultrapassado o Canadá e se tornado o terceiro maior exportador de "
        "produtos agrícolas do mundo.",
        [110],
        [
            "O Brasil ultrapassou o Canadá e se tornou o terceiro maior exportador "
            "de produtos agrícolas do mundo.",
        ],
    ),
    item(
        "v1-mu-002",
        "answerable",
        "dificil",
        DOC_MU,
        "Qual foi a área de terras envolvida na aquisição da Klabin no Paraná?",
        "A compra envolveu 107 mil hectares, dos quais 63 mil hectares de "
        "florestas plantadas no Paraná.",
        [230],
        [
            "A compra envolve 107 mil hectares de terras com 63 mil hectares de "
            "florestas plantadas no Paraná.",
        ],
    ),
    item(
        "v1-mu-003",
        "answerable",
        "medio",
        DOC_MU,
        "Por que associar-se à Klabin interessava à chilena Arauco, segundo o texto?",
        "Era uma forma de driblar a restrição à compra de terras por estrangeiros.",
        [230],
        [
            "Para a chilena Arauco, associar-se à Klabin é uma forma de driblar a "
            "restrição à compra de terras por estrangeiros.",
        ],
    ),
    item(
        "v1-mu-004",
        "answerable",
        "dificil",
        DOC_MU,
        "Como foi estruturado o negócio entre a Bunge e o grupo Moema?",
        "Foi um negócio de US$ 1,5 bilhão sem dinheiro, apenas com troca de ações "
        "da Bunge na Bolsa de Nova York pelas do grupo brasileiro.",
        [140],
        [
            "O negócio, de US$1,5 bilhão, não envolveu dinheiro, apenas a troca de "
            "ações da Bunge na Bolsa de Nova York pelas do grupo brasileiro.",
        ],
    ),
    item(
        "v1-mu-005",
        "answerable",
        "dificil",
        DOC_MU,
        "O que levou a Sementes Selecta a pedir recuperação judicial, segundo o texto?",
        "Os contratos de proteção ('hedge') feitos no mercado futuro para se "
        "proteger da variação dos preços da soja.",
        [290],
        [
            "O infortúnio da Selecta foi ironicamente resultado dos contratos de "
            'proteção ("hedge") que a empresa fez no mercado futuro para se '
            "proteger da variação dos preços da soja.",
        ],
    ),
    item(
        "v1-mu-006",
        "answerable",
        "medio",
        DOC_MU,
        "Que obra rodoviária foi privatizada em 1994 no governo Itamar Franco?",
        "A Ponte Rio-Niterói.",
        [80],
        [
            "No subsetor rodoviário foi privatizada em 1994 a Ponte Rio-Niterói no "
            "governo Itamar Franco/PRN.",
        ],
    ),
    item(
        "v1-mu-007",
        "answerable",
        "facil",
        DOC_MU,
        "Qual foi o prazo contratual da concessão citada no setor rodoviário?",
        "Vinte anos, de 1995 a 2015.",
        [80],
        [
            "Foi adotado o modelo de concessão e o prazo contratual foi de 20 anos - 1995/2015.",
        ],
    ),
    item(
        "v1-mu-008",
        "answerable",
        "medio",
        DOC_MU,
        "O que caracteriza o 'Consórcio Modular' na indústria automobilística, segundo o texto?",
        "Os fornecedores tornam-se responsáveis pela montagem de pelo menos "
        "alguma parte dos veículos.",
        [30],
        [
            "No Consórcio Modular, os fornecedores tornam-se responsáveis pela "
            "montagem de pelo menos alguma parte dos veículos.",
        ],
    ),
    item(
        "v1-mu-009",
        "answerable",
        "dificil",
        DOC_MU,
        "Em quais estados se localiza a área da Sollus, na região conhecida como 'Mapitoba'?",
        "Nos estados do Maranhão, Piauí, Tocantins e Bahia.",
        [410],
        [
            "A Sollus tem uma área de 30 mil hectares – dos quais, aproximadamente "
            "16 mil cultiváveis – no Maranhão, Piauí, Tocantins e Bahia (região "
            'conhecida como "Mapitoba").',
        ],
    ),
    item(
        "v1-mu-010",
        "answerable",
        "medio",
        DOC_MU,
        "Que decisão da CTNBio, no final da década de 1990, é apontada como marco "
        "da liberação de transgênicos no Brasil?",
        "A autorização do plantio comercial da soja Roundup Ready (RR), tolerante "
        "ao herbicida glifosato.",
        [450],
        [
            "a Comissão Técnica Nacional de Biossegurança (CTNBio) autorizou o "
            "plantio comercial da soja Roundup Ready (RR), tolerante ao herbicida "
            "glifosato",
        ],
    ),
    item(
        "v1-mu-011",
        "answerable",
        "dificil",
        DOC_MU,
        "A que efeitos sobre embriões de ratos está associada a cipermetrina, segundo o texto?",
        "É tóxica para os embriões de ratos, incluindo perda pós-implantação dos "
        "fetos e más-formações viscerais.",
        [490],
        [
            "e tóxica para os embriões de ratos, incluindo a perda pós-implantação "
            "dos fetos e másformações viscerais",
        ],
    ),
    item(
        "v1-mu-012",
        "answerable",
        "medio",
        DOC_MU,
        "Com qual grupo a trading suíça Glencore fechou acordo no setor do trigo?",
        "Com o Grupo Predileto, comprando 50% do capital da controladora dos "
        "Moinhos Cruzeiro do Sul.",
        [260],
        [
            "fechou um acordo com a Predileto Investimentos S/A do Grupo "
            "Predileto, controladora dos Moinhos Cruzeiro do Sul S/A, comprou 50% "
            "do capital da empresa nacional",
        ],
    ),
    item(
        "v1-mu-013",
        "ambiguous_partial",
        "medio",
        DOC_MU,
        "A ascensão do Brasil a terceiro maior exportador agrícola reflete um "
        "avanço econômico real?",
        "O autor contesta essa leitura, tratando a mudança de posição no ranking "
        "como uma 'matemagia' ideológica.",
        [110],
        [
            'Utilizando-se dessa "matemagia" o agronegócio do Brasil passou de 5o lugar para 3o',
        ],
        notas=(
            "Parcial: o texto enquadra o salto no ranking como 'matemagia' "
            "ideológica, contestando-o em vez de confirmá-lo como progresso real."
        ),
    ),
    item(
        "v1-mu-014",
        "ambiguous_partial",
        "dificil",
        DOC_MU,
        "A produção agropecuária em larga escala beneficia o conjunto da sociedade?",
        "Segundo o depoimento citado, essa produção só é vantajosa para um grupo "
        "— usineiros e grandes fazendeiros —, não para o conjunto da sociedade.",
        [520],
        [
            "Essa produção agropecuária em larga escala só é vantajosa para um grupo.",
        ],
        notas=(
            "Parcial: trata-se de um testemunho crítico que atribui os benefícios "
            "a 'um grupo social', não de uma análise equilibrada do conjunto."
        ),
    ),
    item(
        "v1-mu-015",
        "ambiguous_partial",
        "medio",
        DOC_MU,
        "A legalização do cultivo de transgênicos no Brasil seguiu um percurso regular?",
        "O autor a caracteriza como uma 'legalização às avessas', com "
        "peculiaridades que precisam ser resgatadas, sem descrevê-la como "
        "regular.",
        [450],
        [
            "A historicidade de uma legalização às avessas: A liberação do cultivo "
            "e manipulação dos OGMs no Brasil possui peculiaridades que precisam "
            "ser resgatadas.",
        ],
        notas=(
            "Parcial: a expressão 'legalização às avessas' aponta irregularidade, "
            "mas o percurso completo depende da narrativa que se segue no texto."
        ),
    ),
    item(
        "v1-mu-016",
        "unanswerable",
        "facil",
        DOC_MU,
        "Qual é o preço do litro do etanol nas bombas de São Paulo hoje?",
        notas=(
            "Não respondível: a obra não fornece preços de combustível ao "
            "consumidor, tampouco atuais."
        ),
    ),
    item(
        "v1-mu-017",
        "unanswerable",
        "medio",
        DOC_MU,
        "Quantos empregos diretos o setor sucroenergético gerou no Brasil em 2023?",
        notas=(
            "Não respondível: o corpus não apresenta estatísticas de emprego do setor para 2023."
        ),
    ),
    item(
        "v1-mu-018",
        "unanswerable",
        "medio",
        DOC_MU,
        "Qual é a capacidade instalada de energia solar do agronegócio brasileiro?",
        notas=("Não respondível: geração de energia solar não é tema tratado nesta obra."),
    ),
    item(
        "v1-mu-019",
        "unanswerable",
        "facil",
        DOC_MU,
        "Como registrar uma cooperativa agrícola na Junta Comercial?",
        notas=(
            "Não respondível: o procedimento jurídico de registro de cooperativas não é abordado."
        ),
    ),
    item(
        "v1-mu-020",
        "unanswerable",
        "dificil",
        DOC_MU,
        "Qual é a pegada de carbono por tonelada de soja exportada pelo porto de Santos?",
        notas=("Não respondível: o corpus não calcula pegada de carbono por tonelada exportada."),
    ),
]

# ---------------------------------------------------------------------------
# poor-scan fixture (derived from ph,+...+cerrado-goiano.pdf) — 18 fixture pages
# paginas_esperadas are FIXTURE pages; the manifest page_map translates each to
# the original source page for the evidence audit.
# ---------------------------------------------------------------------------
CG_ITEMS: list[dict] = [
    item(
        "v1-cg-001",
        "answerable",
        "facil",
        DOC_CG,
        "Qual tem sido o maior símbolo do processo de ocupação agrícola do "
        "Cerrado, além da transgenia?",
        "O uso crescente de agrotóxicos.",
        [2],
        [
            "Além da tecnologia da transgenia, o maior símbolo desse processo tem "
            "sido o uso crescente de agrotóxicos.",
        ],
    ),
    item(
        "v1-cg-002",
        "answerable",
        "facil",
        DOC_CG,
        "Qual é a extensão contínua do Cerrado e sua participação no território brasileiro?",
        "Uma área contínua de 192,8 milhões de hectares, o equivalente a 22,65% "
        "do território brasileiro.",
        [3],
        [
            "com uma área contínua de 192,8 milhões de hectares (22,65% do território brasileiro)",
        ],
    ),
    item(
        "v1-cg-003",
        "answerable",
        "medio",
        DOC_CG,
        "Qual é a relação entre o território de Goiás e o bioma Cerrado?",
        "Considerando as áreas de transição, Goiás tem 100% de seu território no "
        "Cerrado, o que corresponde a 17,64% da cobertura total do bioma no país.",
        [3],
        [
            "o estado tem 100% de seu território no Cerrado, o que corresponde a "
            "17,64% da cobertura total desse bioma no país",
        ],
    ),
    item(
        "v1-cg-004",
        "answerable",
        "medio",
        DOC_CG,
        "Quanto resta da área original do Cerrado, segundo o IBGE (2012)?",
        "Remanesce somente 50,9% da área original do Cerrado.",
        [4],
        [
            "remanesce somente 50,9% da área original do Cerrado",
        ],
    ),
    item(
        "v1-cg-005",
        "answerable",
        "dificil",
        DOC_CG,
        "Qual estado apresenta a maior perda de área do bioma Cerrado e em que proporção?",
        "Goiás, onde a supressão do bioma chega a 65,5% da área total.",
        [4],
        [
            "No estado de Goiás, a supressão do bioma chega a 65,5% da área total",
        ],
    ),
    item(
        "v1-cg-006",
        "answerable",
        "medio",
        DOC_CG,
        "Quantas espécies de animais do Cerrado estão ameaçadas de extinção por "
        "causa da expansão agrícola?",
        "Pelo menos 137 espécies de animais que ocorrem no Cerrado.",
        [5],
        [
            "pelo menos 137espécies de animais que ocorrem no Cerrado estão "
            "ameaçadas de extinção em razão da grande expansão da agricultura",
        ],
    ),
    item(
        "v1-cg-007",
        "answerable",
        "facil",
        DOC_CG,
        "Em que ano e contexto histórico a Revolução Verde foi estabelecida, segundo o texto?",
        "A partir de 1945, no contexto da Guerra Fria, em um mundo polarizado "
        "entre dois blocos de poder.",
        [6],
        [
            "A Revolução Verde foi estabelecida a partir de 1945, no contexto da "
            "Guerra Fria, em um mundo polarizado entre dois blocos de poder.",
        ],
    ),
    item(
        "v1-cg-008",
        "answerable",
        "medio",
        DOC_CG,
        "Quais efeitos o chamado 'modelo convencional' teve sobre os pequenos agricultores?",
        "Levou-os a perder o controle da produção, a comprar insumos cada vez "
        "mais caros e a vender seus produtos a preços cada vez menores.",
        [7],
        [
            "O chamado “modelo convencional” levou os pequenos agricultores a "
            "perder o controle da produção, a comprar insumos cada vez mais caros "
            "e a vender seus produtos a preços cada vez menores.",
        ],
    ),
    item(
        "v1-cg-009",
        "answerable",
        "dificil",
        DOC_CG,
        "Quais doenças estão entre as principais decorrentes das intoxicações por agrotóxicos?",
        "Doenças dermatológicas, problemas renais e vários tipos de câncer.",
        [9],
        [
            "Doenças dermatológicas, problemas renais e vários tipos de cânceres "
            "estão entre as principais enfermidades resultantes das intoxicações "
            "por agrotóxicos (ROSA; PESSOA; RIGOTTO, 2011).",
        ],
    ),
    item(
        "v1-cg-010",
        "answerable",
        "medio",
        DOC_CG,
        "O que o texto afirma sobre a permanência dos resíduos de agrotóxicos na natureza?",
        "Podem permanecer na natureza por vários anos, tornando quase impossível "
        "identificar espécies livres de contaminação.",
        [10],
        [
            "Os resíduos de agrotóxicos podem permanecer na natureza por vários "
            "anos, como indicaram pesquisas em várias partes do mundo, tornando "
            "quase impossível identificar espécies livres de contaminação.",
        ],
    ),
    item(
        "v1-cg-011",
        "answerable",
        "medio",
        DOC_CG,
        "Como o Centro Mundial Agroflorestal define os sistemas agroflorestais (SAF)?",
        "Como a integração de árvores em paisagens rurais produtivas.",
        [14],
        [
            "O Centro Mundial Agroflorestal define SAF como a integração de "
            "árvores em paisagens rurais produtivas.",
        ],
    ),
    item(
        "v1-cg-012",
        "answerable",
        "dificil",
        DOC_CG,
        "Quantos trabalhos sobre agroextrativismo foram encontrados nas bases ISI "
        "e Scopus no período de 1991 a 2014?",
        "Foram 52 trabalhos no ISI e 109 no Scopus.",
        [15],
        [
            "No ISI, foram encontrados 52 trabalhos e, no Scopus, 109, publicados "
            "no período de 1991 a 2014.",
        ],
    ),
    item(
        "v1-cg-013",
        "ambiguous_partial",
        "medio",
        DOC_CG,
        "O leite materno de mães brasileiras está contaminado por agrotóxicos?",
        "O texto relata a detecção de diferentes tipos de agrotóxicos no leite "
        "materno, mas com base em um estudo localizado (Lucas do Rio Verde/MT), "
        "não em uma conclusão nacional.",
        [11],
        [
            "O resultado mais surpreendente, no entanto, foi a detecção de "
            "diferentes tipos de agrotóxicos no leite materno.",
        ],
        notas=(
            "Parcial: a evidência vem de uma pesquisa localizada (Lucas do Rio "
            "Verde/MT), não de uma medição nacional generalizável."
        ),
    ),
    item(
        "v1-cg-014",
        "ambiguous_partial",
        "dificil",
        DOC_CG,
        "Por que o Pantanal não foi objeto de estudos sobre agroextrativismo?",
        "O texto apenas conjectura que o Pantanal, visto por muitos como "
        "subsistema do Cerrado, talvez tenha sido enquadrado nas pesquisas sobre "
        "este bioma.",
        [17],
        [
            "O Pantanal, considerado por muitos autores como um subsistema do "
            "Cerrado, talvez tenha sido enquadrado nas pesquisas acerca deste "
            "bioma.",
        ],
        notas=(
            "Parcial: os próprios autores afirmam fazer 'apenas suposições' para "
            "explicar a ausência desses biomas."
        ),
    ),
    item(
        "v1-cg-015",
        "ambiguous_partial",
        "medio",
        DOC_CG,
        "Os resultados de pesquisas financiadas pela indústria de agrotóxicos são "
        "declarados de forma transparente?",
        "Há indícios de que não são declarados com transparência, tendendo a "
        "favorecer o produto, mas o texto ressalva que isso também ocorre em "
        "estudos não financiados por empresas.",
        [18],
        [
            "Há muitos indícios de que os resultados destas pesquisas não são "
            "declarados de forma transparente, pois tendem a ser escritos de "
            "maneira enviesada em favor do produto.",
        ],
        notas=(
            "Parcial: o corpus qualifica imediatamente que o enviesamento também "
            "aparece em estudos não financiados por empresas."
        ),
    ),
    item(
        "v1-cg-016",
        "unanswerable",
        "facil",
        DOC_CG,
        "Qual é o preço médio da saca de soja na bolsa de Chicago em 2024?",
        notas=(
            "Não respondível: o livro trata de agrotóxicos e agroextrativismo no "
            "Cerrado, não de cotações de commodities."
        ),
    ),
    item(
        "v1-cg-017",
        "unanswerable",
        "medio",
        DOC_CG,
        "Quais são os procedimentos de registro de um novo agrotóxico junto ao IBAMA e à ANVISA?",
        notas=(
            "Não respondível: o texto discute impactos dos agrotóxicos, mas não o "
            "processo regulatório de registro."
        ),
    ),
    item(
        "v1-cg-018",
        "unanswerable",
        "medio",
        DOC_CG,
        "Qual foi a área plantada de cana-de-açúcar no estado de São Paulo na safra 2019/2020?",
        notas=("Não respondível: foge do escopo regional e temático, centrado no Cerrado goiano."),
    ),
    item(
        "v1-cg-019",
        "unanswerable",
        "facil",
        DOC_CG,
        "Como preparar uma calda bordalesa para o controle de fungos em hortaliças?",
        notas=("Não respondível: receita agronômica de defensivo não é abordada na obra."),
    ),
    item(
        "v1-cg-020",
        "unanswerable",
        "dificil",
        DOC_CG,
        "Qual é a estrutura química detalhada da molécula de glifosato e sua rota "
        "de síntese industrial?",
        notas=(
            "Não respondível: o texto cita riscos do glifosato à saúde, mas não "
            "descreve sua estrutura química nem rota de síntese."
        ),
    ),
]

ALL_ITEMS: list[dict] = HA_ITEMS + MA_ITEMS + PP_ITEMS + BH_ITEMS + MU_ITEMS + CG_ITEMS


def build() -> list[dict]:
    return ALL_ITEMS


def main() -> None:
    out_path = pathlib.Path(__file__).parent / "datasets" / "v1" / "golden.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(entry, ensure_ascii=False) for entry in ALL_ITEMS]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(ALL_ITEMS)} items to {out_path}")


if __name__ == "__main__":
    main()
