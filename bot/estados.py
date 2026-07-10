"""
estados.py — O MAPA DE ESTADOS da conversa.

A ideia (Semana 3, "a memória do bot"): além de guardar os dados, o bot precisa
saber DUAS coisas a cada momento da conversa:

  1) ESTADO DA CONVERSA  -> ONDE estamos no diálogo
     (conversa nova? esperando um menu? coletando um pedido?)

  2) OBJETIVO DO USUÁRIO -> O QUE a pessoa está tentando fazer
     (bate-papo? tirar dúvida? simular um pedido? mexer num pedido?)

Este arquivo só LÊ a sessão e devolve esses dois "rótulos". Ele NÃO muda nada —
quem guarda os rótulos na sessão é o contexto.py. Deixamos tudo aqui, junto e
nomeado, pra ficar fácil de entender e de mostrar o mapa pro professor.
"""

# ═══════════════════════ EIXO 1: ESTADO DA CONVERSA ═══════════════════════
# Os nomes possíveis de "onde estamos". São poucos de propósito (simples).
OCIOSO           = "OCIOSO"            # conversa nova ou recém-encerrada (deu "tchau")
AGUARDANDO_NOME  = "AGUARDANDO_NOME"   # o bot perguntou o nome e espera o cliente dizer
EM_ASSUNTO       = "EM_ASSUNTO"        # conversando sobre algum tópico
AGUARDANDO_OPCAO = "AGUARDANDO_OPCAO"  # o bot mostrou um menu e espera a escolha
AGUARDANDO_ID    = "AGUARDANDO_ID"     # o bot pediu o número do pedido
COLETANDO_PEDIDO = "COLETANDO_PEDIDO"  # o bot está montando um pedido novo


def estado_da_conversa(sessao):
    """
    Diz ONDE a conversa está agora, olhando os sinais que a sessão JÁ guarda.

    A ordem importa: testamos do mais específico (no meio de uma sub-tarefa)
    para o mais geral.
    """
    if sessao.get("aguardando_nome"):
        return AGUARDANDO_NOME           # bot pediu o nome no início e espera a resposta
    if not sessao.get("ativa"):
        return OCIOSO                    # ninguém falou ainda (ou acabou de se despedir)
    if sessao.get("registro_pedido") is not None:
        return COLETANDO_PEDIDO          # estamos perguntando os dados de um pedido novo
    if sessao.get("aguardando_id"):
        return AGUARDANDO_ID             # pedimos o número do pedido e esperamos ele
    if sessao.get("aguardando_opcao"):
        return AGUARDANDO_OPCAO          # mostramos um menu e esperamos a escolha
    return EM_ASSUNTO                    # conversa ativa, sem sub-tarefa aberta


# ═══════════════════════ EIXO 2: OBJETIVO DO USUÁRIO ═══════════════════════
# Agrupamos as ~147 intenções em poucas METAS. Assim o bot entende a "intenção
# grande" por trás da conversa, não só a frase do momento.

# Bate-papo: cumprimentar, agradecer, elogiar, reclamar, perguntar sobre o bot.
_CONVERSA_SOCIAL = {
    "saudacao", "saudacao_girias1", "saudacao_girias2", "despedida",
    "agradecimento_continuo", "elogios1", "elogios2", "ofensas", "sobre_o_bot",
}

# Mexer num pedido específico (é o nosso CRUD de pedidos).
_GERIR_PEDIDO = {
    "registrar_pedido", "status_pedido", "alterar_pedido_especifico",
    "cancelar_pedido", "alterar_pedido", "etapas_pedido",
    "etapa_consulta", "acompanhamento",
}

# Estimar/planejar um pedido: prazo, viabilidade, consumo de tecido e preço
# INDICATIVO. NÃO é "orçamento" fechado — preço e fechamento são de VENDAS; a
# produção só dá a estimativa. Por isso o nome é SIMULAR_PEDIDO (e não orçamento).
# Obs: os "combinado_" de COMPATIBILIDADE (cor em tecido, tamanho em produto...)
# NÃO entram aqui — eles são dúvida, então caem no objetivo padrão TIRAR_DUVIDA.
_SIMULAR_PEDIDO = {
    "combinado_preco_qtd_produto", "combinado_preco_personalizacao",
    "combinado_prazo_qtd_produto", "combinado_prazo_personalizacao_produto",
    "combinado_desconto_volume", "viabilidade_producao", "consumo_tecido",
    "combinado_pedido_completo", "combinado_b2b_uniforme_completo",
}

# Nomes possíveis de objetivo:
CONVERSA_SOCIAL = "CONVERSA_SOCIAL"
GERIR_PEDIDO    = "GERIR_PEDIDO"
SIMULAR_PEDIDO  = "SIMULAR_PEDIDO"
IR_OUTRO_SETOR  = "IR_OUTRO_SETOR"
TIRAR_DUVIDA    = "TIRAR_DUVIDA"
INDEFINIDO      = "INDEFINIDO"


def objetivo_do_usuario(intencao):
    """
    Diz O QUE o usuário quer, traduzindo a intenção fina (ex: 'cores_basicas')
    para uma meta grande (ex: 'TIRAR_DUVIDA').
    """
    if intencao in _CONVERSA_SOCIAL:
        return CONVERSA_SOCIAL
    if intencao in _GERIR_PEDIDO:
        return GERIR_PEDIDO
    if intencao in _SIMULAR_PEDIDO:
        return SIMULAR_PEDIDO
    if intencao.startswith("setor_"):     # setor_vendas, setor_logistica, etc.
        return IR_OUTRO_SETOR
    if intencao == "fallback":
        return INDEFINIDO                 # o bot não entendeu o que a pessoa quis
    # Todo o resto (qualidade, tecidos, produção, cuidados...) é tirar dúvida.
    return TIRAR_DUVIDA
