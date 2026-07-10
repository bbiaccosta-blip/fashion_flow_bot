"""
Extração de slots a partir da mensagem do usuário.

REGRAS DE OURO:
- Função pura: NÃO toca em sessão. Só lê a mensagem e retorna slots.
- Quem mescla com contexto é bot/contexto.py:merge_com_contexto.
- Quando o bot está aguardando opção de menu, o extractor não extrai
  quantidade (evita o Crítico 3: número do menu virar quantidade).
"""
import re

from bot.normalizar import normalizar


# ── Unidades que podem acompanhar uma quantidade ───────────────────
# Inclui plurais e produtos conhecidos. Unidade é OBRIGATÓRIA — assim
# evita pegar números soltos (anos de pedido, "em 100 dias", etc).
UNIDADES_QTD = (
    r'pecas?|camisetas?|polos?|moletons?|moletom|uniformes?|vestidos?|'
    r'calcas?|calças?|bermudas?|regatas?|leggings?|joggers?|'
    r'jaquetas?|jalecos?|baby looks?|oversized|unidades?|\bun\b|pcs|'
    r'camisas?|jeans|aventai?s|aventais?'
)

# ── Produtos: chave → id_produto ───────────────────────────────────
# Ordem importa: chaves mais específicas vêm primeiro pra não serem
# engolidas por chaves curtas (ex: "camiseta premium" antes de "camiseta").
PRODUTOS = [
    # "camisa(s)/camiseta(s) premium" e "premiun" (typo) = a camiseta premium.
    # Vêm PRIMEIRO pra vencer o "camisas" genérico no empate de posição (senão
    # "camisas premium" caía em camiseta_basica e perdia o detalhe da premium).
    ("camisetas? premium", "camiseta_premium"),
    ("camisas? premium", "camiseta_premium"),
    ("camisetas? premiun", "camiseta_premium"),
    ("camisas? premiun", "camiseta_premium"),
    # mais específicos primeiro
    ("camiseta premium", "camiseta_premium"),
    ("camiseta basica", "camiseta_basica"),
    ("camiseta de time", "camiseta_basica"),
    ("baby look", "baby_look"),
    ("calca jeans", "calca_jeans"),
    ("calca alfaiataria", "calca_alfaiataria"),
    ("vestido midi", "vestido_midi"),
    ("vestido longo", "vestido_longo"),
    ("uniforme polo", "uniforme_polo"),
    ("uniforme jaleco", "uniforme_jaleco"),
    # genéricos (já cobrem plurais por causa do \w*)
    ("camisetas?", "camiseta_basica"),
    ("camisas?", "camiseta_basica"),
    ("polos?", "polo"),
    ("moletons?", "moletom"),
    ("moletom", "moletom"),
    ("jaquetas?", "jaqueta"),
    ("calcas?", "calca_jeans"),
    ("calças?", "calca_jeans"),
    ("leggings?", "legging"),
    ("bermudas?", "bermuda"),
    ("regatas?", "regata"),
    ("vestidos?", "vestido_midi"),
    ("joggers?", "jogger"),
    ("uniformes?", "uniforme_polo"),
    ("jalecos?", "uniforme_jaleco"),
    ("oversized", "oversized"),
    ("premium", "camiseta_premium"),   # "premium" sozinho = a camiseta premium
    ("premiun", "camiseta_premium"),   # typos comuns
    ("premim", "camiseta_premium"),
]

# ── Personalizações ────────────────────────────────────────────────
PERSONALIZACOES = [
    (r"silkscreen", "silkscreen"),
    (r"silk screen", "silkscreen"),
    (r"\bsilk\b", "silkscreen"),
    (r"serigrafia", "silkscreen"),
    (r"\bdtf\b", "dtf"),
    (r"impressao digital", "dtf"),
    (r"bordad[oa]s?", "bordado"),
    (r"\bbordar\b", "bordado"),
    (r"etiquetas?", "etiqueta"),
]

# ── Tecidos ────────────────────────────────────────────────────────
TECIDOS = [
    (r"algodao pima", "algodao_pima"),
    (r"algodao penteado", "algodao_penteado"),
    (r"algodao basico", "algodao_basico"),
    (r"\bdry.?fit\b", "dry_fit"),
    (r"malha mista", "malha_mista"),
    (r"moletom flanelado", "moletom_flanelado"),
    (r"moletom peluciado", "moletom_peluciado"),
    (r"\bviscose\b", "viscose"),
    (r"\blinho\b", "linho"),
    (r"\bsuplex\b", "suplex"),
    (r"\bjeans\b", "jeans"),
    (r"alfaiataria", "alfaiataria"),
    (r"\bla\b", "la"),
    (r"\btencel\b", "tencel"),
    (r"\balgodao\b", "algodao_basico"),
]

CORES = [
    ("preto", "preto"), ("preta", "preto"),
    ("branco", "branco"), ("branca", "branco"),
    ("cinza mescla", "cinza_mescla"),
    ("cinza chumbo", "cinza_chumbo"),
    ("cinza", "cinza_mescla"),
    ("marinho", "marinho"),
    ("royal", "royal"),
    ("vermelho", "vermelho"), ("vermelha", "vermelho"),
    ("vinho", "vinho"),
    ("verde militar", "verde_militar"),
    ("verde bandeira", "verde_bandeira"),
    ("amarelo", "amarelo"), ("amarela", "amarelo"),
    ("rosa", "rosa"),
    ("azul", "royal"),
]

USOS = [
    ("verao", "verao"),
    ("inverno intenso", "inverno_intenso"),
    ("inverno leve", "inverno_leve"),
    ("inverno", "inverno"),
    ("corporativo", "corporativo"),
    ("esporte", "esporte"),
    ("casual", "casual"),
    ("dia a dia", "dia_a_dia"),
    ("formal", "formal"),
    ("meia estacao", "meia_estacao"),
]


def _primeiro_match(padroes, texto):
    """
    Roda cada padrão na ordem e retorna (valor, pos_inicio) do primeiro match.
    Se nenhum bate, retorna (None, -1).
    """
    melhor_pos = None
    melhor_valor = None
    for padrao, valor in padroes:
        m = re.search(padrao, texto)
        if m:
            if melhor_pos is None or m.start() < melhor_pos:
                melhor_pos = m.start()
                melhor_valor = valor
    return melhor_valor


def _produto_mais_a_esquerda(texto):
    """
    Pega o produto que aparece PRIMEIRO na frase (mais à esquerda).
    Conserta o MÉDIO 18 (legging vence regata por ordem do dict).
    """
    melhor_pos = None
    melhor_valor = None
    for padrao, valor in PRODUTOS:
        # \b força borda de palavra; cobre singular e plural pela presença de s?
        m = re.search(rf"\b{padrao}\b", texto)
        if m:
            if melhor_pos is None or m.start() < melhor_pos:
                melhor_pos = m.start()
                melhor_valor = valor
    return melhor_valor


def extrair_slots(mensagem, em_menu=False):
    """
    Extrai slots da mensagem. NÃO toca em sessão (função pura).

    Parâmetros:
        mensagem: texto bruto do usuário
        em_menu: True quando o bot está aguardando uma resposta de menu.
                 Quando True, não extrai quantidade (evita Crítico 3).

    Retorna: dict com os slots extraídos NESTE turno.
    """
    if em_menu:
        # No meio de um menu, a entrada é a escolha do usuário.
        # O responder/classifier cuida da seleção. Não confundimos slots.
        return {}

    t = normalizar(mensagem)
    slots = {}

    # ── Passo 1: número do pedido (FF-AAAA-NNNN) ────────────────
    # Extraído PRIMEIRO. Removemos o trecho da string pra evitar que
    # 2024 ou outro número do código vire "quantidade" (CRÍTICO 2).
    match_pedido = re.search(r'FF-\d{4}-\d{4}', mensagem, re.IGNORECASE)
    if match_pedido:
        slots["numero_pedido"] = match_pedido.group(0).upper()
        # remove o número do pedido do texto pra próximas buscas
        t = re.sub(r'ff-\d{4}-\d{4}', ' ', t)

    # ── Passo 2: prazo desejado ──────────────────────────────────
    # Extraído antes de quantidade pra evitar conflito (ALTO 8).
    match_prazo = re.search(
        r'(?:em|ate|prazo de)\s*(\d+)\s*dias?', t
    )
    if match_prazo:
        slots["prazo_desejado"] = int(match_prazo.group(1))
        # remove o trecho do prazo pra próximas buscas
        t = t[:match_prazo.start()] + ' ' + t[match_prazo.end():]

    # ── Passo 3: quantidade (unidade obrigatória) ───────────────
    # CRÍTICO 2: agora exige unidade explícita — não pega número solto.
    match_qtd = re.search(rf'\b(\d+)\s*({UNIDADES_QTD})\b', t)
    if match_qtd:
        slots["quantidade"] = int(match_qtd.group(1))

    # ── Passo 4: produto (mais à esquerda) ──────────────────────
    produto = _produto_mais_a_esquerda(t)
    if produto:
        slots["produto"] = produto

    # ── Passo 5: negação de personalização (CRÍTICO 22) ─────────
    # "sem bordado", "sem silk", "nenhuma personalização" → nenhuma
    neg_pers = re.search(
        r'(?:sem|nao quero|sem nenhuma?)\s+'
        r'(bordad[oa]s?|silk\w*|serigrafia|dtf|estamp\w*|etiqueta|personali\w+)',
        t
    )
    if neg_pers:
        slots["personalizacao"] = "nenhuma"
    else:
        # ── Passo 5b: personalização normal ─────────────────────
        # Pega a primeira (mais à esquerda) — se houver mais de uma,
        # o classifier/responder cuida disso depois.
        valor = _primeiro_match(PERSONALIZACOES, t)
        if valor:
            slots["personalizacao"] = valor

    # ── Passo 6: tecido ──────────────────────────────────────────
    valor = _primeiro_match(TECIDOS, t)
    if valor:
        slots["tecido"] = valor

    # ── Passo 7: cor (aceita plural: "pretas", "brancos", "vermelhos") ──
    for chave, valor in CORES:
        if re.search(rf"\b{chave}s?\b", t):
            slots["cor"] = valor
            break

    # ── Passo 8: grade/tamanho (com prefixo obrigatório p/ letras curtas) ─
    if re.search(r'plus.?size|plus|g1|g2|g3|g4', t):
        slots["grade"] = "plus_size"
    elif re.search(r'infantil|crianca|kids', t):
        slots["grade"] = "infantil"
    elif re.search(r'(?:tamanho|grade)\s+(?:pp|p|m|g|gg|xgg)\b', t):
        # MÉDIO 16: só conta "M" como tamanho se vier após "tamanho/grade"
        slots["grade"] = "adulto"

    # ── Passo 9: uso/ocasião ─────────────────────────────────────
    for chave, valor in USOS:
        if re.search(rf"\b{chave}\b", t):
            slots["uso"] = valor
            break

    # ── Passo 10: urgência ───────────────────────────────────────
    if re.search(r'urgente|pra ontem|com pressa|preciso rapido|prazo curto|adiantar', t):
        slots["urgente"] = True

    # ── Passo 11: metragem ───────────────────────────────────────
    match_metros = re.search(r'(\d+[\.,]?\d*)\s*(metros?|m\b|m2|m²)', t)
    if match_metros:
        slots["metragem"] = float(match_metros.group(1).replace(",", "."))

    return slots
