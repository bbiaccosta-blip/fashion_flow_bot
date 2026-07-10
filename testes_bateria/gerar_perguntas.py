# -*- coding: utf-8 -*-
"""
gerar_perguntas.py — Gera ~1000 perguntas comuns pra bateria de teste do Fashion Flow Bot.

Cada pergunta vem com a CATEGORIA esperada. Depois, testar_bot.py roda todas
pelo pipeline real e compara a intenção classificada com o conjunto de intenções
aceitáveis daquela categoria (ver MAPA_CATEGORIA_INTENCOES em testar_bot.py).

As frases imitam como cliente real digita: minúsculas, sem acento, gíria,
com e sem pontuação, com typo. Uso só produtos/tecidos/cores que o extractor conhece.
"""
import csv
import itertools
import os
import random

random.seed(42)  # reprodutível

# Vocabulário que o bot REALMENTE reconhece (do extractor.py)
PRODUTOS = ["camiseta", "camisetas", "polo", "moletom", "jaqueta", "calca jeans",
            "legging", "bermuda", "regata", "vestido midi", "baby look", "jogger",
            "uniforme", "jaleco", "camiseta premium", "oversized"]
TECIDOS = ["algodao", "viscose", "linho", "jeans", "suplex", "dry fit", "moletom flanelado",
           "algodao pima", "alfaiataria", "malha mista"]
CORES = ["preto", "branco", "cinza", "marinho", "vermelho", "vinho", "verde militar",
         "amarelo", "rosa", "azul", "royal"]
PERSONALIZACOES = ["silk", "silkscreen", "dtf", "bordado", "estampa", "serigrafia"]
QTDS = [10, 20, 30, 50, 100, 150, 200, 300, 500, 1000]

perguntas = []  # (categoria, texto)


def add(categoria, *textos):
    for t in textos:
        perguntas.append((categoria, t))


# ─────────────────────────────────────────────────────────────────────
# 1. SOCIAL — saudações, despedidas, agradecimentos, elogios, ofensas
# ─────────────────────────────────────────────────────────────────────
add("saudacao", "oi", "ola", "opa", "eai", "e ai", "bom dia", "boa tarde", "boa noite",
    "oii", "oie", "salve", "eae", "olá", "oi tudo bem", "oi bom dia", "bom diaa",
    "oi, tudo bem?", "hey", "oi td bem")
add("saudacao_giria", "mano", "bro", "fala ai", "e ai parceiro", "salve mano",
    "diva", "amiga", "oi diva", "fala mana", "eai bro")
add("despedida", "tchau", "ate logo", "flw", "falou", "ate mais", "vlw", "ate a proxima",
    "era so isso", "resolvido", "encerrar", "ate amanha", "valeu flw", "ok tchau")
add("agradecimento", "obrigado", "obrigada", "valeu", "obg", "vlw obg", "muito obrigada",
    "brigado", "obrigado mesmo", "obrigada pela ajuda")
add("elogio", "muito bom", "perfeito", "adorei", "amei", "parabens", "otimo atendimento",
    "voce e otimo", "que legal", "sensacional", "top demais", "arrasou", "que tudo",
    "adorei o atendimento", "voces sao otimos")
add("ofensa", "voce e burro", "que bot inutil", "idiota", "porcaria de bot",
    "nao presta pra nada", "voce e pessimo")

# ─────────────────────────────────────────────────────────────────────
# 2. QUALIDADE
# ─────────────────────────────────────────────────────────────────────
add("qualidade", "me fala sobre qualidade", "quero saber da qualidade", "sobre qualidade",
    "qualidade das pecas", "topico qualidade", "fala da qualidade")
add("qualidade", "as pecas sao originais?", "e original mesmo?", "e produto autentico?",
    "e falsificado?", "as roupas sao autenticas", "isso e original ou replica")
add("qualidade", "as pecas sao duraveis?", "quantas lavagens aguenta", "a roupa dura muito?",
    "e resistente?", "aguenta bastante lavagem", "dura por quanto tempo")
add("qualidade", "como e o controle de qualidade", "tem inspecao", "voces verificam as pecas",
    "como funciona a inspecao", "tem controle de qualidade")
add("qualidade", "veio com defeito", "minha peca veio com defeito", "peca com defeito",
    "tem defeito de fabricacao", "chegou com problema", "a costura ta com defeito")
add("qualidade", "tem certificacao", "tem selo", "quais certificados voces tem",
    "tem certificado de qualidade", "possui algum selo")

# ─────────────────────────────────────────────────────────────────────
# 3. PERSONALIZAÇÃO
# ─────────────────────────────────────────────────────────────────────
add("personalizacao", "quero personalizar", "sobre personalizacao", "fazem customizacao",
    "posso customizar a peca", "da pra personalizar", "quero customizar minha roupa")
add("personalizacao", "quais tipos de personalizacao", "opcoes de personalizacao",
    "que tipos de estampa tem", "quais formas de personalizar")
add("personalizacao", "como funciona o silk", "o que e silkscreen", "fazem serigrafia",
    "me explica o silk screen", "silk serve pra que")
add("personalizacao", "o que e dtf", "como funciona dtf", "fazem impressao digital",
    "estampa digital dtf", "me fala do dtf")
add("personalizacao", "fazem bordado", "como e o bordado", "quero bordar minha peca",
    "tem bordado?", "bordado na camiseta")
add("personalizacao", "fazem etiqueta personalizada", "etiqueta com minha marca",
    "posso por minha etiqueta", "etiqueta propria")
add("personalizacao", "fazem modelagem exclusiva", "criam modelagem propria", "modelagem sob medida")
add("personalizacao", "qual o prazo de personalizacao", "quanto tempo pra personalizar",
    "demora pra personalizar", "prazo pra estampar")
add("personalizacao", "como envio a arte", "qual formato da arte", "posso mandar png",
    "como mando o arquivo", "aceita arquivo cdr")

# ─────────────────────────────────────────────────────────────────────
# 4. CORES
# ─────────────────────────────────────────────────────────────────────
add("cores", "quais cores tem", "que cores voces tem", "paleta de cores", "cores disponiveis",
    "quais as cores", "tem quais cores")
add("cores", "quais cores em estoque", "cores pronta entrega", "cores basicas")
add("cores", "fazem tingimento", "posso pedir cor personalizada", "tingem sob demanda",
    "consigo uma cor especifica", "cor fora da paleta")
add("cores", "quantas cores na estampa", "limite de cores", "maximo de cores na estampa")
add("cores", "estampa em peca escura fica boa", "combina estampa com peca escura")

# ─────────────────────────────────────────────────────────────────────
# 5. TAMANHOS
# ─────────────────────────────────────────────────────────────────────
add("tamanhos", "quais tamanhos", "grade de tamanho", "que tamanhos tem", "tabela de tamanho",
    "quais os tamanhos disponiveis")
add("tamanhos", "tem tamanho adulto", "grade adulto", "tem tamanho gg", "tamanho m tem",
    "voces tem p m g gg")
add("tamanhos", "tem tamanho infantil", "roupa de crianca", "tamanho pra crianca",
    "fazem tamanho infantil")
add("tamanhos", "tem plus size", "tamanho plus", "voces fazem g1 g2 g3", "tem tamanho grande",
    "atendem plus size")
add("tamanhos", "tem tabela de medidas", "medidas em cm", "qual a medida do busto",
    "tabela de medidas em centimetros")

# ─────────────────────────────────────────────────────────────────────
# 6. QUANTIDADE MÍNIMA
# ─────────────────────────────────────────────────────────────────────
add("quantidade_minima", "qual a quantidade minima", "tem pedido minimo", "minimo de pecas",
    "qual o minimo pra pedir", "quantas pecas no minimo")
add("quantidade_minima", "minimo por peca", "minimo pra silk", "minimo pra bordado",
    "quantas pecas por cor no minimo", "minimo por cor")
add("quantidade_minima", "faco pedido de 1000 pecas", "pedido de alto volume", "atacado grande",
    "pedido grande de 500 pecas")
add("quantidade_minima", "quero poucas pecas", "pedido pequeno", "menos de 30 pecas",
    "da pra fazer so 5 pecas")

# ─────────────────────────────────────────────────────────────────────
# 7. SUSTENTABILIDADE
# ─────────────────────────────────────────────────────────────────────
add("sustentabilidade", "voces sao sustentaveis", "sobre sustentabilidade", "e ecologico",
    "se preocupam com meio ambiente", "praticas sustentaveis")
add("sustentabilidade", "aproveitam o tecido", "reduzem desperdicio", "encaixe de molde")
add("sustentabilidade", "usam algodao organico", "tem poliester reciclado", "material ecologico",
    "usam rpet")
add("sustentabilidade", "voces reciclam", "fazem reciclagem de tecido", "reciclam retalho")
add("sustentabilidade", "a tinta e toxica", "usam quimica nociva", "a tinta faz mal")
add("sustentabilidade", "as condicoes de trabalho sao boas", "tem trabalho escravo",
    "e trabalho digno")
add("sustentabilidade", "e vegano", "tem produto de origem animal", "e cruelty free",
    "usam couro animal")
add("sustentabilidade", "a embalagem e sustentavel", "embalagem reciclavel", "caixa reciclada")

# ─────────────────────────────────────────────────────────────────────
# 8. MANUTENÇÃO / CUIDADOS
# ─────────────────────────────────────────────────────────────────────
add("manutencao", "como cuido da peca", "cuidados com a roupa", "sobre manutencao",
    "como conservar a roupa")
add("manutencao", "como lavo a peca", "posso lavar na maquina", "como faco a lavagem",
    "pode lavar a mao", "lavar a peca")
add("manutencao", "posso passar ferro", "pode passar a ferro", "qual temperatura do ferro")
add("manutencao", "pode por na secadora", "posso secar na secadora", "secadora pode")
add("manutencao", "posso usar alvejante", "pode agua sanitaria", "pode qboa", "usar cloro")
add("manutencao", "como tiro mancha", "remover mancha de oleo", "mancha de comida")
add("manutencao", "como cuido do algodao", "algodao encolhe", "como lavar algodao")
add("manutencao", "como cuido da viscose", "viscose amassa", "como lavar viscose")
add("manutencao", "como cuido do poliester", "como lavar poliester")
add("manutencao", "como cuido do linho", "linho amassa muito", "como lavar linho")
add("manutencao", "como cuido do jeans", "jeans desbota", "como lavar jeans")
add("manutencao", "como cuido da la", "como lavar la", "cuidado com trico")
add("manutencao", "como cuido da malha", "malha estica", "malha encolhe")
add("manutencao", "como cuido do moletom", "moletom encolhe", "moletom desbota")
add("manutencao", "minha peca encolheu", "a roupa encolheu na lavagem", "encolheu tudo")
add("manutencao", "minha peca desbotou", "perdeu a cor", "a cor saiu na lavagem")

# ─────────────────────────────────────────────────────────────────────
# 9. PRODUÇÃO
# ─────────────────────────────────────────────────────────────────────
add("producao", "como e a producao", "processo produtivo", "como voces produzem",
    "como funciona a producao")
add("producao", "quais as etapas de producao", "fases da producao", "passos da producao",
    "fluxo de producao")
add("producao", "onde fica a fabrica", "onde produzem", "onde e produzido", "local da fabrica")
add("producao", "qual a capacidade produtiva", "quantas pecas por mes", "capacidade da fabrica")
add("producao", "que tecnologia usam", "quais maquinas tem", "usam automacao", "tem equipamento moderno")
add("producao", "quantos funcionarios tem", "sobre a equipe", "quantos colaboradores")
add("producao", "como e a modelagem", "fazem prova piloto", "tem ficha tecnica")
add("producao", "como e o corte e costura", "que tipo de costura", "maquina de corte")

# ─────────────────────────────────────────────────────────────────────
# 10. CATÁLOGO / PRODUTOS
# ─────────────────────────────────────────────────────────────────────
add("catalogo", "o que voces fazem", "quais produtos voces tem", "que tipo de produto fazem",
    "quais pecas voces produzem", "o que da pra fazer")
add("catalogo", "fazem camiseta", "voces fazem polo", "tem regata", "fazem baby look",
    "produzem oversized")
add("catalogo", "fazem moletom", "tem jaqueta", "produzem hoodie")
add("catalogo", "fazem calca", "tem calca jeans", "produzem legging", "fazem bermuda", "tem jogger")
add("catalogo", "fazem vestido", "tem vestido midi", "produzem vestido longo")
add("catalogo", "fazem uniforme", "produzem uniforme corporativo", "tem jaleco")
add("catalogo", "fazem roupa infantil", "tem roupa de crianca", "produzem moda infantil")
add("catalogo", "fazem calcado", "voces fazem sapato", "tem tenis", "fazem acessorio", "fazem bone")

# ─────────────────────────────────────────────────────────────────────
# 11. SUGESTÃO DE PRODUTO
# ─────────────────────────────────────────────────────────────────────
add("sugestao_produto", "me sugere uma peca", "o que voce indica", "me indica um produto",
    "qual peca voce recomenda")
add("sugestao_produto", "peca pra usar no dia a dia", "algo casual", "peca basica pro cotidiano")
add("sugestao_produto", "peca pra trabalhar", "algo corporativo", "roupa pro escritorio",
    "peca pra reuniao")
add("sugestao_produto", "peca pra academia", "roupa pra treino", "algo pra esporte",
    "roupa pra corrida")
add("sugestao_produto", "peca pra festa", "roupa pra casamento", "algo pra formatura",
    "peca pra evento")
add("sugestao_produto", "peca pra inverno", "roupa pra frio", "algo quentinho")
add("sugestao_produto", "peca pra verao", "roupa pra calor", "algo leve e fresco")
add("sugestao_produto", "qual uniforme voce indica", "sugestao de uniforme", "melhor uniforme")
add("sugestao_produto", "sugestao de presente", "presente pra namorada", "quero presentear alguem")

# ─────────────────────────────────────────────────────────────────────
# 12. TECIDOS
# ─────────────────────────────────────────────────────────────────────
add("tecidos", "quais tecidos voces tem", "sobre tecidos", "que tecido usam", "quais os tecidos",
    "lista de tecidos", "tecidos disponiveis")
add("tecidos", "qual a composicao do tecido", "porcentagem de algodao", "do que e feito o tecido")
add("tecidos", "de onde vem o tecido", "origem do tecido", "quem e o fornecedor de tecido")
add("tecidos", "tenho pele sensivel qual tecido", "sou alergico que tecido", "tecido pra dermatite")
add("tecidos", "trabalham com couro", "tem couro vegano", "fazem couro sintetico")
add("tecidos", "qual tecido pra calor", "tecido fresco pra verao", "tecido leve e respiravel")
add("tecidos", "qual tecido pra frio", "tecido quente pra inverno", "tecido grosso")
add("tecidos", "qual tecido resistente", "tecido duravel pra usar muito", "tecido do dia a dia")
add("tecidos", "qual tecido pra academia", "tecido que absorve suor", "tecido esportivo")
add("tecidos", "qual tecido formal", "tecido elegante", "tecido sofisticado pra alfaiataria")
add("tecidos", "quais cores de tecido em estoque", "cor do tecido disponivel")

# ─────────────────────────────────────────────────────────────────────
# 13. DISPONIBILIDADE / ESTOQUE / PRONTA ENTREGA
# ─────────────────────────────────────────────────────────────────────
add("disponibilidade", "tem material disponivel", "materia prima em estoque",
    "tem tecido em estoque", "tem algodao em estoque", "tem jeans em estoque")
add("disponibilidade", "quando repoe o estoque", "vai ter de novo quando", "quando volta o material")
add("disponibilidade", "tem pronta entrega", "tem peca pronta", "voces tem em estoque pra entrega")

# ─────────────────────────────────────────────────────────────────────
# 14. PRAZO
# ─────────────────────────────────────────────────────────────────────
add("prazo", "qual o prazo", "quanto tempo demora", "quando fica pronto", "previsao de prazo",
    "prazo de entrega da producao", "em quanto tempo fica pronto")
add("prazo", "qual o prazo padrao", "prazo comum", "prazo normal", "tempo medio de producao")
add("prazo", "prazo com personalizacao", "prazo com bordado", "prazo com silk", "prazo com dtf")
add("prazo", "tenho urgencia", "preciso urgente", "pra ontem", "prazo curto", "consigo rapido")
add("prazo", "prazo pra pedido grande", "prazo de lote grande", "prazo de 500 pecas")
add("prazo", "meu pedido atrasou", "passou do prazo", "ta atrasado", "estourou o prazo")

# ─────────────────────────────────────────────────────────────────────
# 15. COMBINADAS — prazo/preço com produto e quantidade
# ─────────────────────────────────────────────────────────────────────
for q in [50, 100, 200, 500]:
    for p in ["camisetas", "polos", "moletons"]:
        add("prazo_combinado", f"qual o prazo de {q} {p}", f"prazo de {q} {p}",
            f"quando fica pronto {q} {p}")
        add("preco_combinado", f"preco de {q} {p}", f"quanto custa {q} {p}",
            f"valor de {q} {p}", f"quanto fica {q} {p}")
add("prazo_combinado", "prazo camiseta bordada", "prazo polo com silk", "prazo moletom com dtf")
add("preco_combinado", "quanto custa com bordado", "quanto fica com silk", "preco da personalizacao")

# ─────────────────────────────────────────────────────────────────────
# 16. DESCONTO POR VOLUME
# ─────────────────────────────────────────────────────────────────────
add("desconto", "tem desconto por volume", "desconto pra atacado", "desconto progressivo",
    "quanto mais compro mais barato")

# ─────────────────────────────────────────────────────────────────────
# 17. COMBINADAS DE COMPATIBILIDADE (tecido em produto, cor em tecido, etc.)
# ─────────────────────────────────────────────────────────────────────
for tec in ["algodao", "viscose", "linho", "jeans"]:
    add("compat_tecido_produto", f"posso fazer camiseta de {tec}", f"da pra usar {tec} em camiseta",
        f"camiseta de {tec} fica bom", f"{tec} serve pra camiseta")
add("compat_tecido_produto", "quais tecidos pra camiseta", "quais tecidos pra polo",
    "que tecido posso usar em moletom", "quais tecidos servem pra vestido")
add("compat_pers_tecido", "posso fazer bordado em jeans", "da pra bordar viscose",
    "silk em algodao funciona", "posso estampar no linho")
add("compat_cor_tecido", "tem algodao vermelho", "moletom preto disponivel",
    "viscose rosa tem", "algodao na cor marinho")
add("compat_cor_tecido", "quais cores em algodao", "cores disponiveis em viscose",
    "que cores tem no moletom")
add("compat_tamanho_produto", "tem camiseta plus size", "polo plus size tem",
    "moletom em plus", "vestido plus size")
add("gramatura", "qual gramatura pra camiseta", "qual peso de tecido usar",
    "tecido grosso ou fino pra moletom", "quantas gramas o tecido")

# ─────────────────────────────────────────────────────────────────────
# 18. VIABILIDADE DE PRODUÇÃO
# ─────────────────────────────────────────────────────────────────────
add("viabilidade", "consigo 500 camisetas em 10 dias", "da pra produzir 1000 pecas em 20 dias",
    "conseguem fazer 300 moletons em 15 dias", "e viavel 200 polos em 5 dias")
add("viabilidade", "qual a capacidade tecnica", "voces conseguem produzir isso",
    "da pra produzir esse volume")

# ─────────────────────────────────────────────────────────────────────
# 19. CONSUMO DE TECIDO
# ─────────────────────────────────────────────────────────────────────
add("consumo", "quantos metros pra 100 camisetas", "quantos metros de tecido pra 50 polos",
    "metros de tecido pra 200 moletons")

# ─────────────────────────────────────────────────────────────────────
# 20. CRUD DE PEDIDOS — status, alterar, cancelar, registrar
# ─────────────────────────────────────────────────────────────────────
add("pedido_status", "qual o status do meu pedido", "onde esta meu pedido", "andamento do pedido",
    "em que etapa ta meu pedido", "quero acompanhar meu pedido", "rastrear pedido")
add("pedido_status", "status do pedido FF-2024-0001", "meu pedido FF-2024-0002",
    "cade o pedido FF-2024-0003")
add("pedido_alterar", "quero alterar meu pedido", "mudar o pedido", "preciso trocar tamanho do pedido",
    "alterar a cor do pedido", "modificar meu pedido")
add("pedido_cancelar", "quero cancelar o pedido", "cancelar meu pedido", "desisti do pedido",
    "quero cancelamento", "cancela ai")
add("pedido_registrar", "quero fazer um pedido", "registrar um pedido", "fazer pedido novo",
    "quero registrar pedido", "novo pedido", "abrir um pedido", "cadastrar pedido")

# ─────────────────────────────────────────────────────────────────────
# 21. B2B / EMPRESAS
# ─────────────────────────────────────────────────────────────────────
add("b2b", "atendem empresa", "fazem atendimento b2b", "atendem pessoa juridica",
    "vendem pra empresa")
add("b2b", "fazem private label", "produzem pra minha marca", "white label",
    "peca com minha marca")
add("b2b", "quero revender", "sou revendedor", "compro pra revender", "atendem atacadista")
add("b2b", "fazem uniforme escolar", "uniforme de escola", "farda escolar", "camiseta pra escola")
add("b2b", "uniforme pra empresa com logo e prazo", "uniforme empresa preco e prazo")

# ─────────────────────────────────────────────────────────────────────
# 22. META DO BOT
# ─────────────────────────────────────────────────────────────────────
add("bot_meta", "voce e um robo", "voce e ia", "voce e humano", "qual seu nome",
    "voce e um bot", "to falando com uma pessoa")
add("bot_meta", "quero falar com atendente", "quero um humano", "me passa pra uma pessoa",
    "falar com alguem de verdade", "quero atendente humano")
add("bot_meta", "qual o horario de atendimento", "que horas voces atendem", "horario de funcionamento")

# ─────────────────────────────────────────────────────────────────────
# 23. OUTROS SETORES (encaminhamento) — NÃO é produção
# ─────────────────────────────────────────────────────────────────────
add("setor_vendas", "quanto custa uma camiseta", "qual o preco", "quero comprar", "qual o valor",
    "quanto sai uma polo", "formas de pagamento", "aceita cartao", "parcela em quantas vezes")
add("setor_logistica", "voces entregam", "qual o frete", "como e a entrega", "fazem envio",
    "entregam em todo brasil", "qual transportadora", "quanto custa o frete", "codigo de rastreio")
add("setor_devolucao", "quero devolver", "como faco a troca", "veio tamanho errado quero trocar",
    "politica de devolucao", "quero meu dinheiro de volta", "como devolvo a peca")
add("setor_compras", "quero ser fornecedor", "como vendo pra voces", "setor de compras",
    "quero fornecer tecido")
add("setor_almoxarifado", "controle de estoque interno", "almoxarifado", "estocagem de material")

# ─────────────────────────────────────────────────────────────────────
# 24. FALLBACK ESPERADO — gibberish / totalmente fora
# ─────────────────────────────────────────────────────────────────────
add("fallback_ok", "asdfgh", "kkkk", "xpto qwerty", "??????", "aaaaa", "123xyz",
    "lorem ipsum", "blablabla", "test test", ".....")
add("fallback_ok", "qual a capital da franca", "me conta uma piada", "que horas sao",
    "qual o resultado do jogo", "vai chover amanha")

# ─────────────────────────────────────────────────────────────────────
# EXPANSÃO PROGRAMÁTICA — pra chegar em ~1000 com variações realistas
# ─────────────────────────────────────────────────────────────────────

# 24a. Catálogo por produto — "voces fazem X?" / "tem X?"
gatilhos_cat = ["voces fazem {p}", "fazem {p}", "tem {p}", "produzem {p}", "vende {p}",
                "trabalham com {p}", "da pra fazer {p}", "tem {p} ai"]
for p in PRODUTOS:
    for g in gatilhos_cat:
        add("catalogo", g.format(p=p))

# 24b. Tecido em produto — compatibilidade explícita
gatilhos_compat = ["posso fazer {p} de {t}", "da pra fazer {p} em {t}", "{p} de {t} fica bom",
                   "{t} serve pra {p}", "combina {t} com {p}", "recomenda {t} pra {p}"]
for p in ["camiseta", "polo", "moletom", "vestido midi", "calca"]:
    for t in ["algodao", "viscose", "linho", "jeans", "suplex"]:
        g = random.choice(gatilhos_compat)
        add("compat_tecido_produto", g.format(p=p, t=t))

# 24c. Cor em tecido — disponibilidade
for t in ["algodao", "viscose", "moletom flanelado", "suplex", "linho"]:
    for c in ["preto", "branco", "vermelho", "marinho", "rosa", "verde militar"]:
        g = random.choice(["tem {t} {c}", "{t} na cor {c}", "tem {t} na cor {c}",
                           "{c} disponivel em {t}"])
        add("compat_cor_tecido", g.format(t=t, c=c))

# 24d. Preço combinado (out-of-sector estimate) e prazo combinado — mais volume
for q in QTDS:
    for p in ["camisetas", "polos", "moletons", "regatas", "calcas", "vestidos"]:
        add("preco_combinado", random.choice([
            f"quanto custa {q} {p}", f"preco de {q} {p}", f"valor de {q} {p}",
            f"quanto sai {q} {p}", f"orcamento de {q} {p}"]))
        add("prazo_combinado", random.choice([
            f"prazo de {q} {p}", f"em quanto tempo {q} {p}", f"quando fica pronto {q} {p}",
            f"qual prazo pra {q} {p}"]))

# 24e. Personalização em produto — prazo/tipo
for pers in PERSONALIZACOES:
    add("personalizacao", random.choice([
        f"como funciona {pers}", f"fazem {pers}", f"quero {pers} na peca",
        f"me explica {pers}"]))
    add("prazo", f"qual o prazo com {pers}")

# 24f. Sugestão por ocasião — mais variações
ocasioes = {
    "casual": ["peca pro dia a dia", "algo casual", "roupa casual", "peca basica"],
    "trabalho": ["roupa pro trabalho", "peca corporativa", "algo pro escritorio", "roupa de reuniao"],
    "esporte": ["roupa de academia", "peca pra treino", "algo pra esporte", "roupa pra corrida"],
    "festa": ["roupa de festa", "peca pra evento", "algo pra casamento", "roupa de formatura"],
    "inverno": ["peca pra frio", "roupa de inverno", "algo quentinho", "peca pra epoca fria"],
    "verao": ["roupa pra calor", "peca de verao", "algo fresquinho", "peca leve pro verao"],
}
for _, frases in ocasioes.items():
    for f in frases:
        add("sugestao_produto", f)

# 24g. Cuidados por tecido — mais formas
mapa_cuidado = {
    "algodao": "manutencao", "viscose": "manutencao", "linho": "manutencao",
    "jeans": "manutencao", "moletom": "manutencao", "malha": "manutencao", "la": "manutencao",
    "poliester": "manutencao",
}
for tec, cat in mapa_cuidado.items():
    for g in [f"como lavo {tec}", f"como cuido de {tec}", f"posso lavar {tec} na maquina",
              f"{tec} pode passar ferro", f"cuidado com {tec}"]:
        add(cat, g)

# 24h. Prazo — muitas formas comuns
for g in ["qual o prazo de producao", "quanto tempo pra ficar pronto", "demora quanto tempo",
          "prazo medio de entrega da producao", "em quantos dias fica pronto",
          "quando meu pedido fica pronto", "prazo de fabricacao", "tempo de producao",
          "quanto tempo leva pra produzir", "prazo pra fazer"]:
    add("prazo", g)

# 24i. Preço puro (vendas) — muitas formas
for g in ["qual o preco", "quanto custa", "qual o valor", "quanto sai", "me passa o preco",
          "qual o preco da camiseta", "quanto ta a polo", "valor unitario", "preco por peca",
          "quanto voces cobram", "tabela de precos"]:
    add("setor_vendas", g)

# 24j. Entrega/frete (logistica) — muitas formas
for g in ["qual o frete", "como funciona a entrega", "voces entregam onde", "prazo de entrega",
          "quanto custa o envio", "entregam na minha cidade", "fazem entrega", "tem frete gratis",
          "como rastrear a entrega", "qual transportadora usam"]:
    add("setor_logistica", g)

# 24k. Saudações + pergunta (combinadas comuns)
for prod_q in ["oi quero saber dos tecidos", "boa tarde queria uma camiseta",
               "ola voces fazem moletom", "oi qual o prazo", "bom dia quero personalizar",
               "oi tudo bem quero fazer um pedido", "ola quais cores tem"]:
    add("saudacao_composta", prod_q)


# ─────────────────────────────────────────────────────────────────────
# Salvar
# ─────────────────────────────────────────────────────────────────────
# Dedup preservando ordem
vistos = set()
final = []
for cat, txt in perguntas:
    chave = txt.strip().lower()
    if chave and chave not in vistos:
        vistos.add(chave)
        final.append((cat, txt))

out = os.path.join(os.path.dirname(__file__), "perguntas.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["categoria", "pergunta"])
    w.writerows(final)

print(f"Geradas {len(final)} perguntas unicas.")
from collections import Counter
c = Counter(cat for cat, _ in final)
for cat, n in c.most_common():
    print(f"  {n:4d}  {cat}")
