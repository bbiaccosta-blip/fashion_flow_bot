"""
Geração da resposta a partir da intenção classificada + slots efetivos + dados.
"""
import re

from bot.normalizar import normalizar
from bot.intencoes_runtime import EXIGE_HANDLER, MENUS
# CRUD de pedidos — cada operação mora no seu próprio arquivo em bot/pedidos/.
from bot.pedidos import criar, consultar, atualizar, cancelar



# Rótulo humano por prefixo/id de intenção — usado pela clarificação (R4).
# Ordem importa: prefixos específicos primeiro.
_LABELS_INTENCAO_PREFIXO = [
    ("combinado_preco", "preço"),
    ("combinado_prazo", "prazo"),
    ("combinado_desconto", "desconto"),
    ("combinado_cor", "cores"),
    ("combinado_tecido", "tecido"),
    ("combinado_tamanho", "tamanhos"),
    ("combinado_gramatura", "gramatura"),
    ("combinado_personalizacao", "personalização"),
    ("prazo_", "prazos"),
    ("previsao_prazo", "prazos"),
    ("qualidade", "qualidade"),
    ("personalizacao", "personalização"),
    ("sustent_", "sustentabilidade"),
    ("sustentabilidade", "sustentabilidade"),
    ("manut_", "cuidados com a peça"),
    ("manutencao", "cuidados com a peça"),
    ("cuidados_", "cuidados com a peça"),
    ("cat_camisetas", "camisetas"),
    ("cat_moletons", "moletons"),
    ("cat_calcas", "calças"),
    ("cat_vestidos", "vestidos"),
    ("cat_uniformes", "uniformes"),
    ("cat_infantil", "linha infantil"),
    ("cat_", "catálogo"),
    ("sug_trabalho", "sugestão de trabalho"),
    ("sug_esporte", "sugestão de esporte"),
    ("sug_festa", "sugestão de festa"),
    ("sug_inverno", "sugestão de inverno"),
    ("sug_verao", "sugestão de verão"),
    ("sug_uniforme", "uniforme corporativo"),
    ("sug_tec_", "sugestão de tecido"),
    ("sug_", "sugestão"),
    ("tec_", "tecidos"),
    ("tecidos", "tecidos"),
    ("cores_", "cores"),
    ("personalizacao_cores", "cores"),
    ("personalizacao_tamanhos", "tamanhos"),
    ("producao_", "produção"),
    ("producao", "produção"),
    ("status_pedido", "status do pedido"),
    ("cancelar_pedido", "cancelamento"),
    ("alterar_pedido", "alteração do pedido"),
    ("registrar_pedido", "registrar pedido"),
    ("setor_vendas", "vendas"),
    ("setor_logistica", "entrega"),
    ("setor_devolucao", "devolução"),
    ("setor_compras", "compras/fornecimento"),
    ("etapas_pedido", "etapas do pedido"),
    ("catalogo", "catálogo"),
    ("revenda", "revenda"),
    ("atende_empresa", "atendimento corporativo"),
    ("uniforme_escolar", "uniforme escolar"),
    ("private_label", "marca própria"),
]


def _label_intencao(intencao):
    """Devolve rótulo amigável pra intenção; fallback é o slug legível."""
    if not intencao:
        return "outro assunto"
    for prefix, label in _LABELS_INTENCAO_PREFIXO:
        if intencao == prefix or intencao.startswith(prefix + "_") or intencao.startswith(prefix):
            return label
    return intencao.replace("_", " ")


def _quer_menu(mensagem):
    """Verdadeiro quando o usuário pediu explicitamente opções/lista/menu."""
    t = normalizar(mensagem or "")
    return bool(re.search(
        r'\b(menu|opcoes|opções|opcao|opção|lista|listar|mostra|mostrar|quais|qual sao|quais sao|tipos|categorias|não sei|nao sei)\b',
        t
    ))


def _resposta_menu_direta(intencao, slots, dados):
    """Resumo direto para intenções que antes abriam menu por padrão."""
    produto = (slots or {}).get("produto")
    tecido = (slots or {}).get("tecido")
    textos = {
        "qualidade": (
            "As peças passam por controle de tecido, modelagem, corte, costura e acabamento. "
            "Também avaliamos durabilidade, defeitos de fabricação e certificações quando aplicável."
        ),
        "personalizacao": (
            "Trabalhamos com bordado, silkscreen, DTF, etiqueta personalizada e modelagem exclusiva. "
            "A melhor técnica depende da arte, tecido, quantidade e prazo."
        ),
        "personalizacao_tipos": (
            "As principais técnicas são bordado para acabamento premium, silkscreen para volume, "
            "DTF para artes coloridas/gradientes e etiqueta personalizada para marca própria."
        ),
        "personalizacao_cores": (
            "Temos cores básicas em estoque e cores sob demanda por tingimento. Para estampa, a combinação "
            "entre cor da peça e cor da arte precisa de amostra física quando há contraste alto."
        ),
        "personalizacao_tamanhos": (
            "Trabalhamos com grade adulto, infantil e plus size conforme o produto. Se você disser a peça, "
            "eu confirmo a grade disponível."
        ),
        "personalizacao_quantidade": (
            "A quantidade mínima muda por técnica: DTF aceita tiragens menores, bordado e silk ficam melhores "
            "a partir de volumes maiores. Para pedido grande, há desconto e planejamento em lotes."
        ),
        "sustentabilidade": (
            "A Fashion Flow trabalha com aproveitamento de tecido, reciclagem de sobras, opções de materiais "
            "reciclados e controle de químicos/tintas certificados quando a linha exige."
        ),
        "manutencao": (
            "Cuidados gerais: lavar do avesso, água fria, ciclo delicado, secar à sombra e evitar secadora. "
            "Peças com estampa ou bordado devem ser passadas do avesso."
        ),
        "manut_por_tecido": (
            "Os cuidados mudam por tecido: algodão pode encolher um pouco, viscose exige delicadeza, "
            "jeans pode desbotar e moletom não combina com calor alto/secadora."
        ),
        "producao": (
            "A produção passa por ficha técnica, modelagem, corte, costura, acabamento, revisão de qualidade "
            "e embalagem. Produzimos internamente no Brasil."
        ),
        "catalogo": (
            "Produzimos camisetas, polos, moletons, jaquetas, calças, vestidos, uniformes e linha infantil. "
            "Se você disser a categoria, eu detalho os modelos."
        ),
        "sugestao_produto": (
            "Posso sugerir por uso: dry fit para esporte, moletom/jaqueta para frio, polo ou camisa social "
            "para trabalho, vestido/alfaiataria para ocasiões especiais."
        ),
        "tecidos": (
            "Trabalhamos com algodão básico/penteado/pima, dry fit, viscose, linho, suplex, jeans, moletom, "
            "malha mista, tencel e alfaiataria. A escolha depende do produto e do uso."
        ),
        "sug_tecido_uso": (
            "Para calor, prefira algodão leve, viscose ou dry fit. Para frio, moletom flanelado e jeans pesado. "
            "Para esporte, dry fit ou suplex; para formal, linho ou alfaiataria."
        ),
        "previsao_prazo": (
            "O prazo padrão de produção fica entre 15 e 30 dias úteis, variando por quantidade, produto e personalização. "
            "Se você disser produto e quantidade, eu estimo melhor."
        ),
        "etapas_pedido": (
            "Um pedido passa por modelagem, corte, costura, acabamento, qualidade e expedição. Para consultar um pedido real, "
            "me informe o número no formato FF-AAAA-NNNN."
        ),
    }
    if intencao == "tecidos" and produto:
        return f"Para {produto.replace('_', ' ')}, eu posso confirmar tecidos recomendados e compatibilidade. Quer saber tecido ideal, composição ou cores?"
    if intencao == "personalizacao_cores" and tecido:
        return f"Para {tecido.replace('_', ' ')}, eu consigo consultar as cores cadastradas. Quer as cores em estoque ou combinação com estampa?"
    return textos.get(intencao)

def pecas(qtd):
    """Singular/plural correto (MÉDIO 26)."""
    return "peça" if qtd == 1 else "peças"


# ─────────────────────────── CRUD: coleta na conversa ───────────────────────────
# A lógica de CADA operação está em bot/pedidos/. O que fica aqui é só a parte de
# CONVERSA: perguntar os campos do registro um a um e descobrir o que alterar.

# Campos que precisamos coletar para registrar um pedido (na ordem das perguntas).
CAMPOS_REGISTRO = ["produto", "quantidade", "cor", "tamanho", "tecido", "personalizacao"]

PERGUNTAS_REGISTRO = {
    "produto": "Qual produto você quer produzir? (ex: camiseta, polo, moletom, vestido...)",
    "quantidade": "Quantas peças?",
    "cor": "Qual cor? (ex: preto, branco, marinho, vermelho...)",
    "tamanho": "Qual tamanho ou grade? (ex: M, G, infantil, plus size...)",
    "tecido": "Qual tecido? (ex: algodão, algodão pima, moletom flanelado, viscose...)",
    "personalizacao": "Qual personalização? (bordado, silk, DTF — ou responda 'nenhuma')",
}

# Palavras que abortam o registro no meio do caminho.
ABORTAR_REGISTRO = {"cancelar", "parar", "sair", "deixa pra la", "esquece", "esquecer", "desistir"}

# Palavras que sinalizam "não quero mais adicionar" — se aparecem quando o form
# estava pedindo produto (mas o cliente já tem itens no carrinho), fechar em vez
# de tratar como resposta inválida.
FECHAR_PEDIDO_FRASES = re.compile(
    r'^(so isso|\bnao\b|\bnão\b|nada mais|mais nada|era so|era só|pode fechar|'
    r'ja chega|chega|finaliz|acabou|encerrar?)\s*[!.]*$'
)


# Rótulo amigável de cada campo, pra mensagem de "isso não parece X".
ROTULO_CAMPO = {
    "produto": "um produto", "quantidade": "uma quantidade", "cor": "uma cor",
    "tamanho": "um tamanho", "tecido": "um tecido", "personalizacao": "uma personalização",
}



def _slots_registro_do_turno(mensagem):
    """Slots ditos AGORA, mapeados para os nomes do formulário de pedido."""
    from bot.extractor import extrair_slots
    st = extrair_slots(mensagem, em_menu=False)
    reg = {}
    for campo in ("produto", "quantidade", "cor", "tecido", "personalizacao"):
        if st.get(campo) not in (None, ""):
            reg[campo] = st[campo]
    if st.get("grade") not in (None, ""):
        reg["tamanho"] = st["grade"]
    return reg


_MARCADORES_TROCA = re.compile(
    r'\b(na verdade|muda|mudar|troca|trocar|corrig|na real|seria|prefiro)\b'
)


def _preencher_campos_fora_de_ordem(reg, mensagem):
    """Aproveita campos válidos mesmo quando o cliente respondeu fora da ordem.

    Também trata TROCA no meio do fluxo: se o cliente diz produto novo E há
    marcador de correção ("na verdade, moletom"), substituímos o produto e
    esquecemos os slots-filhos que podem ficar inconsistentes (tecido, cor,
    tamanho — grade do adulto do produto antigo pode não valer pro novo).
    """
    novos = _slots_registro_do_turno(mensagem)
    marcador = bool(_MARCADORES_TROCA.search(normalizar(mensagem)))
    for campo, valor in novos.items():
        if campo not in CAMPOS_REGISTRO:
            continue
        if not reg.get(campo):
            reg[campo] = valor
        elif marcador and reg.get(campo) != valor:
            # Correção explícita → substitui o valor.
            reg[campo] = valor
            # Se trocou o PRODUTO, invalida slots-filhos que dependem dele.
            if campo == "produto":
                for filho in ("tecido", "cor", "tamanho", "personalizacao"):
                    reg.pop(filho, None)
    return novos

def _valor_campo(mensagem, campo):
    """
    VALIDA a resposta do cliente para o campo perguntado no registro. Devolve o
    valor se for plausível, ou None se não for (aí o bot re-pergunta em vez de
    gravar lixo). Conserta o bug de "quais outros produtos tem" virar a cor.

    Obs: cor/tecido/personalização específicos já vêm pelo EXTRACTOR (passo 1 do
    fluxo). Aqui a gente só trata o texto cru: número, tamanho, 'nenhuma' e
    'tanto faz'. Cor/tecido arbitrário NÃO é aceito cru (o extractor conhece o
    vocabulário — se não pegou, não é uma cor/tecido válido).
    """
    t = normalizar((mensagem or "").strip())
    if not t:
        return None
    indiferente = bool(re.search(r'tanto faz|qualquer|indiferente|voce (que )?escolh|'
                                 r'nao sei|o (mais )?comum|padrao', t))
    if campo == "quantidade":
        m = re.search(r"\d+", t)
        return m.group(0) if m else None
    if campo == "tamanho":
        if re.search(r'plus|g1|g2|g3|g4', t):
            return "plus_size"
        if re.search(r'infantil|crianca|kids', t):
            return "infantil"
        m = re.fullmatch(r'(pp|p|m|g|gg|xgg)', t.replace(" ", ""))
        if m:
            return m.group(0).upper()
        if "adulto" in t or indiferente:
            return "adulto"
        return None
    if campo == "personalizacao":
        if re.search(r'nenhuma|sem person|sem estamp|nao quero nada|\bnenhum\b|'
                     r'\bnao\b|\bsem\b', t) or indiferente:
            return "nenhuma"
        return None   # silk/dtf/bordado vêm pelo extractor
    if campo in ("cor", "tecido"):
        return "a definir" if indiferente else None
    return None


def _responder_duvida_no_pedido(mensagem, dados):
    """
    Responde uma PERGUNTA feita no meio do registro (ex: "me fala da premium",
    "quais cores tem", "quanto custa"). Devolve a resposta, ou None se não for
    uma dúvida clara (aí o fluxo só re-pergunta o campo).

    Classifica/responde com sessao=None: sem o estado do registro (senão voltaria
    pro próprio registrar_pedido) e sem herdar os slots do pedido em andamento.
    """
    from bot.classifier import classificar
    from bot.extractor import extrair_slots

    st = extrair_slots(mensagem)
    intent = classificar(mensagem, st, st, dados["intencoes"], None)
    # Essas não são "dúvidas para responder e voltar": ou é ruído, ou mexeria no
    # próprio pedido (aí a gente só re-pergunta o campo).
    if intent in ("fallback", "registrar_pedido", "finalizar_pedidos", "selecao_opcao",
                  "cancelar_pedido", "alterar_pedido_especifico", "alterar_pedido",
                  "status_pedido"):
        return None
    return responder(intent, st, dados, None, mensagem)


def _fluxo_registrar(slots, sessao, mensagem, dados=None):
    """
    CREATE conversacional: coleta os campos do pedido ao longo da conversa e,
    quando tudo está preenchido, chama criar.registrar_pedido (que grava no CSV).
    `dados` é usado pra responder dúvidas feitas no meio do registro.
    """
    if sessao is None:
        return "Não consegui iniciar o registro agora."

    # Permite abortar o registro a qualquer momento.
    if normalizar(mensagem).strip() in ABORTAR_REGISTRO:
        sessao["registro_pedido"] = None
        sessao["registro_campo_pendente"] = None
        return "Tudo bem, cancelei o registro do pedido. Posso ajudar em outra coisa?"

    # "so isso"/"nao" no meio do form quando JÁ HÁ itens no carrinho: cliente
    # quis fechar o pedido (provavelmente errou/confundiu). Em vez de tratar como
    # resposta inválida, fecha o pedido.
    if sessao.get("carrinho") and FECHAR_PEDIDO_FRASES.match(normalizar(mensagem).strip()):
        # Se o item em montagem já tem os campos essenciais (produto+quantidade),
        # salva-o antes de fechar (senão o cliente perderia o item novo).
        reg_atual = sessao.get("registro_pedido") or {}
        if reg_atual.get("produto") and reg_atual.get("quantidade"):
            # completa com "nenhuma" quando personalização faltou (é o campo mais
            # comum onde o cliente responde "so isso" achando que fechou tudo).
            if not reg_atual.get("personalizacao"):
                reg_atual["personalizacao"] = "nenhuma"
            if not reg_atual.get("tecido"):
                reg_atual["tecido"] = "a definir"
            if not reg_atual.get("cor"):
                reg_atual["cor"] = "a definir"
            if not reg_atual.get("tamanho"):
                reg_atual["tamanho"] = "a definir"
            sessao["carrinho"].append(dict(reg_atual))
        sessao["registro_pedido"] = None
        sessao["registro_campo_pendente"] = None
        carrinho = sessao.get("carrinho", [])
        sessao["aguardando_mais_produto"] = False
        sessao["carrinho"] = []
        cliente = sessao.get("nome_cliente", "")
        return criar.registrar_pedido_lote(carrinho, cliente)["mensagem"]

    primeiro = sessao.get("registro_pedido") is None
    reg = sessao.get("registro_pedido") or {}

    # 1-2. Preenche os campos.
    pendente = sessao.get("registro_campo_pendente")
    invalido = False
    novos = {}
    if primeiro:
        # No primeiro turno usamos só os slots ditos AGORA. Isso evita herdar um
        # orçamento antigo quando o cliente diz apenas "quero fazer pedido".
        for campo, valor in _slots_registro_do_turno(mensagem).items():
            reg[campo] = valor
    elif pendente and not reg.get(pendente):
        # Aproveita campos fora de ordem (ex: cliente diz "algodão pima" quando
        # a pergunta era tamanho; guardamos o tecido e continuamos pedindo tamanho).
        novos = _preencher_campos_fora_de_ordem(reg, mensagem)
        valor = novos.get(pendente)
        if valor in (None, ""):
            valor = _valor_campo(mensagem, pendente)
        if valor:
            reg[pendente] = valor
        elif not novos:
            invalido = True
    sessao["registro_pedido"] = reg

    # 3. Ainda falta algum campo? Pergunta o próximo.
    faltando = [c for c in CAMPOS_REGISTRO if not reg.get(c)]
    if faltando:
        proximo = faltando[0]
        sessao["registro_campo_pendente"] = proximo
        intro = ""
        if invalido and proximo == pendente:
            # O cliente não respondeu o campo — provavelmente fez uma PERGUNTA no
            # meio do pedido. O professor cobra: NÃO deixar dúvida sem resposta.
            # Então respondemos a dúvida e VOLTAMOS pro pedido, re-perguntando.
            duvida = _responder_duvida_no_pedido(mensagem, dados) if dados else None
            # nudge GENTIL (não atropela): responde a dúvida e lembra do pedido
            # sem exigir, deixando o cliente perguntar quantas coisas quiser.
            volta = (f"Sem pressa 🙂 — quando quiser seguir com o pedido, "
                     f"{PERGUNTAS_REGISTRO[proximo][0].lower()}{PERGUNTAS_REGISTRO[proximo][1:]}")
            if duvida:
                return f"{duvida}\n\n{volta}"
            return (f"Não entendi isso como {ROTULO_CAMPO.get(pendente, 'resposta')}. "
                    f"{PERGUNTAS_REGISTRO[proximo]} (ou digite 'cancelar' pra sair do pedido)")
        if primeiro:
            # confirma o que já entendeu no pedido (ex: "100x camiseta em linho")
            partes = []
            if reg.get("quantidade") and reg.get("produto"):
                partes.append(f"{reg['quantidade']}x {reg['produto'].replace('_', ' ')}")
            elif reg.get("produto"):
                partes.append(reg["produto"].replace("_", " "))
            if reg.get("cor"):
                partes.append(reg["cor"].replace("_", " "))
            if reg.get("tecido"):
                partes.append("em " + reg["tecido"].replace("_", " "))
            resumo = ", ".join(partes)
            intro = (f"Boa, anotei: {resumo}. Vou registrar seu pedido — só faltam "
                     "alguns dados. " if resumo else "Vamos registrar seu pedido! ")
        elif novos and proximo == pendente:
            anotados = []
            for campo, valor in novos.items():
                if campo != proximo and reg.get(campo) == valor:
                    anotados.append(f"{ROTULO_CAMPO.get(campo, campo)} {str(valor).replace('_', ' ')}")
            if anotados:
                intro = "Anotei " + ", ".join(anotados) + ". "
        return intro + PERGUNTAS_REGISTRO[proximo]

    # 4. Completou a coleta DESTE item → guarda no CARRINHO (ainda NÃO grava;
    #    o pedido só fecha quando o cliente disser que não quer mais produtos —
    #    aí vira UM pedido só, com vários itens).
    sessao["registro_campo_pendente"] = None
    sessao["registro_pedido"] = None
    sessao.setdefault("carrinho", []).append(dict(reg))
    sessao["aguardando_mais_produto"] = True
    n = len(sessao["carrinho"])
    resumo = f"{reg.get('quantidade')}x {str(reg.get('produto', '')).replace('_', ' ')} " \
             f"{str(reg.get('cor', '')).replace('_', ' ')}".strip()
    return (f"Anotei o item {n}: {resumo}. Quer adicionar mais algum produto a esse "
            "pedido? (me diz o próximo, ou 'não' pra fechar o pedido)")


def _detectar_alteracao(mensagem, slots):
    """
    Descobre qual campo o cliente quer mudar e para qual valor novo.
    Retorna (campo, valor) ou (None, None) se não der pra inferir.

    Duas regras que consertam o bug do "mudou de 'preto' para 'preto'":
    - O valor NOVO é o que vem depois de "para/pra" — em "de algodão PARA linho",
      o alvo é linho (o primeiro tecido citado costuma ser o valor ATUAL).
    - Re-extrai da própria mensagem (sem herdar o contexto), senão pegava uma
      cor/tecido velho da conversa e "alterava" pro mesmo valor.
    """
    from bot.extractor import extrair_slots

    t = normalizar(mensagem)
    m_alvo = re.search(r'\b(?:para|pra|pro)\s+(.+)$', t)
    alvo = extrair_slots(m_alvo.group(1)) if m_alvo else {}   # valor depois de "para"
    aqui = extrair_slots(mensagem)                            # slots ditos AGORA (sem contexto)

    def val(chave):
        return alvo.get(chave) if alvo.get(chave) is not None else aqui.get(chave)

    # 1. Campo dito por extenso na frase ("mudar o TECIDO para linho").
    if "tecido" in t and val("tecido") is not None:
        return "tecido", val("tecido")
    if "cor" in t and val("cor") is not None:
        return "cor", val("cor")
    if "tamanho" in t and val("grade") is not None:
        return "tamanho", val("grade")
    if "quantidade" in t or "quantas" in t:
        q = val("quantidade")
        if q is None and m_alvo:            # "mudar a quantidade para 200" (sem unidade)
            m_num = re.search(r'\d+', m_alvo.group(1))
            q = int(m_num.group()) if m_num else None
        if q is not None:
            return "quantidade", q
    if "personaliza" in t and val("personalizacao") is not None:
        return "personalizacao", val("personalizacao")

    # 2. Sem o nome do campo: infere pelo ALVO (o que vem depois de "para").
    for campo, chave in (("tecido", "tecido"), ("cor", "cor"), ("quantidade", "quantidade"),
                         ("personalizacao", "personalizacao"), ("tamanho", "grade")):
        if alvo.get(chave) is not None:
            return campo, alvo[chave]

    # 3. Último recurso: um único slot dito na própria mensagem.
    for campo, chave in (("tecido", "tecido"), ("cor", "cor"), ("quantidade", "quantidade"),
                         ("personalizacao", "personalizacao")):
        if aqui.get(chave) is not None:
            return campo, aqui[chave]
    return None, None


def _reafirma_produtos(dados):
    """Lista as CATEGORIAS de produtos que a Fashion Flow faz (tabela produtos.csv)."""
    df = dados["produtos"]
    ativos = df[df["ativo"].astype(str).str.strip().str.lower() == "sim"]
    cats = list(dict.fromkeys(ativos["categoria"].tolist()))   # únicas, na ordem
    if len(cats) > 1:
        return ", ".join(cats[:-1]) + " e " + cats[-1]
    return cats[0] if cats else ""


def responder(intencao, slots, dados, sessao=None, mensagem=""):
    """
    Retorna a resposta em texto para o usuário.
    `slots` aqui são os slots EFETIVOS (foco_atual + slots_turno mesclados).
    """

    if sessao and sessao.get("aguardando_id") and intencao in ("status_pedido", "alterar_pedido_especifico", "cancelar_pedido") and not slots.get("numero_pedido"):
        t_msg = normalizar(mensagem)
        if re.search(r'nao tenho|não tenho|nao sei|não sei|sem numero|sem número|esqueci', t_msg):
            return (
                "Sem o número do pedido eu não consigo consultar com segurança. "
                "Procura no comprovante ou na mensagem de confirmação; o formato é FF-AAAA-NNNN. "
                "Se preferir, posso seguir com outra dúvida enquanto isso."
            )
        nudges = sessao.setdefault("pedido_id_nudges", {})
        nudges[intencao] = nudges.get(intencao, 0) + 1
        if intencao == "status_pedido":
            if nudges[intencao] == 1:
                return (
                    "Consigo consultar, mas preciso do número do pedido para não olhar o pedido errado. "
                    "Ele fica no formato FF-AAAA-NNNN."
                )
            return (
                "Ainda falta o número FF-AAAA-NNNN. Sem ele eu não consigo ver andamento, etapa ou previsão desse pedido."
            )
        if intencao == "alterar_pedido_especifico":
            if nudges[intencao] == 1:
                return (
                    "Para ver se dá para alterar, preciso do número FF-AAAA-NNNN. "
                    "A alteração depende da etapa: em modelagem costuma dar, depois do corte geralmente não."
                )
            return (
                "Ainda preciso do número FF-AAAA-NNNN para conferir se esse pedido pode ser alterado."
            )
        if intencao == "cancelar_pedido":
            return "Para cancelar com segurança, me informe o número FF-AAAA-NNNN do pedido."

    # ── MULTI-INTENÇÃO: cliente perguntou 3+ tópicos numa frase só ──
    # O classifier detectou e guardou a lista em sessao["topicos_pendentes"].
    # Em vez de responder um dos tópicos e ignorar o resto (comportamento antigo),
    # a gente lista o que entendeu e pergunta por qual começar.
    if intencao == "multi_intencao":
        from bot.classifier import _TOPICOS_LABELS
        topicos = (sessao or {}).get("topicos_pendentes", [])
        if topicos:
            nomes = [_TOPICOS_LABELS.get(x, x) for x in topicos]
            if len(nomes) == 2:
                lista = f"{nomes[0]} e {nomes[1]}"
            else:
                lista = ", ".join(nomes[:-1]) + f" e {nomes[-1]}"
            return (f"Vi que você quer saber sobre vários assuntos: {lista}. "
                    f"Por qual você quer começar?")

    # ── CLARIFICAÇÃO: top-2 candidatas com score empatado ─────
    # O classifier detectou ambiguidade real e nos passou as duas intenções.
    # Preferimos perguntar ao cliente qual assunto ele quer do que arriscar
    # a errada silenciosamente.
    if intencao == "clarificacao":
        candidatas = (sessao or {}).get("candidatas_ambiguas", [])
        if len(candidatas) >= 2:
            a = _label_intencao(candidatas[0])
            b = _label_intencao(candidatas[1])
            if a != b:
                return (
                    f"Ficou meio ambíguo pra mim aqui. Você quer saber sobre {a} "
                    f"ou sobre {b}?"
                )

    # ── cores_basicas COM cor citada: confirma a cor primeiro (grounding) ──
    # "queria uma roupa rosa" caía na lista genérica de 12 cores onde "rosa"
    # era a última palavra — o cliente não sentia que foi ouvido. Aqui, se a
    # cor pedida veio no turno, a resposta abre confirmando e convida a
    # escolher a peça (as 12 cores do estoque cobrem todas as do extractor).
    if intencao == "cores_basicas" and (slots or {}).get("cor"):
        _NOME_COR = {
            "royal": "azul royal", "marinho": "azul marinho",
            "cinza_mescla": "cinza mescla", "cinza_chumbo": "cinza chumbo",
            "verde_militar": "verde militar", "verde_bandeira": "verde bandeira",
        }
        cor_pedida = slots["cor"]
        cor_nome = _NOME_COR.get(cor_pedida, cor_pedida.replace("_", " "))
        return (
            f"Temos {cor_nome} sim, em pronta entrega! Qual peça você procura "
            f"nessa cor? Fazemos camisetas, polos, moletons, calças, vestidos e "
            f"uniformes — é só me dizer que eu te passo os detalhes."
        )

    if intencao == "manut_amaciante":
        return (
            "Melhor evitar amaciante, principalmente em moletom, dry fit e peças com estampa. "
            "Ele pode endurecer fibras, reduzir respirabilidade e prejudicar a durabilidade da personalização. "
            "Prefira sabão neutro e água fria."
        )

    if intencao == "sobre_marca_tempo":
        return (
            "A Fashion Flow atua como confecção de produção própria, com foco em peças sob demanda, "
            "uniformes, personalização e private label. Para histórico comercial completo, o setor de vendas confirma os detalhes."
        )

    if intencao == "sustent_algodao_organico":
        return (
            "Alguns lotes podem usar algodão certificado/sustentável sob demanda, mas a linha padrão não é toda orgânica. "
            "Quando o pedido exige certificação, confirmamos disponibilidade do tecido antes de fechar produção."
        )

    if intencao == "sustent_fibra_reciclada":
        return (
            "Sim, trabalhamos com opções de poliéster reciclado (rPET) e reaproveitamento de sobras têxteis em linhas específicas. "
            "A disponibilidade depende do produto e da cor escolhida."
        )

    if intencao == "negociacao_pedido":
        # Cliente perguntou sobre combinar/misturar/variar no mesmo pedido.
        # Resposta comercial: sim/depende + próximo passo pra fechamento.
        return (
            "Dá pra fazer: no mesmo pedido você pode combinar cor por cor, variar tamanhos "
            "dentro da grade, misturar bordado e silk em peças diferentes e até dividir "
            "quantidades por variação (ex: 250 pretas + 250 brancas). Combinar duas técnicas "
            "na MESMA peça (bordado + silk) é possível, mas encarece — vendas confirma o "
            "acréscimo. Me diz como você quer dividir que eu registro no pedido."
        )

    if intencao == "comparar_premium_basica":
        return (
            "A camiseta premium usa algodão pima penteado: toque mais macio, fio mais fino "
            "e melhor durabilidade. A básica é mais econômica e funciona bem para volume, "
            "uniforme simples e ações promocionais. Se a peça for para marca própria, revenda "
            "ou uso frequente, eu indicaria a premium; se o foco for custo, a básica resolve melhor."
        )

    if intencao == "qualidade_defeito":
        if sessao is not None:
            sessao["problema_cliente"] = {"intencao": intencao, "msg": mensagem, "slots": dict(slots or {})}
        t_msg = normalizar(mensagem or "")
        if re.search(r'resolver|arrumar|corrigir|e agora|o que faco|o que faço', t_msg):
            return (
                "Certo, vamos resolver pelo pedido. Me envie o número FF-AAAA-NNNN e uma foto do defeito; "
                "com isso a qualidade consegue avaliar se entra como troca, retrabalho ou devolução."
            )
        if re.search(r'costura', t_msg):
            return (
                "Costura torta entra como possível defeito de acabamento. Para abrir a análise, preciso do número do pedido "
                "e uma foto mostrando a costura; assim a equipe confere lote, etapa e melhor solução."
            )
        return (
            "Entendi: isso parece defeito de fabricação ou problema de acabamento. "
            "Para resolver, preciso do número do pedido e, se possível, uma foto da peça mostrando o defeito. "
            "Com isso dá para acionar qualidade/devoluções e orientar troca, retrabalho ou análise técnica."
        )

    if intencao == "prazo_atraso":
        if sessao is not None:
            sessao["problema_cliente"] = {"intencao": intencao, "msg": mensagem, "slots": dict(slots or {})}
            sessao["aguardando_id"] = "status_pedido"
        return (
            "Vamos tratar o atraso pelo pedido certo. Me informe o número do pedido no formato FF-AAAA-NNNN; "
            "com ele eu consulto o andamento e vejo se está em produção, qualidade ou expedição."
        )

    if intencao == "prazo_urgente":
        return (
            "Dá para avaliar aceleração de prazo, mas depende da etapa do pedido e da fila de produção. "
            "Se você já tem um pedido, me envie o número FF-AAAA-NNNN. Se ainda é orçamento, me diga produto, quantidade e data limite."
        )

    if intencao in {"setor_vendas", "setor_logistica", "setor_devolucao", "setor_compras"}:
        # Dedupe: 2ª/3ª ocorrência consecutiva do mesmo setor gera resposta variada
        # (Grice: Quantity/Relation — não repetir e oferecer próximo passo útil).
        buf = (sessao or {}).get("ultimas_intencoes", [])
        repeticoes = 0
        for prev in reversed(buf):
            if prev == intencao:
                repeticoes += 1
            else:
                break

        if intencao == "setor_vendas":
            perfil = (sessao or {}).get("perfil_recomendacao", {})
            # GROUNDING: se o cliente JÁ disse produto/qtd/personalização, ecoar
            # em vez de pedir de novo — respeita Grice (Relation) e mostra que
            # o bot está prestando atenção.
            focos = (sessao or {}).get("foco_atual", {})
            produto_foco = focos.get("produto") or (slots or {}).get("produto")
            qtd_foco = focos.get("quantidade") or (slots or {}).get("quantidade")
            pers_foco = focos.get("personalizacao") or (slots or {}).get("personalizacao")
            dados_ja_ditos = [x for x in (produto_foco, qtd_foco, pers_foco) if x]

            if dados_ja_ditos and repeticoes == 0:
                partes = []
                if qtd_foco: partes.append(f"{qtd_foco} peças")
                if produto_foco: partes.append(produto_foco.replace("_", " "))
                if pers_foco and pers_foco != "nenhuma":
                    partes.append(f"com {pers_foco.replace('_', ' ')}")
                resumo = ", ".join(partes) if partes else "o pedido"
                return (
                    f"Pra {resumo}, o valor final quem confirma é vendas — mas eu consigo "
                    f"dar uma estimativa aqui na hora. Se o que falta é só quantidade ou "
                    f"personalização, é só me dizer que eu calculo."
                )

            base = (
                "Pensando em menor preço, normalmente camiseta básica ou polo simples sem muitas cores de personalização "
                "fica mais em conta. Para comparar valor final, vendas precisa de produto, quantidade, logo/personalização e prazo."
            ) if perfil.get("prioridade") == "preco" else (
                "Para preço, valor final, pagamento, desconto ou fechamento, vendas confirma a proposta. "
                "Se você me disser produto, quantidade e personalização, eu consigo dar uma estimativa antes."
            )
            if repeticoes == 1:
                return (
                    "Como te falei, o fechamento de valor é com vendas. Mas se você me disser produto, "
                    "quantidade e personalização, eu já te dou uma estimativa aqui — evita esperar pra saber."
                )
            if repeticoes >= 2:
                return (
                    "Pra não ficar em círculo: me passa produto, quantidade e personalização "
                    "(mesmo que aproximado) que eu estimo pra você. Se preferir, posso chamar uma pessoa de vendas."
                )
            return base

        if intencao == "setor_logistica":
            if repeticoes == 1:
                return (
                    "Como comentei, entrega/frete/rastreio quem confirma é logística. "
                    "Se você me passar o número FF-AAAA-NNNN e o CEP, eu consigo verificar prazo estimado."
                )
            if repeticoes >= 2:
                return (
                    "Ainda depende de logística pra dar valor exato. Me diz o CEP e "
                    "o número do pedido (FF-AAAA-NNNN) que peço pra alguém retornar."
                )
            return (
                "Isso fica com logística: frete, envio, rastreio e prazo de entrega dependem do endereço e da transportadora. "
                "Se você já tem pedido, me informe o número FF-AAAA-NNNN; se ainda não fechou, vendas calcula o frete no orçamento."
            )

        if intencao == "setor_devolucao":
            if repeticoes >= 1:
                return (
                    "Pra devolução/troca eu preciso do número do pedido (FF-AAAA-NNNN) "
                    "e do motivo. Com isso, encaminho pra equipe de qualidade avaliar."
                )
            return (
                "Para troca, devolução, tamanho errado ou problema na peça recebida, o próximo passo é abrir análise do pedido. "
                "Me envie o número FF-AAAA-NNNN e explique o que veio errado; com isso a equipe verifica troca, ajuste ou devolução."
            )

        if intencao == "setor_compras":
            if repeticoes >= 1:
                return (
                    "Ainda é assunto de compras. Se puder me passar tipo de tecido, ficha técnica "
                    "e volume, eu encaminho o contato direto pra evitar mais idas e vindas."
                )
            return (
                "Se você quer vender ou fornecer tecido para a Fashion Flow, isso é assunto de compras. "
                "O ideal é enviar tipo de material, composição, ficha técnica, capacidade de fornecimento e contato comercial."
            )

    if intencao == "setor_almoxarifado":
        return (
            "Disponibilidade de matéria-prima é controlada pelo almoxarifado. "
            "Me diga qual tecido ou material você quer consultar que eu tento verificar pela base cadastrada."
        )

    if intencao == "sug_trabalho":
        return (
            "Para empresa, eu indicaria polo corporativa quando precisa de imagem profissional e custo controlado; "
            "camiseta premium para evento mais informal; e dry fit se o local for quente ou a equipe ficar em movimento. "
            "Se tiver logo, bordado passa mais confiança; silk/DTF costuma sair melhor em volume ou arte colorida."
        )

    if intencao == "sug_tec_quente":
        return (
            "Para local quente, priorize tecido leve e respirável: algodão leve, viscose, linho ou dry fit. "
            "Para uniforme de empresa com logo, eu compararia polo dry fit com bordado pequeno ou camiseta premium clara com silk/DTF."
        )

    if intencao == "personalizacao_bordado" and re.search(r'\blogo\b', normalizar(mensagem or "")):
        return (
            "Para logo de empresa, o bordado é a opção mais profissional e durável, especialmente em polo e uniforme. "
            "Se o logo tiver muitas cores ou degradê, DTF pode preservar melhor a arte; se for grande volume, silk pode reduzir custo."
        )

    # ── Atualizar último item do carrinho (cliente disse personalização
    #    depois de já ter fechado o item, ainda pensando no anterior) ──
    if intencao == "atualizar_ultimo_item":
        carrinho = (sessao or {}).get("carrinho", [])
        if carrinho:
            item = carrinho[-1]
            pers = item.get("personalizacao", "").replace("_", " ") or "nenhuma"
            n = len(carrinho)
            return (
                f"Corrigi o item {n}: {item.get('quantidade')}x "
                f"{item.get('produto', '').replace('_', ' ')} "
                f"{item.get('cor', '').replace('_', ' ')} com {pers}. "
                "Quer adicionar mais algum produto? (me diz o próximo, ou 'não' pra fechar)"
            )

    # ── CREATE: registrar pedido (coleta os campos ao longo da conversa) ──
    if intencao == "registrar_pedido":
        return _fluxo_registrar(slots, sessao, mensagem, dados)

    # ── Fecha o pedido: grava o CARRINHO como UM pedido só (vários itens) ──
    if intencao == "finalizar_pedidos":
        carrinho = (sessao or {}).get("carrinho", [])
        if sessao is not None:
            sessao["aguardando_mais_produto"] = False
            sessao["carrinho"] = []
        if not carrinho:
            return "Beleza! Qualquer coisa é só chamar. 😊"
        cliente = (sessao or {}).get("nome_cliente", "")
        return criar.registrar_pedido_lote(carrinho, cliente)["mensagem"]

    # ── Seleção de menu ──────────────────────────────────────────
    if intencao == "selecao_opcao":
        from rapidfuzz import fuzz

        opcao_menu = sessao.get("aguardando_opcao") if sessao else None
        # Mapa completo de menus, mesclando nosso (tecido/produto) com a versão
        # expandida da equipe (qualidade, personalização, sustentabilidade etc).
        opcoes_por_menu = {
            "menu_tecido": {
                "algodao basico": "algodao_basico", "algodao penteado": "algodao_penteado",
                "algodao pima": "algodao_pima", "dry fit": "dry_fit", "viscose": "viscose",
                "suplex": "suplex", "moletom flanelado": "moletom_flanelado",
                "moletom peluciado": "moletom_peluciado", "malha mista": "malha_mista",
                "linho": "linho", "jeans": "jeans", "alfaiataria": "alfaiataria",
            },
            "menu_produto": {
                "camiseta basica": "camiseta_basica", "camiseta premium": "camiseta_premium",
                "polo": "polo", "baby look": "baby_look", "moletom": "moletom",
                "jaqueta": "jaqueta", "calca jeans": "calca_jeans", "legging": "legging",
                "bermuda": "bermuda", "regata": "regata", "vestido midi": "vestido_midi",
                "jogger": "jogger", "uniforme polo": "uniforme_polo",
                "uniforme jaleco": "uniforme_jaleco", "oversized": "oversized",
            },
            "menu_qualidade": {
                "originalidade das pecas": "qualidade_originalidade",
                "durabilidade":            "qualidade_durabilidade",
                "controle de qualidade":   "qualidade_controle",
                "defeitos de fabricacao":  "qualidade_defeito",
                "certificacoes":           "qualidade_certificacoes",
            },
            "menu_personalizacao": {
                "tipos de personalizacao":  "personalizacao_tipos",
                "cores disponiveis":        "personalizacao_cores",
                "tamanhos disponiveis":     "personalizacao_tamanhos",
                "quantidade minima":        "personalizacao_quantidade",
                "prazo de personalizacao":  "personalizacao_prazo",
                "envio de arte":            "personalizacao_envio_arte",
            },
            "menu_personalizacao_tipos": {
                "estampa silkscreen":     "personalizacao_silkscreen",
                "estampa dtf digital":    "personalizacao_dtf",
                "bordado":                "personalizacao_bordado",
                "etiqueta personalizada": "personalizacao_etiqueta",
                "modelagem exclusiva":    "personalizacao_modelagem_exclusiva",
            },
            "menu_personalizacao_cores": {
                "cores basicas em estoque":    "cores_basicas",
                "tingimento sob demanda":      "cores_sob_demanda",
                "combinacao cor peca estampa": "cores_combinacao",
                "limite de cores por tecnica": "cores_limite_tecnica",
            },
            "menu_personalizacao_tamanhos": {
                "grade adulto":      "tamanhos_adulto",
                "grade infantil":    "tamanhos_infantil",
                "plus size":         "tamanhos_plus_size",
                "tabela de medidas": "tamanhos_tabela_medidas",
            },
            "menu_personalizacao_quantidade": {
                "minimo por tipo de personalizacao": "qtd_minima_personalizacao",
                "minimo por cor":                    "qtd_minima_cor",
                "pedidos grandes 500":               "qtd_grande_volume",
                "pedidos pequenos ate 30":           "qtd_pequena_volume",
            },
            "menu_sustentabilidade": {
                "aproveitamento de tecido": "sustent_aproveitamento",
                "materiais sustentaveis":   "sustent_materiais_eco",
                "reciclagem de sobras":     "sustent_reciclagem",
                "tinturas e quimicos":      "sustent_quimicos",
                "praticas trabalhistas":    "sustent_trabalho",
                "logistica sustentavel":    "sustent_logistica",
            },
            "menu_manutencao": {
                "como lavar":         "manut_lavar",
                "ferro de passar":    "manut_ferro",
                "secadora":           "manut_secadora",
                "alvejante":          "manut_alvejante",
                "tirar mancha":       "manut_mancha",
                "cuidados por tecido":"manut_por_tecido",
                "encolhimento":       "manut_encolhimento",
                "desbotamento":       "manut_desbotamento",
            },
            "menu_manut_por_tecido": {
                "algodao":   "cuidados_algodao",
                "viscose":   "cuidados_viscose",
                "poliester": "cuidados_poliester",
                "linho":     "cuidados_linho",
                "jeans":     "cuidados_jeans",
                "la":        "cuidados_la",
                "malha":     "cuidados_malha",
                "moletom":   "cuidados_moletom",
            },
            "menu_producao": {
                "etapas do processo":   "producao_etapas",
                "onde e produzido":     "producao_onde",
                "capacidade produtiva": "producao_capacidade",
                "tecnologia":           "producao_tecnologia",
                "equipe":               "producao_equipe",
                "modelagem":            "producao_modelagem",
                "corte e costura":      "producao_corte_costura",
            },
            "menu_catalogo": {
                "camisetas e basicas":    "cat_camisetas",
                "moletons e jaquetas":    "cat_moletons",
                "calcas e shorts":        "cat_calcas",
                "vestidos":               "cat_vestidos",
                "uniformes corporativos": "cat_uniformes",
                "linha infantil":         "cat_infantil",
            },
            "menu_sugestao_produto": {
                "casual dia a dia":       "sug_casual",
                "trabalho corporativo":   "sug_trabalho",
                "esporte academia":       "sug_esporte",
                "festa ocasiao especial": "sug_festa",
                "inverno":                "sug_inverno",
                "verao":                  "sug_verao",
                "uniforme empresa":       "sug_uniforme",
                "presente":               "sug_presente",
            },
            "menu_tecidos": {
                "lista de tecidos disponiveis": "tec_disponiveis",
                "composicao de cada peca":      "tec_composicao",
                "origem dos tecidos":           "tec_origem",
                "sugestao por uso":             "sug_tecido_uso",
                "tecido para pele sensivel":    "tec_pele_sensivel",
                "nao trabalhamos com":          "tec_couro",
            },
            "menu_sug_tecido_uso": {
                "clima quente":   "sug_tec_quente",
                "clima frio":     "sug_tec_frio",
                "uso diario":     "sug_tec_diario",
                "esporte":        "sug_tec_esporte",
                "ocasiao formal": "sug_tec_formal",
            },
            "menu_previsao_prazo": {
                "prazo padrao":       "prazo_padrao",
                "com personalizacao": "prazo_com_personalizacao",
                "pedido urgente":     "prazo_urgente",
                "pedido grande 500":  "prazo_grande_pedido",
                "atraso de pedido":   "prazo_atraso",
            },
            "menu_etapas_pedido": {
                "em que etapa esta":        "etapa_consulta",
                "alterar pedido":           "alterar_pedido",
                "cancelar pedido":          "cancelar_pedido",
                "acompanhamento detalhado": "acompanhamento",
            },
        }
        opcoes = opcoes_por_menu.get(opcao_menu, {})

        # usuário digitou um número
        try:
            numero = int(mensagem.strip())
            lista = list(opcoes.values())
            if 1 <= numero <= len(lista):
                escolha = lista[numero - 1]
                if sessao:
                    # MÉDIO 15: não persiste no foco_atual; só limpa o menu.
                    sessao["aguardando_opcao"] = None
                # Renderiza a sub-intenção COMPLETA (recursa no responder). Se ela
                # tiver um submenu próprio (ex: "tipos de personalização" → os 5
                # tipos), o submenu aparece. Antes voltava só o texto e o submenu
                # ficava sem opções ("Qual te interessa?" sem listar nada).
                return responder(escolha, {}, dados, sessao, mensagem)
        except (ValueError, TypeError):
            pass

        # usuário digitou o nome
        melhor_score = 0
        melhor_valor = None
        msg_norm = normalizar(mensagem)
        for chave, valor in opcoes.items():
            score = fuzz.partial_ratio(normalizar(chave), msg_norm)
            if score > melhor_score:
                melhor_score = score
                melhor_valor = valor

        if melhor_score >= 75:
            if sessao:
                sessao["aguardando_opcao"] = None
            return responder(melhor_valor, {}, dados, sessao, mensagem)

        # "quais são / me mostra as opções / não sei / lista" dentro de um menu →
        # RE-MOSTRA as opções (em vez de escapar pra fallback ou 'sobre o bot').
        t_norm = normalizar(mensagem)
        if re.search(r'\bquais\b|\bquantos\b|\bqual\b.*\b(sao|são|opc|tipo)|'
                     r'opcoe?s|op[çc][aã]o|me mostra|\bmostra\b|\blista\b|'
                     r'nao sei|não sei|me ajuda|\btodas\b|\btodos\b', t_norm):
            lista_opcoes = "\n".join(f"  {i+1}. {c.title()}"
                                     for i, c in enumerate(opcoes.keys()))
            return f"Claro! As opções são:\n{lista_opcoes}"

        # Não casou nenhuma opção. Antes isso virava um beco-sem-saída ("Não
        # entendi sua escolha" repetido) e o cliente ficava preso no menu. Agora
        # a gente SAI do menu e trata a mensagem como uma pergunta nova — a pessoa
        # provavelmente mudou de assunto ("me explica o silk") ou escolheu por
        # uma frase que não é o rótulo exato ("tem vegano?"). Conserta o "menu sem saída".
        from bot.extractor import extrair_slots
        from bot.contexto import merge_com_contexto
        from bot.classifier import classificar

        if sessao:
            sessao["aguardando_opcao"] = None
        slots_novos = extrair_slots(mensagem, em_menu=False)
        slots_ef = merge_com_contexto(slots_novos, sessao, mensagem) if sessao else slots_novos
        nova_intencao = classificar(mensagem, slots_novos, slots_ef, dados["intencoes"], sessao)
        if nova_intencao not in ("selecao_opcao", "fallback"):
            return responder(nova_intencao, slots_ef, dados, sessao, mensagem)

        # Nem como pergunta nova deu — aí sim mostra o menu de novo pra ajudar.
        if sessao:
            sessao["aguardando_opcao"] = opcao_menu
        lista_opcoes = "\n".join(f"  {i+1}. {c.title()}" for i, c in enumerate(opcoes.keys()))
        return f"Não entendi sua escolha. Por favor, selecione uma opção:\n{lista_opcoes}"

    # ── Prazo sem contexto (cenário 12) ──────────────────────────
    if intencao == "prazo_sem_contexto":
        prazo = slots.get("prazo_desejado", 0)
        return (
            f"Vi que você mencionou {prazo} dias — pra eu dizer se conseguimos, preciso saber: "
            "qual produto, qual quantidade e se tem personalização (silk, bordado, DTF)?"
        )

    if intencao == "alterar_pedido":
        return responder("alterar_pedido_especifico", slots, dados, sessao, mensagem)

    # ── DELETE: cancelar pedido (soft delete) ────────────────────
    if intencao == "cancelar_pedido":
        numero = slots.get("numero_pedido")
        if not numero:
            # Ainda não temos o ID → pergunta e guarda a ação como pendente.
            if sessao is not None:
                sessao["aguardando_id"] = "cancelar_pedido"
            return (
                "Pra cancelar, me informa o número do pedido (formato FF-AAAA-NNNN). "
                "Aviso: cancelamento é livre na modelagem; depois do corte pode haver "
                "custo de material já usado."
            )
        if sessao is not None:
            sessao["aguardando_id"] = None
        return cancelar.cancelar_pedido(numero, sessao.get("nome_cliente") if sessao else None)["mensagem"]

    # ── Disponibilidade de materiais / estoque (CRÍTICO 5) ──────
    if intencao == "disponibilidade_materiais":
        tecido = slots.get("tecido")
        df = dados["estoque_materiais"]
        if tecido:
            row = df[df["tecido"] == tecido]
            if not row.empty:
                r = row.iloc[0]
                if r["status"] == "disponivel":
                    return (
                        f"Sim, temos {tecido.replace('_', ' ')} em estoque: "
                        f"{r['metros_disponivel']}m disponíveis. {r['observacao']}."
                    )
                else:
                    return (
                        f"No momento {tecido.replace('_', ' ')} está sem estoque. "
                        f"Previsão de reposição: {r['previsao_reposicao']}. {r['observacao']}."
                    )
        # sem tecido específico — visão geral
        disponiveis = df[df["status"] == "disponivel"]["tecido"].tolist()
        indispon = df[df["status"] == "indisponivel"]["tecido"].tolist()
        return (
            "Visão geral de estoque: "
            f"disponíveis ({len(disponiveis)}) — {', '.join(t.replace('_',' ') for t in disponiveis[:6])}"
            + (f"... + {len(disponiveis)-6} outros." if len(disponiveis) > 6 else ".")
            + (f" Indisponíveis: {', '.join(t.replace('_',' ') for t in indispon)}." if indispon else "")
        )

    # ── READ: consultar pedido por ID ────────────────────────────
    if intencao == "status_pedido":
        numero = slots.get("numero_pedido")
        if not numero:
            # Não veio o ID → pergunta e marca que estamos esperando ele.
            if sessao is not None:
                sessao["aguardando_id"] = "status_pedido"
            return (
                "Claro! Me informa o número do pedido que eu consulto o andamento na "
                "produção. O formato é FF-AAAA-NNNN (ex: FF-2026-0001)."
            )
        if sessao is not None:
            sessao["aguardando_id"] = None
        return consultar.consultar_pedido(numero, sessao.get("nome_cliente") if sessao else None)["mensagem"]

    # ── UPDATE: alterar um campo do pedido ───────────────────────
    if intencao == "alterar_pedido_especifico":
        numero = slots.get("numero_pedido")
        campo, valor = _detectar_alteracao(mensagem, slots)
        # Recupera a alteração que guardamos enquanto pedíamos o ID.
        if (campo is None or valor is None) and sessao and sessao.get("alteracao_pendente"):
            campo = sessao["alteracao_pendente"].get("campo")
            valor = sessao["alteracao_pendente"].get("valor")
        if not numero:
            # Falta o ID → pergunta e guarda o que o cliente quer mudar.
            if sessao is not None:
                sessao["aguardando_id"] = "alterar_pedido_especifico"
                sessao["alteracao_pendente"] = {"campo": campo, "valor": valor}
            return (
                "Pra alterar, me informa o número do pedido (FF-AAAA-NNNN). Lembrando: "
                "só dá pra alterar enquanto está na etapa de modelagem."
            )
        if sessao is not None:
            sessao["aguardando_id"] = None
        if not campo or valor is None:
            if sessao is not None:
                sessao["alteracao_pendente"] = None
            return (
                f"O que você quer mudar no pedido {numero}? Posso alterar cor, tamanho, "
                "quantidade, tecido ou personalização — e me diz pro quê. "
                "Ex: 'mudar a cor para branco'."
            )
        resultado = atualizar.alterar_campo(numero, campo, valor, sessao.get("nome_cliente") if sessao else None)
        if sessao is not None:
            sessao["alteracao_pendente"] = None
        return resultado["mensagem"]

    # Obs: NÃO existe handler de "avançar etapa" aqui. Avançar a peça na esteira
    # (modelagem -> corte -> ...) é ação da produção interna, não do cliente. A
    # função atualizar.avancar_etapa existe e é testada, mas não é exposta no chat.

    # ── Viabilidade de produção ──────────────────────────────────
    if intencao == "viabilidade_producao":
        quantidade = slots.get("quantidade", 0)
        tecido = slots.get("tecido")
        prazo = slots.get("prazo_desejado")
        urgente = slots.get("urgente", False)

        df_cap = dados["capacidade_produtiva"]
        df_est = dados["estoque_materiais"]

        costura = df_cap[df_cap["setor"] == "costura"].iloc[0]
        cap_disponivel = int(costura["disponivel_hoje_pecas"])
        viavel_capacidade = quantidade <= cap_disponivel

        material_msg = ""
        material_ok = True
        if tecido:
            row_mat = df_est[df_est["tecido"] == tecido]
            if not row_mat.empty:
                r = row_mat.iloc[0]
                material_ok = r["status"] == "disponivel"
                if not material_ok:
                    material_msg = (
                        f" Porém, {tecido.replace('_', ' ')} está sem estoque "
                        f"(reposição em {r['previsao_reposicao']})."
                    )
                else:
                    material_msg = (
                        f" {tecido.replace('_', ' ').title()} disponível "
                        f"({r['metros_disponivel']}m em estoque)."
                    )

        aviso_urgencia = ""
        if urgente:
            aviso_urgencia = " Notei que é urgente — taxa de urgência aplicada é de 20% a 40%."

        if prazo and prazo < 15:
            return (
                f"Para {quantidade} {pecas(quantidade)} em {prazo} dias: nosso prazo mínimo é de "
                "15 dias úteis (sem personalização). "
                f"A capacidade do setor de costura é de {cap_disponivel} peças/dia.{material_msg}{aviso_urgencia} "
                "Para esse prazo, vendas avalia taxa de urgência."
            )

        if viavel_capacidade and material_ok:
            return (
                f"Sim, temos capacidade técnica para produzir {quantidade} {pecas(quantidade)}. "
                f"O setor de costura tem {cap_disponivel} peças disponíveis hoje.{material_msg}{aviso_urgencia} "
                "Para confirmar, fale com vendas."
            )
        else:
            motivos = []
            if not viavel_capacidade:
                motivos.append(
                    f"a capacidade disponível hoje é de {cap_disponivel} peças "
                    f"e você solicitou {quantidade}"
                )
            if not material_ok:
                motivos.append(material_msg.strip())
            return (
                f"Pode haver dificuldades para produzir {quantidade} {pecas(quantidade)} agora: "
                f"{'; '.join(motivos)}.{aviso_urgencia} "
                "Fale com vendas para avaliar alternativas."
            )

    # ── Consumo de tecido ────────────────────────────────────────
    if intencao == "consumo_tecido":
        quantidade = slots.get("quantidade", 0)
        produto = slots.get("produto")
        tecido = slots.get("tecido")
        metragem = slots.get("metragem", 0)

        df = dados["consumo_tecido"]
        filtro = df[df["produto"] == produto]
        if tecido:
            filtro_tec = filtro[filtro["tecido_principal"] == tecido]
            if not filtro_tec.empty:
                filtro = filtro_tec

        if filtro.empty:
            return (
                f"Não tenho dados de consumo para {produto or 'esse produto'}. "
                "Fale com o setor técnico."
            )

        metros_por_peca = float(filtro.iloc[0]["metros_por_peca"])
        metros_necessarios = round(metros_por_peca * quantidade, 2)
        obs = filtro.iloc[0]["observacao"]

        if metragem > 0:
            if metragem >= metros_necessarios:
                sobra = round(metragem - metros_necessarios, 2)
                return (
                    f"Para {quantidade} {pecas(quantidade)} de {produto.replace('_',' ')}, "
                    f"precisa de {metros_necessarios}m ({metros_por_peca}m por peça). "
                    f"Com {metragem}m você tem o suficiente — sobram {sobra}m. Obs: {obs}"
                )
            else:
                falta = round(metros_necessarios - metragem, 2)
                return (
                    f"Para {quantidade} {pecas(quantidade)} de {produto.replace('_',' ')}, "
                    f"precisa de {metros_necessarios}m ({metros_por_peca}m por peça). "
                    f"Com apenas {metragem}m, faltam {falta}m. Obs: {obs}"
                )

        return (
            f"Para {quantidade} {pecas(quantidade)} de {produto.replace('_',' ')}, "
            f"precisa de aproximadamente {metros_necessarios}m ({metros_por_peca}m por peça). Obs: {obs}"
        )

    # ── Prazo ────────────────────────────────────────────────────
    if intencao in ("combinado_prazo_qtd_produto", "combinado_prazo_personalizacao_produto"):
        quantidade = slots.get("quantidade", 0)
        produto = slots.get("produto")
        personalizacao = slots.get("personalizacao", "nenhuma")
        urgente = slots.get("urgente", False)
        prazo_desejado = slots.get("prazo_desejado")
        # ALTO 30: produto inexistente vira esclarecimento
        if not produto:
            return (
                "Pra calcular prazo eu preciso saber qual produto você quer. "
                "Trabalhamos com camisetas, polos, moletons, vestidos, calças, uniformes e mais. "
                "Qual deles?"
            )
        if not quantidade:
            pers_txt = f" com {personalizacao}" if personalizacao != "nenhuma" else ""
            return (
                f"Consigo estimar o prazo de {produto.replace('_',' ')}{pers_txt}, "
                "mas preciso da quantidade de peças. Quantas unidades você quer produzir?"
            )

        df = dados["prazo"]
        filtro = df[
            (df["produto"] == produto) &
            (df["qtd_min"] <= quantidade) &
            (df["qtd_max"] >= quantidade) &
            (df["personalizacao"] == personalizacao)
        ]
        if filtro.empty:
            filtro = df[
                (df["produto"] == produto) &
                (df["qtd_min"] <= quantidade) &
                (df["qtd_max"] >= quantidade)
            ]
        if filtro.empty:
            # MÉDIO 31: mensagem específica pra quantidades muito altas
            qtd_max = df[df["produto"] == produto]["qtd_max"].max() if not df[df["produto"] == produto].empty else 0
            if quantidade > qtd_max:
                return (
                    f"{quantidade} peças é um pedido grande — acima da nossa tabela padrão "
                    f"(máximo tabelado: {qtd_max}). Pra esse volume é orçamento especial com vendas, "
                    "geralmente em fases (lotes de 100-200 peças) e prazo planejado."
                )
            return (
                f"Não encontrei dados de prazo para {produto.replace('_',' ')} com quantidade {quantidade}. "
                "Fale com vendas pra estimativa personalizada."
            )
        r = filtro.iloc[0]
        pers_txt = f" com {personalizacao}" if personalizacao != "nenhuma" else ""
        prazo_min = int(r['prazo_min_dias'])
        prazo_max = int(r['prazo_max_dias'])

        aviso = ""
        # MÉDIO 17 + urgência: usa o slot urgente que estava sendo ignorado
        if urgente or (prazo_desejado and prazo_desejado < prazo_min):
            aviso = (
                f" Pelo prazo desejado ({prazo_desejado} dias) ser mais curto que o normal, "
                if prazo_desejado and prazo_desejado < prazo_min else " Notei que é urgente — "
            ) + "aplicamos taxa de urgência de 20% a 40%. Fale com vendas pra avaliar."

        return (
            f"Para {quantidade} {pecas(quantidade)} de {produto.replace('_',' ')}{pers_txt}: "
            f"prazo estimado de {prazo_min} a {prazo_max} dias úteis.{aviso} "
            "Prazo confirmado pelo setor de vendas no fechamento do pedido."
        )

    if intencao == "combinado_preco_personalizacao":
        produto = slots.get("produto")
        quantidade = slots.get("quantidade")
        personalizacao = slots.get("personalizacao")
        tecnica = f" de {personalizacao}" if personalizacao and personalizacao != "nenhuma" else ""
        if produto and quantidade:
            # Reaproveita a tabela de preço quando já há produto e quantidade.
            slots = dict(slots)
            slots["personalizacao"] = personalizacao or "nenhuma"
            return responder("combinado_preco_qtd_produto", slots, dados, sessao, mensagem)
        base = (
            f"A personalização{tecnica} costuma acrescentar de 10% a 40% sobre o valor base, "
            "dependendo da técnica, tamanho da arte, número de cores e volume. "
        )
        if not produto or not quantidade:
            return base + "Pra estimar melhor, me diga produto e quantidade de peças."
        return base + "O fechamento do valor final é com vendas."

    # ── Preço ────────────────────────────────────────────────────
    if intencao == "combinado_preco_qtd_produto":
        quantidade = slots.get("quantidade", 0)
        produto = slots.get("produto")
        personalizacao = slots.get("personalizacao", "nenhuma")
        if sessao and sessao.get("tipo_turno") == "correcao_orcamento" and not re.search(
            r'preco|preço|valor|custa|quanto fica|orcamento|orçamento|sai por', normalizar(mensagem or "")
        ):
            return (
                f"Corrigi o orçamento para {quantidade} {pecas(quantidade)} de "
                f"{produto.replace('_',' ') if produto else 'produto ainda não definido'}. "
                "Se quiser, eu calculo o valor estimado."
            )
        if not produto:
            return (
                "Pra calcular preço eu preciso saber qual produto você quer. "
                "Trabalhamos com camisetas, polos, moletons, vestidos, calças, uniformes e mais. "
                "Qual deles?"
            )

        df = dados["preco"]
        filtro = df[
            (df["produto"] == produto) &
            (df["qtd_min"] <= quantidade) &
            (df["qtd_max"] >= quantidade) &
            (df["personalizacao"] == personalizacao)
        ]
        if filtro.empty:
            filtro = df[
                (df["produto"] == produto) &
                (df["qtd_min"] <= quantidade) &
                (df["qtd_max"] >= quantidade)
            ]
        if filtro.empty:
            qtd_max = df[df["produto"] == produto]["qtd_max"].max() if not df[df["produto"] == produto].empty else 0
            if quantidade > qtd_max:
                return (
                    f"{quantidade} peças é um volume bem grande — fora da nossa tabela "
                    f"(máximo: {qtd_max}). Pra esse pedido vale orçamento especial com vendas, "
                    "tem desconto progressivo a partir de 500 peças."
                )
            return (
                f"Não encontrei dados de preço para {produto.replace('_',' ')} com quantidade {quantidade}. "
                "Fale com vendas pra orçamento personalizado."
            )
        r = filtro.iloc[0]
        total = round(float(r["preco_unitario_estimado"]) * quantidade, 2)
        pers_txt = f" com {personalizacao}" if personalizacao != "nenhuma" else ""
        return (
            f"Para {quantidade} {pecas(quantidade)} de {produto.replace('_',' ')}{pers_txt}: "
            f"valor unitário estimado de R$ {r['preco_unitario_estimado']} "
            f"({r['desconto_aplicado']} de desconto). "
            f"Total estimado: R$ {total:.2f}. "
            "Valor indicativo — fechamento com vendas."
        )

    # ── Compatibilidade tecido × personalização ──────────────────
    if intencao == "combinado_personalizacao_em_tecido":
        tecido = slots.get("tecido")
        personalizacao = slots.get("personalizacao")
        df = dados["compat_tecido_personalizacao"]
        filtro = df[(df["tecido"] == tecido) & (df["personalizacao"] == personalizacao)]
        if filtro.empty:
            return f"Não tenho dados sobre {personalizacao} em {tecido}. Consulte o setor técnico."
        r = filtro.iloc[0]
        obs = str(r["observacao"]).strip()
        obs = obs[:1].upper() + obs[1:] if obs else obs
        if r["compativel"].strip().lower() == "sim":
            return f"Sim! {obs}"
        return obs

    # ── Compatibilidade tecido × produto ─────────────────────────
    if intencao == "combinado_tecido_em_produto":
        tecido = slots.get("tecido")
        produto = slots.get("produto")
        df = dados["compat_tecido_produto"]
        filtro = df[(df["tecido"] == tecido) & (df["produto"] == produto)]
        if filtro.empty:
            return f"Não tenho dados sobre {tecido} em {produto}. Consulte o setor técnico."
        r = filtro.iloc[0]
        obs = str(r["observacao"]).strip()
        obs = obs[:1].upper() + obs[1:] if obs else obs
        if r["compativel"].strip().lower() == "sim":
            return f"Sim! {obs}"
        return obs

    # ── Quais tecidos combinam com um produto ────────────────────
    # (Antes esse id tinha uma resposta PLACEHOLDER de dev no CSV — "Consultar
    # lookup... e listar". Agora lista de verdade os tecidos compatíveis.)
    if intencao == "combinado_tecidos_disponiveis_para_produto":
        produto = slots.get("produto")
        if not produto:
            return ("Pra qual produto? (ex: camiseta, moletom, calça, vestido...) "
                    "Aí eu listo os tecidos que combinam.")
        df = dados["compat_tecido_produto"]
        compat = df[(df["produto"] == produto)
                    & (df["compativel"].str.strip().str.lower() == "sim")]
        if compat.empty:
            return (f"Não tenho tecidos cadastrados como ideais para "
                    f"{produto.replace('_',' ')}. Consulte o setor técnico.")
        tecidos = ", ".join(t.replace("_", " ") for t in compat["tecido"].tolist())
        return f"Para {produto.replace('_',' ')}, os tecidos recomendados são: {tecidos}."

    # ── Cores disponíveis para tecido ────────────────────────────
    if intencao == "combinado_cores_disponiveis_para_tecido":
        tecido = slots.get("tecido")
        if not tecido:
            return "Pra qual tecido? Exemplos: algodão, moletom, viscose, jeans ou linho."
        df = dados["cor_tecido"]
        filtro = df[df["tecido"] == tecido]
        if filtro.empty:
            return f"Não tenho cores cadastradas para {tecido.replace('_',' ')}. Consulte vendas para cor sob demanda."
        estoque = filtro[filtro["disponibilidade"].astype(str).str.strip().str.lower() == "estoque"]
        base = estoque if not estoque.empty else filtro
        cores = ", ".join(c.replace("_", " ") for c in base["cor"].tolist())
        sufixo = "em estoque permanente" if not estoque.empty else "cadastradas/sob demanda"
        return f"Para {tecido.replace('_',' ')}, as cores {sufixo} são: {cores}."

    # ── Cor em tecido ────────────────────────────────────────────
    if intencao == "combinado_cor_em_tecido":
        cor = slots.get("cor")
        tecido = slots.get("tecido")
        # Sem tecido (ou sem cor) não dá pra consultar a matriz cor×tecido — e a
        # gente NÃO pode responder "... em None". A pessoa provavelmente só citou
        # uma cor: mostramos a paleta em estoque (cores_basicas).
        if not tecido or not cor:
            linha = dados["intencoes"][dados["intencoes"]["id_intencao"] == "cores_basicas"]
            if not linha.empty:
                return linha.iloc[0]["resposta_padrao"]
            return ("Me diz a cor e o tecido (ex: 'preto em algodão') que eu confiro a "
                    "disponibilidade — ou pergunta pelas cores em estoque.")
        df = dados["cor_tecido"]
        filtro = df[(df["tecido"] == tecido) & (df["cor"] == cor)]
        if filtro.empty:
            return (f"Não tenho dados sobre a cor {cor.replace('_',' ')} em "
                    f"{tecido.replace('_',' ')}. Consulte o setor de vendas.")
        r = filtro.iloc[0]
        disp = "em estoque permanente" if r["disponibilidade"] == "estoque" else "sob demanda (mínimo 80 peças + 7 a 10 dias)"
        return f"A cor {cor.replace('_',' ')} em {tecido.replace('_',' ')} está {disp}."

    # ── Gramatura ────────────────────────────────────────────────
    if intencao == "combinado_gramatura_produto_uso":
        produto = slots.get("produto")
        uso = slots.get("uso")
        df = dados["gramatura"]
        filtro = df[df["produto"] == produto]
        if uso:
            filtro_uso = filtro[filtro["uso"] == uso]
            if not filtro_uso.empty:
                filtro = filtro_uso
        if filtro.empty:
            return f"Não tenho dados de gramatura para {produto}. Consulte o setor técnico."
        r = filtro.iloc[0]
        return (
            f"Gramatura recomendada para {produto.replace('_',' ')} "
            f"({r['uso']}): {r['gramatura_min_g_m2']} a {r['gramatura_max_g_m2']} g/m². "
            f"{r['observacao']}"
        )

    # ── Tamanho / grade ──────────────────────────────────────────
    if intencao == "combinado_tamanho_em_produto":
        produto = slots.get("produto")
        grade = slots.get("grade")
        df = dados["tamanho_produto"]
        filtro = df[(df["produto"] == produto) & (df["grade"] == grade)]
        if filtro.empty:
            return f"Não tenho dados de grade {grade} para {produto}. Consulte o setor de vendas."
        r = filtro.iloc[0]
        disp = "disponível" if r["disponivel"] == "sim" else "não disponível"
        return (
            f"Grade {grade.replace('_',' ')} para {produto.replace('_',' ')}: {disp}. "
            f"{r['observacao']}"
        )

    # ── Fora do catálogo: NEGA e REAFIRMA o que a gente faz ──────
    # (o professor pediu esse comportamento com o exemplo da "moto".)
    if intencao == "cat_nao_fazemos":
        from bot.classifier import item_fora_catalogo
        item = item_fora_catalogo(mensagem)
        nega = (f"Não trabalhamos com {item} — " if item
                else "Isso não faz parte do que a gente produz — ")
        return (nega + "a Fashion Flow é uma confecção de vestuário. Nós fazemos: "
                f"{_reafirma_produtos(dados)}. Quer saber de algum desses?")

    # ── Detalhe de um produto específico (ex: "premium") ─────────
    if intencao == "produto_detalhe":
        produto = slots.get("produto")
        linha = dados["produtos"][dados["produtos"]["produto"] == produto]
        if linha.empty:
            return (f"A Fashion Flow faz: {_reafirma_produtos(dados)}. "
                    "Sobre qual você quer saber?")
        r = linha.iloc[0]
        return f"{r['nome']}: {r['descricao']}. (Categoria: {r['categoria']}.)"

    # ── Resposta padrão do CSV ──────────────────────────────────
    # O CSV é base de conhecimento/keywords. Fluxos internos, CRUD e respostas
    # calculadas precisam ter handler acima; se chegarem aqui, é bug controlado.
    if intencao in EXIGE_HANDLER:
        return (
            "Consigo ajudar com isso, mas faltou uma regra interna para concluir a resposta. "
            "Pode reformular ou informar produto, quantidade e detalhes do pedido?"
        )

    df_int = dados["intencoes"]
    row = df_int[df_int["id_intencao"] == intencao]
    if not row.empty:
        resposta = row.iloc[0]["resposta_padrao"]
        followup = row.iloc[0]["pergunta_followup"]
        followup_txt = str(followup) if followup and str(followup) != "nan" else ""

        if intencao in MENUS and "|" in followup_txt and not _quer_menu(mensagem):
            direta = _resposta_menu_direta(intencao, slots, dados)
            if direta:
                return direta + " Se quiser, posso listar as opções."

        if followup_txt:
            if "|" in followup_txt:
                if sessao:
                    sessao["aguardando_opcao"] = f"menu_{intencao}"
                opcoes = followup_txt.split("|")
                # tira o rótulo "Escolha uma opção:" que veio colado na 1ª opção
                opcoes[0] = re.sub(r'(?i)^\s*escolha uma op[çc][aã]o:\s*', '',
                                   opcoes[0]).strip()
                lista = "\n".join(f"  {i+1}. {o.strip()}" for i, o in enumerate(opcoes))
                return f"{resposta}\n{lista}"
            return f"{resposta}\n{followup_txt}"
        return resposta

    # ── Fallback ─────────────────────────────────────────────────
    # Se a sessão tem produto no foco, cita o produto e oferece caminhos concretos
    # (Grice/relevância — evita mensagem genérica quando há contexto).
    foco_produto = (slots or {}).get("produto") or (sessao or {}).get("foco_atual", {}).get("produto")
    if foco_produto:
        nome_produto = foco_produto.replace("_", " ")
        return (
            f"Não peguei essa. Sobre {nome_produto}, quer saber preço, prazo, "
            "cores, tecidos, personalização ou cuidados? É só me dizer qual desses."
        )
    return (
        "Não entendi bem sua pergunta. Posso ajudar com: "
        "prazos, preços, tecidos, personalização, compatibilidade, "
        "gramatura, tamanhos e status de pedidos. Pode reformular?"
    )
