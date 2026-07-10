"""
Gerenciamento de contexto da conversa (a "memória do garçom").

Design:
- foco_atual: slots do assunto que está sendo discutido AGORA (curto prazo)
- historico_turnos: registro completo de cada turno (longo prazo, memória)
- aguardando_opcao: menu que o bot mostrou e está aguardando resposta
- ultimo_assunto: última intenção real (ignora "selecao_opcao" de menu)
- ativa: se a conversa já começou
"""
import re

from bot.estados import estado_da_conversa, objetivo_do_usuario
from bot.normalizar import normalizar
from bot.politica import detectar_tipo_turno, numero_solto_de_correcao


# ── slots que NUNCA persistem no foco_atual ──────────────────────
# São perguntas de turno único. Saem do foco_atual depois de usados.
SLOTS_EFEMEROS = {"numero_pedido", "metragem", "prazo_desejado", "urgente"}

# ── slots "filhos" de produto ────────────────────────────────────
# Quando o produto muda, esses são invalidados (são propriedades do produto antigo).
SLOTS_FILHOS_PRODUTO = {"personalizacao", "cor", "grade", "tecido"}

# Intenções de orçamento (preço/prazo/viabilidade)
INTENCOES_ORCAMENTO = {
    "combinado_preco_qtd_produto",
    "combinado_prazo_qtd_produto",
    "combinado_prazo_personalizacao_produto",
    "combinado_preco_personalizacao",
    "combinado_desconto_volume",
    "viabilidade_producao",
    "consumo_tecido",
}

# Intenções de pedido específico (status / alterar / cancelar)
INTENCOES_PEDIDO = {
    "status_pedido",
    "alterar_pedido_especifico",
    "alterar_pedido",
    "cancelar_pedido",
}


def criar_sessao():
    """Cria sessão nova e vazia."""
    return {
        "foco_atual": {},        # slots do assunto atual (curto prazo)
        "historico_turnos": [],  # registro completo de cada turno (longo prazo)
        "aguardando_opcao": None,
        # ── personalização: nome do cliente (ver bot/cliente.py) ────
        "nome_cliente": None,            # o nome, guardado durante a conversa
        "aguardando_nome": False,        # True enquanto esperamos o cliente dizer o nome
        # ── estados do CRUD de pedidos ──────────────────────────────
        "aguardando_id": None,          # ação esperando o ID ("status_pedido"/"cancelar_pedido"/...)
        "alteracao_pendente": None,     # {campo, valor} guardado até o cliente mandar o ID
        "registro_pedido": None,        # dados coletados do pedido em registro (CREATE), ou None
        "registro_campo_pendente": None,  # campo que estamos perguntando agora
        "carrinho": [],                  # itens do pedido em montagem (vários produtos, 1 pedido)
        "aguardando_mais_produto": False,  # esperando resposta de "quer adicionar mais?"
        # ── mapa de estados da conversa (ver bot/estados.py) ────────
        "estado_conversa": "OCIOSO",     # ONDE estamos no diálogo
        "objetivo_usuario": None,        # O QUE o usuário quer (meta grande)
        "ultimo_assunto": None,
        # Últimas intenções enviadas (mais recente por último). Usado pelo
        # responder pra variar setor_* repetido — sem isso, "preço?"/"valor?"/
        # "quanto?" geram texto idêntico 3x seguidas (Grice, Quantity/Relation).
        "ultimas_intencoes": [],
        # ── score de confiança / re-ranking (ver classifier.pontuar_candidatas) ──
        "intencao_candidatas": [],       # top intenções com score, do último turno
        "confianca": 0.0,                # score da intenção mais forte
        "intencao_escolhida": None,      # a que o bot REALMENTE usou (regra pode ter recalculado)
        "ativa": False,
    }


def resetar_sessao(sessao):
    """Zera tudo (usado em despedida real)."""
    sessao["foco_atual"] = {}
    sessao["historico_turnos"] = []
    sessao["aguardando_opcao"] = None
    sessao["nome_cliente"] = None
    sessao["aguardando_nome"] = False
    sessao["aguardando_id"] = None
    sessao["alteracao_pendente"] = None
    sessao["registro_pedido"] = None
    sessao["registro_campo_pendente"] = None
    sessao["carrinho"] = []
    sessao["aguardando_mais_produto"] = False
    sessao["estado_conversa"] = "OCIOSO"
    sessao["objetivo_usuario"] = None
    sessao["ultimo_assunto"] = None
    sessao["ultimas_intencoes"] = []
    sessao["ativa"] = False
    return sessao


def merge_com_contexto(slots_do_turno, sessao, mensagem=""):
    """
    Junta os slots do turno atual com os do contexto, aplicando regras de invalidação.

    Princípio: quando o assunto principal muda, slots dependentes são esquecidos
    do FOCO atual — mas continuam preservados no histórico de turnos.

    Retorna: dict de slots EFETIVOS (para o classifier/responder usarem),
    SEM modificar a sessão ainda (isso vira responsabilidade do main/app).
    """
    foco = dict(sessao.get("foco_atual", {}))
    tipo_turno = detectar_tipo_turno(mensagem, slots_do_turno, sessao) if mensagem else "continuidade"
    if sessao is not None:
        sessao["tipo_turno"] = tipo_turno

    def base_com(*chaves):
        return {k: foco[k] for k in chaves if k in foco and foco[k] not in (None, "")}

    if tipo_turno == "correcao_orcamento":
        base = base_com("produto", "quantidade", "personalizacao", "prazo_desejado", "urgente")
        qtd = numero_solto_de_correcao(mensagem or "")
        if qtd and base.get("produto"):
            base["quantidade"] = qtd
        produto_novo = slots_do_turno.get("produto")
        if produto_novo and produto_novo != base.get("produto"):
            base["produto"] = produto_novo
            for k in SLOTS_FILHOS_PRODUTO:
                base.pop(k, None)
        for chave, valor in slots_do_turno.items():
            base[chave] = valor
        return base

    if tipo_turno == "pergunta_atributo":
        base = base_com("produto")
        if slots_do_turno.get("tecido"):
            base["tecido"] = slots_do_turno["tecido"]
        for chave, valor in slots_do_turno.items():
            base[chave] = valor
        return base

    if tipo_turno == "compatibilidade":
        base = base_com("produto", "personalizacao")
        for chave, valor in slots_do_turno.items():
            base[chave] = valor
        return base

    if tipo_turno == "recomendacao":
        base = {}
        for chave in ("produto", "personalizacao", "uso"):
            if chave in foco and not slots_do_turno.get(chave):
                base[chave] = foco[chave]
        for chave, valor in slots_do_turno.items():
            base[chave] = valor
        return base

    if tipo_turno == "problema_cliente":
        base = base_com("numero_pedido")
        for chave, valor in slots_do_turno.items():
            base[chave] = valor
        return base

    # Regra 1: se o produto mudou no turno atual, esquecer slots-filhos do produto antigo
    produto_novo = slots_do_turno.get("produto")
    if produto_novo and foco.get("produto") and produto_novo != foco["produto"]:
        for k in SLOTS_FILHOS_PRODUTO:
            foco.pop(k, None)

    # Regra 2: aplica slots novos por cima
    for chave, valor in slots_do_turno.items():
        foco[chave] = valor

    return foco


def atualizar_sessao_pos_turno(sessao, mensagem, slots_efetivos, intencao, resposta):
    """
    Persiste mudanças na sessão DEPOIS que o turno foi respondido.

    - Salva no histórico_turnos
    - Atualiza foco_atual (removendo slots efêmeros)
    - Atualiza ultimo_assunto (mas não com 'selecao_opcao')
    """
    # Histórico cresce sempre
    sessao["historico_turnos"].append({
        "msg": mensagem,
        "intencao": intencao,
        "slots": dict(slots_efetivos),
        "resposta": resposta[:200],  # resumo
    })

    # Foco atual: remove slots efêmeros (eles só valem pro turno em que apareceram)
    novo_foco = {k: v for k, v in slots_efetivos.items() if k not in SLOTS_EFEMEROS}

    # Regra: se mudou para intenção de pedido, esquecer produto/qtd de orçamento
    if intencao in INTENCOES_PEDIDO and sessao.get("ultimo_assunto") in INTENCOES_ORCAMENTO:
        novo_foco.pop("produto", None)
        novo_foco.pop("quantidade", None)

    # Acabou de registrar um item e vamos perguntar "quer mais um produto?" →
    # zera o foco pra o PRÓXIMO produto não herdar os dados do anterior.
    if sessao.get("aguardando_mais_produto"):
        novo_foco = {}

    sessao["foco_atual"] = novo_foco

    # ultimo_assunto: ignora seleções de menu (preserva o assunto real anterior)
    if intencao != "selecao_opcao":
        sessao["ultimo_assunto"] = intencao

    # Buffer curto de intenções pra o responder detectar repetição e variar.
    # Guarda no máximo 5. Ignora seleções de menu (que costumam vir intercaladas).
    if intencao != "selecao_opcao":
        buf = sessao.setdefault("ultimas_intencoes", [])
        buf.append(intencao)
        if len(buf) > 5:
            del buf[:-5]

    if intencao in {"qualidade_defeito", "prazo_atraso", "status_pedido", "prazo_urgente"}:
        sessao["problema_cliente"] = {
            "intencao": intencao,
            "msg": mensagem,
            "slots": dict(slots_efetivos),
        }
    elif intencao not in {"fallback", "casual", "selecao_opcao"} and sessao.get("tipo_turno") != "problema_cliente":
        sessao["problema_cliente"] = None

    if sessao.get("tipo_turno") == "recomendacao":
        perfil = sessao.get("perfil_recomendacao") or {}
        t = normalizar(mensagem)
        if re.search(r'empresa|corporativ|uniforme', t):
            perfil["uso"] = "empresa"
        if re.search(r'evento', t):
            perfil["evento"] = True
        if re.search(r'local quente|calor|verao|verão', t):
            perfil["clima"] = "quente"
        if re.search(r'\blogo\b|bordad|estamp', t):
            perfil["personalizacao"] = "logo"
        if re.search(r'barat|custo|econom', t):
            perfil["prioridade"] = "preco"
        sessao["perfil_recomendacao"] = perfil

    # a intenção que o bot DE FATO usou (pode divergir da candidata de maior score
    # quando uma regra recalcula — ex: "comprar moto": score aponta vendas, regra
    # de negação escolhe cat_nao_fazemos).
    sessao["intencao_escolhida"] = intencao

    sessao["ativa"] = True

    # ── atualiza o MAPA DE ESTADOS da conversa (ver bot/estados.py) ──
    # estado_conversa é recalculado todo turno (deriva dos sinais acima);
    # objetivo_usuario não muda numa seleção de menu (preserva a meta real).
    sessao["estado_conversa"] = estado_da_conversa(sessao)
    if intencao != "selecao_opcao":
        sessao["objetivo_usuario"] = objetivo_do_usuario(intencao)

    return sessao


# ───────────────────────── despedida e casual ─────────────────────────

# Despedidas PURAS (sem agradecimento — agradecimento é casual)
_DESPEDIDAS_EXATAS = {
    "tchau", "ate logo", "ate mais", "flw", "vlw", "falou",
    "era so isso", "resolvido", "encerrar", "finalizar",
    "ate a proxima", "ate depois", "ate amanha",
}

# Casuais — agradecimentos curtos e confirmações
_CASUAIS = {
    "blz", "beleza", "ok", "certo", "entendi", "sim", "legal",
    "otimo", "perfeito", "ta", "massa", "show", "top",
    "obrigado", "obrigada", "obg", "valeu", "brigado", "brigada",
    "tmj", "tranquilo", "vou pensar", "vou ver", "vou analisar",
}


def is_despedida(mensagem):
    """
    Verdadeiro APENAS se a mensagem é uma despedida pura, curta e isolada.

    Conserta o Crítico 4: antes "obrigado, e me fala o prazo" resetava a
    sessão por causa do substring match. Agora exige que a mensagem inteira
    seja despedida (≤ 3 palavras E todas as palavras estão na lista).
    """
    t = normalizar(mensagem).strip()
    if not t:
        return False
    # match exato (qualquer comprimento)
    if t in _DESPEDIDAS_EXATAS:
        return True
    # mensagem curta (≤ 3 palavras) cujas palavras são todas despedidas
    palavras = re.findall(r"\w+", t)
    if 1 <= len(palavras) <= 3:
        # cada palavra é despedida ou casual (ex: "ok tchau", "valeu flw")
        if all(p in _DESPEDIDAS_EXATAS or p in _CASUAIS for p in palavras):
            # mas exige pelo menos UMA palavra de despedida pura
            if any(p in _DESPEDIDAS_EXATAS or p in {"tchau", "flw", "falou"} for p in palavras):
                return any(p in _DESPEDIDAS_EXATAS or p == "flw" or p == "tchau" or p == "falou"
                           for p in palavras)
    return False


def is_casual(mensagem):
    """
    Verdadeiro se a mensagem é só uma confirmação/agradecimento curto.

    Usada pra dizer "pode continuar" sem reiniciar o assunto.
    """
    t = normalizar(mensagem).strip()
    if not t:
        return False
    # match exato
    if t in _CASUAIS:
        return True
    # 2-3 palavras todas casuais (ex: "valeu, obg")
    palavras = re.findall(r"\w+", t)
    if 1 <= len(palavras) <= 3 and all(p in _CASUAIS for p in palavras):
        return True
    return False
