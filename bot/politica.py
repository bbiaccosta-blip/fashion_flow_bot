"""
Política conversacional leve.

A ideia é separar uma decisão de diálogo que não pertence ao classificador puro:
quando o bot abriu menu, mas o cliente claramente mudou de assunto em linguagem
natural, o menu não deve sequestrar o próximo turno.
"""
import re

from bot.normalizar import normalizar

INTENCOES_ORCAMENTO = {
    "combinado_preco_qtd_produto",
    "combinado_prazo_qtd_produto",
    "combinado_prazo_personalizacao_produto",
    "combinado_preco_personalizacao",
    "combinado_desconto_volume",
    "viabilidade_producao",
    "consumo_tecido",
}

SLOTS_ORCAMENTO = {"produto", "quantidade", "personalizacao", "prazo_desejado", "urgente"}
SLOTS_ATRIBUTO_PRODUTO = {"produto", "cor", "grade"}
SLOTS_COMPATIBILIDADE = {"produto", "tecido", "personalizacao"}


def _parece_opcao_menu(texto):
    t = normalizar(texto).strip()
    if re.fullmatch(r'\d+', t):
        return True
    return bool(re.search(
        r'\b(opcao|opção|numero|número)\s*\d+\b|'
        r'\b(primeira|segunda|terceira|quarta|quinta|sexta|setima|sétima|oitava)\b',
        t
    ))


def _pede_lista_opcoes(texto):
    t = normalizar(texto)
    return bool(re.search(
        r'\b(menu|opcoes|opções|quais|lista|mostra|me ajuda|nao sei|não sei)\b',
        t
    ))


def limpar_menu_se_mudou_assunto(mensagem, sessao):
    """
    Fecha menu pendente quando o cliente respondeu em linguagem natural.

    Sem isso, qualquer pergunta depois de um menu entra como `selecao_opcao` e o
    bot tenta encaixar a frase no menu antigo antes de ouvir a intenção real.
    """
    if not sessao or not sessao.get("aguardando_opcao"):
        return False
    if _parece_opcao_menu(mensagem) or _pede_lista_opcoes(mensagem):
        return False
    sessao["menu_interrompido"] = sessao.get("aguardando_opcao")
    sessao["aguardando_opcao"] = None
    return True


def numero_solto_de_correcao(mensagem):
    """Extrai número solto só quando a frase parece correção/refinamento."""
    t = normalizar(mensagem)
    m = re.fullmatch(
        r'\s*(?:na verdade|corrige(?: pra| para)?|muda(?: pra| para)?|troca(?: pra| para)?|'
        r'agora|seria|e|mas e|faz|fecha)?\s*(\d{1,6})\s*(?:pecas?|unidades?)?\??\s*',
        t
    )
    return int(m.group(1)) if m else None


def detectar_tipo_turno(mensagem, slots_turno=None, sessao=None):
    """
    Classifica a fala atual pelo papel conversacional.

    Isso não substitui o classificador de intenção; serve para decidir quais partes
    do contexto podem ser herdadas com segurança antes da classificação.
    """
    slots_turno = slots_turno or {}
    t = normalizar(mensagem)
    ultimo = (sessao or {}).get("ultimo_assunto")
    foco = (sessao or {}).get("foco_atual", {})
    problema_ativo = (sessao or {}).get("problema_cliente")
    tem_orcamento = ultimo in INTENCOES_ORCAMENTO or bool(foco.get("produto") and foco.get("quantidade"))

    if re.search(r'defeito|defeituos|veio errad|saiu errad|costura.{0,24}(torta|solta|defeito)|furo|problema na peca|reclam', t):
        return "problema_cliente"
    if re.search(r'atras|passou do prazo|nao chegou|não chegou|cade meu pedido|cadê meu pedido', t):
        return "problema_cliente"
    if problema_ativo and re.search(r'resolver|arrumar|corrigir|e agora|o que faco|o que faço|posso acelerar|adiantar|urgente', t):
        return "problema_cliente"

    if re.search(r'empresa|corporativ|evento|uniforme|local quente|calor|logo|mais barato|barato|custo|não sei qual|nao sei qual', t):
        return "recomendacao"

    if tem_orcamento and (
        numero_solto_de_correcao(t)
        or re.search(r'\b(na verdade|corrig|troca|trocar|muda|mudar|seria|faz|fecha)\b', t)
    ):
        return "correcao_orcamento"

    if re.search(r'\b(qual|quais)\s+cores?\b|\btem\b.*\b(cor|azul|preto|branco|cinza|marinho|vermelh|rosa|amarel|verde)\b', t) \
       or (slots_turno.get("cor") and re.search(r'\btem\b|disponiv|estoque|cor', t)):
        return "pergunta_atributo"

    if slots_turno.get("tecido") and re.fullmatch(r'\s*(e\s+)?[\w\s]+?\??\s*', t) and foco.get("produto"):
        return "compatibilidade"
    if re.search(r'combina|da pra|dá pra|funciona|serve|em .* da\??|posso usar|pode usar', t):
        return "compatibilidade"

    return "continuidade"
