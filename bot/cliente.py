"""
cliente.py — Nome do cliente + personalização das respostas.

Por quê: o professor quer que as interações sejam PERSONALIZADAS desde o início.
Então, logo no comecinho da conversa, o bot pergunta o nome, GUARDA na sessão
(é a "memória" da Semana 3) e passa a chamar o cliente pelo nome nas respostas.

Aqui ficam 3 coisinhas, bem separadas:
  - primeiro_nome()  -> pega só o 1º nome, bonitinho
  - tratar_nome()    -> cuida de PERGUNTAR e GUARDAR o nome no início
  - personalizar()   -> coloca o nome na frente da resposta do bot
"""
import re

from bot.normalizar import normalizar


def primeiro_nome(nome):
    """Pega só o primeiro nome, com inicial maiúscula. 'maria silva' -> 'Maria'."""
    if not nome:
        return ""
    return nome.strip().split()[0].capitalize()


def _limpar_nome(mensagem):
    """
    Limpa o que o cliente digitou como nome. Tira introduções comuns
    ('meu nome é', 'me chamo', 'sou a/o') e deixa só o nome em si.
    """
    t = mensagem.strip()
    t = re.sub(
        r'(?i)^\s*(meu nome (é|e)|me chamo|pode me chamar de|sou [oa]?|eu sou [oa]?)\s+',
        '', t,
    )
    return t.strip(" .,!?").title()


# Sinais de que o texto é uma PERGUNTA/PEDIDO, não um nome de pessoa. Se a gente
# pediu o nome e vem uma dessas, NÃO guardamos como nome (senão "personalização"
# virava "Prazer, Personalização!" e "gostaria de..." virava "Gostaria").
_PERGUNTA = re.compile(
    r'\?|\b(quero|queria|gostaria|desejo|qual|quais|quanto|quantos|quantas|como|'
    r'quando|onde|cade|tem|temos|voces|vcs|fazem|faz|fazer|preciso|pode|sobre|'
    r'me|informa|mostra|explica|ajuda)\b'
)
# Temas do bot (palavra inteira) — nome de pessoa não é uma dessas.
_TEMA = re.compile(
    r'\b(personaliza\w*|customiza\w*|camisa\w*|camiseta\w*|moleto\w*|calca\w*|'
    r'polos?|vestido\w*|uniforme\w*|jaqueta\w*|legging\w*|bermuda\w*|regata\w*|'
    r'jaleco\w*|tecido\w*|algodao|viscose|linho|jeans|suplex|'
    r'prazo\w*|preco\w*|valor\w*|orcamento\w*|desconto\w*|bordado\w*|silk\w*|'
    r'serigrafia|estampa\w*|tamanho\w*|entrega\w*|frete\w*|pedido\w*|'
    r'catalogo\w*|produto\w*|gramatura\w*|sustentabilidade|qualidade|'
    r'revenda\w*|atacado|manutencao|lavar|encolh\w*)\b'
)


def _parece_nome(nome_limpo):
    """True se o texto parece um nome de pessoa (e não uma pergunta/tema do bot)."""
    t = normalizar(nome_limpo).strip()
    if not t:
        return False
    if len(t.split()) > 4:          # nome tem no máximo ~4 palavras
        return False
    if _PERGUNTA.search(t) or _TEMA.search(t):
        return False
    return True


def tratar_nome(mensagem, sessao):
    """
    Cuida da CAPTURA do nome no começo da conversa.

    Retorna:
      - uma resposta (str) SE ainda estamos tratando do nome (perguntando ou
        confirmando) — nesse caso o fluxo normal do bot NÃO roda neste turno;
      - None se o nome já é conhecido OU se a mensagem é uma pergunta (aí o fluxo
        normal continua e responde a pergunta em vez de virar nome).
    """
    # Já sabemos o nome -> não interfere, segue o fluxo normal do bot.
    if sessao.get("nome_cliente"):
        return None

    # Já perguntamos e estamos esperando -> a mensagem atual DEVERIA ser o nome.
    if sessao.get("aguardando_nome"):
        nome = _limpar_nome(mensagem)
        if not _parece_nome(nome):
            # Não era um nome, era uma pergunta ("personalização", "quero X...").
            # Para de esperar o nome e deixa o pipeline responder normalmente.
            sessao["aguardando_nome"] = False
            sessao["ativa"] = True
            return None
        sessao["nome_cliente"] = nome
        sessao["aguardando_nome"] = False
        sessao["ativa"] = True
        return (
            f"Prazer, {primeiro_nome(nome)}! Sou o assistente do setor de produção "
            "da Fashion Flow. Em que posso te ajudar?"
        )

    # Conversa já ativa (a pessoa já mandou pergunta sem dar nome) -> não fica
    # pedindo o nome de novo; segue respondendo.
    if sessao.get("ativa"):
        return None

    # Primeira interação da conversa -> pede o nome.
    sessao["aguardando_nome"] = True
    return (
        "Olá! Eu sou o assistente do setor de produção da Fashion Flow. "
        "Antes de começar, como posso te chamar?"
    )


def personalizar(resposta, sessao):
    """
    Coloca o nome do cliente na frente da resposta (ex: 'Maria, ...'), pra deixar
    o atendimento pessoal. Não duplica se a resposta já cita o nome.
    """
    nome = sessao.get("nome_cliente")
    if not nome:
        return resposta
    pn = primeiro_nome(nome)
    # se a resposta já tem o nome (ex: confirmação de pedido), não repete
    if not pn or normalizar(pn) in normalizar(resposta):
        return resposta
    return f"{pn}, {resposta}"
