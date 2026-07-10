"""
Classificação de intenção a partir da mensagem + slots + contexto.

Recebe DOIS dicionários de slots:
- slots_turno:    o que o usuário disse AGORA (sem herança de contexto)
- slots_efetivos: foco_atual + slots_turno (com herança)

A separação evita bugs onde uma regra dispara só porque um slot herdado
ainda está na sessão (ex: CRÍTICO 5 — numero_pedido fazendo qualquer
mensagem virar status_pedido).
"""
import re
from rapidfuzz import fuzz

from bot.normalizar import normalizar
from bot.politica import numero_solto_de_correcao


# Itens que a Fashion Flow claramente NÃO faz (fora de vestuário). Serve pra o bot
# NEGAR e reafirmar o catálogo — o professor pediu isso com o exemplo da "moto".
FORA_CATALOGO = (
    r'\b(motos?|carros?|veiculos?|automoveis?|bicicletas?|bikes?|patins|skates?|'
    r'sapatos?|tenis|sandalias?|chinelos?|botas?|calcados?|salto|'
    r'bolsas?|mochilas?|carteiras?|cintos?|oculos|relogios?|joias?|aneis|colares?|brincos?|'
    r'celulares?|telefones?|computadores?|notebooks?|tablets?|eletronicos?|geladeiras?|'
    r'fogao|fogoes|microondas|televisao|tvs?|moveis|movel|sofas?|'
    r'remedios?|brinquedos?|drones?|pneus?|armas?|foguetes?)\b'
)


def item_fora_catalogo(texto):
    """Devolve o item fora do catálogo citado na mensagem (ex: 'moto'), ou None."""
    m = re.search(FORA_CATALOGO, normalizar(texto))
    return m.group(0) if m else None


# Intenções que só fazem sentido COM slots (produto/tecido/cor/quantidade/uso).
# São alcançadas pelas regras de slot (etapa 6/7); NÃO podem ser pescadas por
# similaridade fuzzy (etapa 9) — senão um typo casa por acaso e o responder monta
# resposta com "None" (ex: "grade None para None").
_SO_POR_SLOT = {
    "combinado_tecido_em_produto", "combinado_cor_em_tecido",
    "combinado_tamanho_em_produto", "combinado_gramatura_produto_uso",
    "combinado_personalizacao_em_tecido", "combinado_tecidos_disponiveis_para_produto",
    "combinado_cores_disponiveis_para_tecido", "combinado_prazo_qtd_produto",
    "combinado_preco_qtd_produto", "combinado_prazo_personalizacao_produto",
    "combinado_preco_personalizacao", "consumo_tecido", "viabilidade_producao",
    "produto_detalhe",
}


# Tópicos macro pra detecção de MULTI-INTENÇÃO. Quando a mensagem toca 3+
# tópicos distintos e nenhuma intenção composta (combinado_*) fechou, o bot
# lista o que entendeu e pergunta por qual começar — em vez de escolher uma
# arbitrariamente e ignorar o resto. As regex são propositalmente conservadoras
# (só palavras de contexto claro) pra não disparar em mono-intenção.
_TOPICOS_MULTI = {
    "prazo":         r'\bprazo\b|\bdias?\b|quando fica|quanto tempo|\bdemora\b',
    "preco":         r'\bpreco\b|\bpreço\b|\bvalor\b|\bcusta\b|orcamento|sai por',
    "produto":       r'\bcamise\w*|\bmoleto\w*|\bpolos?\b|\bcalcas?\b|\bcalças?\b|'
                     r'\bvestidos?\b|\bjaquetas?\b|\bbermudas?\b|\bregatas?\b|'
                     r'\bleggings?\b|\buniforme\w*|\bjalecos?\b|\bjeans\b',
    "cor":           r'\bcor(es)?\b',
    "tecido":        r'\btecidos?\b|\balgodao\b|\blinho\b|\bviscose\b|\bsuplex\b',
    "cuidados":      r'\bcuido\b|\bcuidar\b|\blavar?\b|\blavo\b|encolh\w*|desbot\w*|amass\w*',
    "tamanho":       r'\btamanhos?\b|\bgrade\b|numeracao|plus.?size',
    "personalizacao": r'estamp\w*|bordad\w*|\bsilk\w*|\bdtf\b|serigrafia',
    "entrega":       r'entreg\w*|\benvi\w*|\bfrete\b|correios',
}
_TOPICOS_LABELS = {
    "prazo": "prazo", "preco": "preço", "produto": "catálogo de produtos",
    "cor": "cores", "tecido": "tecidos", "cuidados": "cuidados com a peça",
    "tamanho": "tamanhos", "personalizacao": "personalização", "entrega": "entrega",
}


def _detectar_topicos_multi(texto):
    """Retorna o conjunto de tópicos macro que a mensagem toca."""
    return {nome for nome, rx in _TOPICOS_MULTI.items() if re.search(rx, texto)}


def pontuar_candidatas(mensagem, intencoes, top=3):
    """
    Score de CONFIANÇA das intenções — o "recalcular a intenção" que o professor
    pediu. Pontua TODAS as intenções (palavra-chave + fuzzy, ponderado pelo peso)
    e devolve as `top` mais fortes, RE-RANQUEADAS por score.

    - match exato de palavra-chave (fronteira de palavra) → força 1.0
    - senão, similaridade fuzzy (0 a 1)
    - score final = força × (0.6 + 0.4 × peso/9)  → dá pra ver quão "certo" o bot está.

    É transparência/decisão: o classificar() calcula isso todo turno e guarda na
    sessão, e o /contexto (terminal) e /sessao (web) mostram as candidatas.
    """
    t = normalizar(mensagem)
    ranking = []
    for _, row in intencoes.iterrows():
        keywords = str(row["palavras_chave"]).strip()
        if not keywords or keywords == "nan":
            continue
        peso = _peso(row)
        melhor, tipo = 0.0, None
        for kw in keywords.split("|"):
            kw = normalizar(kw.strip())
            if not kw:
                continue
            padrao = (r'\b' + re.escape(kw)) if kw[0].isalnum() else re.escape(kw)
            if re.search(padrao, t):
                melhor, tipo = 1.0, "palavra-chave"
                break
            if len(kw) >= 4 and len(t) >= len(kw) * 0.5:
                sc = fuzz.partial_ratio(kw, t) / 100.0
                if sc > melhor:
                    melhor, tipo = sc, "similaridade"
        if melhor > 0:
            score = round(melhor * (0.6 + 0.4 * peso / 9.0), 3)
            ranking.append({"intencao": row["id_intencao"], "score": score, "por": tipo})
    ranking.sort(key=lambda c: c["score"], reverse=True)
    return ranking[:top]


def _peso(row):
    """
    Lê o PESO da intenção (coluna 'peso' do intencoes.csv). É o número que
    decide quem ganha quando mais de uma intenção bate na mesma frase:
    quanto maior o peso, mais a intenção tem prioridade. Se faltar, usa 5.
    """
    try:
        p = float(row.get("peso", 5))
        return p if p == p else 5.0   # p == p é False quando é NaN
    except (TypeError, ValueError):
        return 5.0



def _parece_pergunta(texto):
    return bool(re.search(
        r'\?|\b(qual|quais|quanto|quantos|quando|como|onde|por que|porque|pode|posso|tem|aceita|trabalha|fazem|da pra|dá pra)\b',
        texto
    ))


def _parece_status_pedido_existente(texto):
    return bool(re.search(
        r'\b(fiz|tenho|ja fiz|já fiz|abri|fechei)\b.{0,30}\bpedido\b|'
        r'\bpedido\b.{0,30}\b(semana passada|ontem|mes passado|mês passado|anterior|antigo|existente)\b|'
        r'\b(como|onde)\s+(ta|esta)\b.{0,20}\bpedido\b|'
        r'\bquero saber\b.{0,25}\bpedido\b',
        texto
    ))


def _escolha_curta_topico(texto):
    mapa = {
        'preco': 'setor_vendas', 'preço': 'setor_vendas', 'valor': 'setor_vendas',
        'prazo': 'previsao_prazo', 'tempo': 'previsao_prazo',
        'cor': 'personalizacao_cores', 'cores': 'personalizacao_cores',
        'tecido': 'tecidos', 'tecidos': 'tecidos',
        'tamanho': 'personalizacao_tamanhos', 'tamanhos': 'personalizacao_tamanhos',
        'grade': 'personalizacao_tamanhos',
        'personalizacao': 'personalizacao', 'personalização': 'personalizacao',
        'qualidade': 'qualidade', 'lavagem': 'manutencao', 'lavar': 'manutencao',
        'cuidado': 'manutencao', 'cuidados': 'manutencao',
        'tipos': 'personalizacao_tipos', 'tipo': 'personalizacao_tipos',
        'catalogo': 'catalogo', 'catálogo': 'catalogo', 'uniforme': 'cat_uniformes',
    }
    chave = re.sub(r'[^a-z0-9 çãáéíóúâêô]+', '', texto).strip()
    return mapa.get(chave)


def _numero_solto(texto):
    # Aceita: "100", "e 100?", "e se for 50", "pra 300", "de 20", "tbm de 20"
    # (tbm→tambem via normalizar). Prefixos comuns de refinamento de orçamento.
    m = re.fullmatch(
        r'\s*(?:e\s+)?(?:tambem\s+)?(?:(?:se\s+)?(?:for|forem|fosse|fossem)\s+)?'
        r'(?:pra|para|de)?\s*(\d+)\s*\??\s*', texto)
    return int(m.group(1)) if m else None

def classificar(mensagem, slots_turno, slots_efetivos, intencoes, sessao=None):
    """
    Retorna o id da intenção classificada.
    """
    t = normalizar(mensagem)

    # Score de confiança / re-ranking das intenções — guardado na sessão pra o
    # /contexto e /sessao mostrarem (o "recalcular a intenção" pedido em sala).
    if sessao is not None:
        candidatas = pontuar_candidatas(mensagem, intencoes)
        sessao["intencao_candidatas"] = candidatas
        sessao["confianca"] = candidatas[0]["score"] if candidatas else 0.0

    # ── 0. Aguardando opção de menu ──────────────────────────────
    if sessao and sessao.get("aguardando_opcao"):
        return "selecao_opcao"

    # ── 0c. Palavras de NAVEGAÇÃO soltas (menu/ajuda/voltar/opcoes) ──
    # Sozinhas, viravam intenções aleatórias no fuzzy ("menu" casava com
    # "meu pedido", "voltar" com "dinheiro de volta"). Aqui a gente força
    # elas caírem na saudação, que já lista os tópicos que o bot cobre.
    # "opa" saiu das keywords do CSV (disparava saudação no MEIO de frases tipo
    # "opa espera, minha socia quer verde"); aqui só conta quando é a mensagem toda.
    if re.fullmatch(r'\s*(menu|ajuda|help|opcao|opcoes|voltar|inicio|comecar|opa)\s*[.!?]*', t):
        return "saudacao"

    topico_curto = _escolha_curta_topico(t)
    if topico_curto:
        return topico_curto

    tipo_turno = (sessao or {}).get("tipo_turno") if sessao else None

    if re.search(r'porcaria de bot|nao presta|não presta|pessim[oa]|horrivel|horrível|inutil|inútil|ruim demais', t):
        return "ofensas"
    if re.fullmatch(r'(que legal|legal demais|muito bom|perfeito|excelente|otimo|ótimo|show|top)', t):
        return "elogios1"

    if re.search(r'\b(arte|arquivo|layout|vetor|png|cdr|pdf|svg)\b', t) and re.search(r'envi|mand|formato|aceit|resoluc', t):
        return "personalizacao_envio_arte"
    if re.search(r'preco da personaliz|preço da personaliz|quanto custa personaliz|valor da personaliz', t):
        return "combinado_preco_personalizacao"
    if slots_turno.get("tecido") and slots_turno.get("personalizacao") and re.search(r'estampar|bordar|personaliz|posso|pode|da pra|dá pra', t):
        return "combinado_personalizacao_em_tecido"
    if slots_turno.get("produto") and slots_turno.get("grade"):
        return "combinado_tamanho_em_produto"
    if slots_turno.get("tecido") and slots_turno.get("cor") and re.search(r'\btem\b|disponiv|estoque|cor|pronta entrega', t):
        return "combinado_cor_em_tecido"
    if re.search(r'cor personalizada|cor especifica|cor específica|cor especial|pantone|tingimento|tingir', t):
        return "cores_sob_demanda"
    if re.search(r'cores?.{0,20}pronta entrega|cores?.{0,20}estoque|quais cores|que cores', t):
        if slots_turno.get("tecido"):
            return "combinado_cores_disponiveis_para_tecido"
        return "cores_basicas"
    if re.search(r'pronta entrega|pecas? pronta|peças? pronta|envio imediato', t):
        return "pronta_entrega"
    if re.search(r'prazo .*personaliz|prazo com personaliz|tempo .*personaliz|demora .*personaliz', t):
        return "prazo_com_personalizacao"
    if re.search(r'prazo .*produc|tempo de produc|prazo medio de produc|prazo médio de produc', t):
        return "prazo_padrao"

    if re.search(r'customiza|customizac|personaliza|personalizac|estampar|estampa personalizada', t):
        if re.search(r'minim|mínim|quantas pecas|quantas peças', t):
            return "personalizacao_quantidade"
        return "personalizacao"
    if re.search(r'minim|mínim|pedido minimo|pedido mínimo', t) and re.search(r'silk|bordad|dtf|personaliz', t):
        return "personalizacao_quantidade"

    if re.search(r'\b(frete|envio|entrega|rastreio|rastreamento|codigo de rastreio|código de rastreio)\b', t):
        return "setor_logistica"
    if re.search(r'material dispon|materia prima|matéria-prima|tem material|disponibilidade', t):
        return "disponibilidade_materiais"
    if re.search(r'como vendo pra voces|quero fornecer|fornecer tecido|sou fornecedor|setor de compras|vender tecido pra voces', t):
        return "setor_compras"

    if re.search(r'aproveita.*tecido|desperdicio|desperdício|sobras? de corte', t):
        return "sustent_aproveitamento"
    if re.search(r'trabalho digno|condicoes de trabalho|condições de trabalho|trabalho escravo|trabalho infantil|clt|facção|faccao', t):
        return "sustent_trabalho"
    if re.search(r'caixa recicl|embalagem recicl|embalagem sustent|logistica sustent', t):
        return "sustent_logistica"

    if re.search(r'o que da pra fazer|o que voces fazem|quais pecas voces produzem|que tipo de produto fazem', t):
        return "catalogo"
    if re.search(r'\b(tem|fazem|voces fazem|produzem|vendem|trabalham com|da pra fazer)\b', t) and slots_turno.get("produto") \
       and not re.search(r'\bpreco|preço|valor|prazo|tempo|quantas|tamanho|grade|cor(es)?|tecido\b', t):
        produto_catalogo = {
            "camiseta_basica": "cat_camisetas", "camiseta_premium": "produto_detalhe",
            "polo": "cat_camisetas", "baby_look": "cat_camisetas", "regata": "cat_camisetas",
            "oversized": "cat_camisetas", "moletom": "cat_moletons", "jaqueta": "cat_moletons",
            "calca_jeans": "cat_calcas", "calca_alfaiataria": "cat_calcas", "legging": "cat_calcas",
            "bermuda": "cat_calcas", "jogger": "cat_calcas", "vestido_midi": "cat_vestidos",
            "vestido_longo": "cat_vestidos", "uniforme_polo": "cat_uniformes", "uniforme_jaleco": "cat_uniformes",
        }
        return produto_catalogo.get(slots_turno["produto"], "catalogo")

    if re.search(r'qual peca.*recomenda|qual peça.*recomenda|me recomenda|sugere uma peca|sugere uma peça', t):
        return "sugestao_produto"
    if re.search(r'prazo curto|pedido urgente|urgente|pra ontem|adiantar prazo', t):
        return "prazo_urgente"
    if re.search(r'prazo.*pedido grande|prazo.*atacado', t):
        return "prazo_grande_pedido"
    if re.search(r'\b(consigo|conseguem|viavel|viável|da pra|dá pra)\b', t) and slots_efetivos.get("quantidade"):
        return "viabilidade_producao"
    if slots_efetivos.get("produto") and re.search(r'quanto ta|quanto tá|quanto custa|preco|preço|valor', t) \
       and not slots_efetivos.get("quantidade") and not re.search(r'\d+', t):
        return "setor_vendas"
    if re.search(r'quanto mais.*barat|desconto.*volume|desconto progressivo', t):
        return "combinado_desconto_volume"
    if re.search(r'tecido grosso|tecido fino|gramatura', t) and slots_efetivos.get("produto"):
        return "combinado_gramatura_produto_uso"
    if re.search(r'\b(rastrear|acompanhar|status|modificar|alterar|mudar)\b.*\bpedido\b', t):
        if re.search(r'modificar|alterar|mudar', t):
            return "alterar_pedido_especifico"
        return "status_pedido"
    if re.search(r'tamanho errado|veio tamanho errado|trocar peca|trocar peça|devolu|reembolso', t):
        return "setor_devolucao"
    if re.search(r'\batendem empresa\b|vendem pra empresa|venda pra empresa|atendimento b2b|cnpj|pessoa juridica|pessoa jurídica', t):
        return "atende_empresa"
    if re.search(r'uniforme escolar|uniforme de escola|farda escolar', t):
        return "uniforme_escolar"
    if re.search(r'produzem pra minha marca|private label|marca propria|marca própria', t):
        return "private_label"

    # Problemas reais do cliente precisam vencer menu, setor genérico e keyword de
    # produção. Aqui a intenção é resolver/triagem, não explicar teoria de costura.
    if re.search(r'defeito|defeituos|veio errad|saiu errad|costura.{0,24}(torta|solta|defeito)|furo|problema na peca|reclam', t):
        return "qualidade_defeito"
    if re.search(r'atras|passou do prazo|nao chegou|não chegou|cade meu pedido|cadê meu pedido', t):
        return "prazo_atraso"
    if tipo_turno == "problema_cliente" and re.search(r'posso acelerar|adiantar|urgente|prazo curto', t):
        return "prazo_urgente"
    if tipo_turno == "problema_cliente" and re.search(r'resolver|arrumar|corrigir|e agora|o que faco|o que faço', t):
        problema = (sessao or {}).get("problema_cliente", {})
        return problema.get("intencao") or "qualidade_defeito"

    # Recomendações em conversa longa: preservar o briefing do cliente em vez de
    # deixar "logo" virar despedida/keyword solta ou "local quente" virar inverno.
    if tipo_turno == "recomendacao":
        if re.search(r'local quente|calor|verao|verão|fresco|leve', t):
            return "sug_tec_quente"
        if re.search(r'\blogo\b|bordad|estamp', t):
            return "personalizacao_bordado"
        if re.search(r'barat|custo|econom|mais em conta|menor valor', t):
            return "setor_vendas"
        if re.search(r'empresa|corporativ|uniforme|evento', t):
            return "sug_trabalho"

    if re.search(r'melhor tecido|qual tecido|tecido ideal|sugere tecido|recomenda tecido', t):
        if re.search(r'frio|inverno|quentinho|aquecer', t):
            return "sug_tec_frio"
        if re.search(r'calor|quente|verao|verão|fresco|leve', t):
            return "sug_tec_quente"

    # ── 0d. MULTI-INTENÇÃO ──────────────────────────────────────
    # Se a frase toca 3+ tópicos distintos (prazo, preço, produto, cor, tecido,
    # cuidados, tamanho, personalização, entrega) e é claramente uma PERGUNTA
    # (não pedido/consulta/cancelamento), listamos o que entendemos e perguntamos
    # por qual começar. Sem isso, o bot escolhia UM tópico arbitrário e ignorava
    # o resto (ex: "qual o prazo e o preco e voces fazem moletom e como lavo"
    # só respondia cuidados_moletom).
    #
    # Guardas pra NÃO sequestrar mono-intenção:
    #   - pedido / menu em andamento (sessão tem outro fluxo)
    #   - tem quantidade + produto (é pedido/orçamento — regras compostas
    #     cuidam melhor)
    #   - tem número de pedido (status/consulta)
    #   - verbos de ação forte (cancelar/alterar/fechar/registrar/consultar/
    #     rastrear) — vai pras regras específicas dessas ações
    _tem_qtd_produto = bool(
        slots_efetivos.get("quantidade") and slots_efetivos.get("produto")
    )
    _tem_pedido_id = bool(slots_efetivos.get("numero_pedido"))
    _tem_verbo_acao = bool(re.search(
        r'\bcancelar\b|\balterar\b|\bmudar\b|\btrocar\b|\bfechar\b|'
        r'\bvou levar\b|\bencomend\w+|\bconsultar\b|\brastrear\b|\bstatus\b|'
        r'\bregistrar\b|\bcadastrar\b', t
    ))
    _sessao_ativa = sessao and (
        sessao.get("registro_pedido") or sessao.get("aguardando_mais_produto")
        or sessao.get("aguardando_opcao") or sessao.get("aguardando_id")
    )
    if not (_tem_qtd_produto or _tem_pedido_id or _tem_verbo_acao or _sessao_ativa):
        topicos = _detectar_topicos_multi(t)
        # ≥ 4 tópicos: 3 costuma bater combinações que já têm intenção dedicada
        # (ex: "prazo + produto + personalização" → prazo_com_personalizacao).
        # A partir de 4 é claramente pergunta múltipla sem intenção específica.
        if len(topicos) >= 4:
            if sessao is not None:
                sessao["topicos_pendentes"] = sorted(topicos)
            return "multi_intencao"

    # ── 0b. Fluxos de CRUD de pedido em andamento ────────────────
    if sessao:
        # Registro de pedido em andamento. Perguntas e ações fortes interrompem
        # o formulário em vez de serem tratadas como campo inválido.
        if sessao.get("registro_pedido") is not None:
            if slots_turno.get("numero_pedido") or _parece_status_pedido_existente(t):
                sessao["registro_interrompido"] = "status_pedido"
                return "status_pedido"
            if re.search(r'\bcancelar\b|\bcancelamento\b', t):
                return "cancelar_pedido"
            if re.search(r'\balterar\b|\bmudar\b|\btrocar\b', t) and re.search(r'pedido|cor|tamanho|quantidade', t):
                sessao["registro_interrompido"] = "alterar_pedido_especifico"
                return "alterar_pedido_especifico"
            pendente = sessao.get("registro_campo_pendente")
            respondeu_pendente = bool(
                (pendente == "produto" and slots_turno.get("produto")) or
                (pendente == "quantidade" and slots_turno.get("quantidade")) or
                (pendente == "cor" and slots_turno.get("cor")) or
                (pendente == "tecido" and slots_turno.get("tecido")) or
                (pendente == "tamanho" and slots_turno.get("grade")) or
                (pendente == "personalizacao" and slots_turno.get("personalizacao"))
            )
            pergunta_explicita = _parece_pergunta(t) and re.search(
                r'\?|\bquanto\b|\bqual\b|\bquais\b|\bquando\b|\bcomo\b|\bposso\b|\bpode\b|\btem\b', t
            )
            if pergunta_explicita:
                sessao["registro_interrompido"] = "duvida"
                # Continua para as regras normais do classificador.
            elif not respondeu_pendente and _parece_pergunta(t):
                sessao["registro_interrompido"] = "duvida"
                # Continua para as regras normais do classificador.
            else:
                return "registrar_pedido"
        # Acabou de registrar um item e perguntamos "quer mais um produto?".
        if sessao.get("aguardando_mais_produto"):
            if re.search(r'\bnao\b|\bnão\b|\bnn\b|so isso|nada mais|mais nada|'
                         r'finaliz|encerr|pode fechar|e so|era so|chega|ta bom|'
                         r'\bnop\b', t):
                return "finalizar_pedidos"
            # Mensagem é SÓ personalização (bordado/silk/dtf) sem produto novo?
            # Cliente esqueceu de dizer no fluxo do item 1 — corrigir o último
            # item do carrinho em vez de começar item 2.
            personalizacao_solta = (
                slots_turno.get("personalizacao") and not slots_turno.get("produto")
                and not slots_turno.get("quantidade") and not slots_turno.get("cor")
                and not slots_turno.get("tecido") and not slots_turno.get("grade")
            )
            if personalizacao_solta and sessao.get("carrinho"):
                sessao["carrinho"][-1]["personalizacao"] = slots_turno["personalizacao"]
                # mantém aguardando_mais_produto e volta a perguntar
                return "atualizar_ultimo_item"
            # qualquer outra coisa (um "sim" ou já um novo produto) → novo item
            sessao["aguardando_mais_produto"] = False
            return "registrar_pedido"
        # Pedimos um ID antes e ele chegou agora → executa a ação que ficou pendente
        # (consultar / cancelar / alterar). Guardada em sessao["aguardando_id"].
        acao_pendente = sessao.get("aguardando_id")
        if acao_pendente and slots_turno.get("numero_pedido"):
            return acao_pendente

    # ── 1. Regras por VERBO (alta prioridade — vencem regras por slot) ──
    # CRÍTICO 6: "cancelar" vem antes de "numero_pedido vira status"
    if re.search(r'\bcancelar\b|\bcancelamento\b', t):
        return "cancelar_pedido"

    if re.search(r'\balterar\b|\bmudar\b|\btrocar\b', t) and re.search(
        r'tamanho|cor|quantidade|pedido', t
    ):
        return "alterar_pedido_especifico"

    if sessao and sessao.get("aguardando_id"):
        if re.search(r'como (ta|esta)|andamento|status|numero|número|nao tenho|não tenho|nao sei|não sei', t):
            return sessao.get("aguardando_id")
        if sessao.get("aguardando_id") == "alterar_pedido_especifico" and (slots_turno.get("cor") or slots_turno.get("grade")):
            return "alterar_pedido_especifico"

    if re.search(r'\bescola\b|\bescolar\b|\bfarda\b', t):
        return "uniforme_escolar"

    if re.search(r'amaciante', t):
        return "manut_amaciante"

    if re.search(r'quanto tempo de mercado|tempo de mercado|anos de mercado', t):
        return "sobre_marca_tempo"

    # ── Perguntas de NEGOCIAÇÃO no pedido (P7) ────────
    # Cliente empresa/atacado pergunta sobre combinações e variações antes de
    # fechar: "posso combinar bordado com silk?", "cor por cor pode variar?",
    # "500 pretas ou 250/250?", "posso misturar tamanhos?". Sem intenção
    # dedicada, essas caíam no catálogo do produto — inútil pra negociação.
    _CORES_NEG = r'pret\w*|branc\w*|azul|verde|vermelh\w*|amarel\w*|rosa|cinza|marinho|royal|vinho'
    if re.search(r'\bpode(?:m)?\s+(?:combinar|misturar|variar|mesclar)\b|'
                 r'\bposso\s+(?:combinar|misturar|variar|mesclar)\b|'
                 r'\bda pra combinar\b|\bcombinar\s+(bordad|silk|dtf|estamp)|'
                 r'\bmisturar\s+(cor|tamanhos?|modelos?|produtos?)|'
                 r'\bvariar?\s+(cor|tamanhos?)|'
                 r'\bmix (de |em )?(cor|tamanhos?)|'
                 # "500 pretas e 250 brancas" / "50 rosa 50 verde" (separador opcional)
                 rf'\b(\d+)\s+({_CORES_NEG})\s*(?:e|,|ou)?\s*(\d+)\s+({_CORES_NEG})', t):
        return "negociacao_pedido"

    # ── Perguntas GRANULARES dentro de tópico ─────────
    # "quantas cores no silk?"/"quantas cores no bordado?" — o cliente quer o
    # limite técnico (6 no silk, 12 no bordado), não a descrição inteira nem o
    # menu de cores em estoque.
    if re.search(r'\bquantas?\s+cores\b|\blimite\s+de\s+cores\b|\bnumero\s+de\s+cores\b', t):
        return "cores_limite_tecnica"
    # "resolucao?" (arte) — pergunta pontual sobre requisitos de arquivo.
    if re.search(r'\bresolu[cç][aã]o\b|\bdpi\b|\bqualidade\s+da\s+arte\b|\btamanho\s+do\s+arquivo\b|'
                 r'\bqual\s+formato\b|\baceita\s+(ai|pdf|png|svg|cdr|jpg|vetor)\b', t):
        return "personalizacao_envio_arte"
    # "tem taxa?" — só é urgência quando o contexto é de urgência.
    if re.search(r'\btem\s+taxa\??|\bpaga\s+taxa\??|\btaxa\s+de\s+urg', t):
        return "prazo_urgente"

    # ── Perguntas BINÁRIAS comuns ("são/produzem/aceitam/têm X?") ──
    # Sem essas regras dedicadas, "voces sao brasileiros?" caía em fallback e
    # "as pecas sao boas?" idem. Cliente espera sim/não com contexto — o classifier
    # já tinha as intenções certas, faltava só o roteamento por linguagem natural.
    if re.search(r'(\bs[aã]o|\bvoces s[aã]o|\bvcs s[aã]o)\s+(brasileir\w*|nacional|do brasil)|'
                 r'produzem\s+(no\s+)?brasil|onde (fica|é|e)\s+(a\s+)?f[aá]brica|'
                 r'\bque\s+lugar\b|\bde\s+onde\s+s[aã]o\b', t):
        return "producao_onde"

    if re.search(r'(\bs[aã]o|\bvoces s[aã]o|\bpecas? s[aã]o)\s+(boas?|durav[eé]is?|de qualidade|bem feitas?|resistentes?)|'
                 r'peca\w* aguenta\w*|resiste', t):
        return "qualidade_durabilidade"

    if re.search(r'(\baceita|\baceitam)\s+(cartao|cart[aã]o|boleto|pix|cnpj|cr[eé]dito|d[eé]bito)|'
                 r'\bformas? de pagamento\b|\bmeio de pagamento\b|parcel\w+', t):
        return "setor_vendas"

    if re.search(r'\b(voces|vcs)?\s*(atendem|vendem|entregam|mandam|enviam)\s+(pra|para)\s+'
                 r'(o\s+|a\s+)?(brasil|sp|sao paulo|rj|rio|mg|belo|salvador|recife|fortaleza|ceara|'
                 r'curitiba|porto alegre|florianopolis|manaus|goiania|df|brasilia|todo brasil|todo o pais|todo pais)', t):
        return "setor_logistica"

    if re.search(r'\btem\s+(a\s+)?(cor\s+)?(pret\w*|branc\w*|cinza|marinho|royal|azul|vermelh\w*|rosa|amarel\w*|verde|vinho|bege|marrom|laranja|roxo|lilas)', t) or \
       re.search(r'\b(pret\w*|branc\w*|cinza|marinho|royal|azul|vermelh\w*|rosa|amarel\w*|verde|vinho|bege|marrom|laranja|roxo|lilas)\s+tem\??$', t):
        return "cores_basicas"

    if re.search(r'\btem\s+(loja|site|instagram|whatsapp|contato)\b|'
                 r'\btem\s+(um\s+)?telefone\b|\bposso\s+visitar\b', t):
        return "sobre_o_bot"

    if re.search(r'\bposso\s+(pedir|comprar)\s+(so\s+|apenas\s+)?(1|um|uma|pouco|pequen)|'
                 r'\bqual\s+o\s+m[ií]nimo|\bpedido\s+m[ií]nimo|\bmenos\s+de\s+\d+', t):
        return "qtd_pequena_volume"

    if re.search(r'fibra reciclada|rpet|reciclad', t):
        return "sustent_fibra_reciclada"

    if re.search(r'algodao.*organico|organico.*algodao|'
                 r'(trabalh\w+|tem|usam|fazem|voces)\s+(com\s+)?(algod\w*\s+)?organic', t):
        return "sustent_algodao_organico"

    if re.search(r'tinta.*toxic|toxica|tóxica|toxico|tóxico', t):
        return "sustent_quimicos"

    if _parece_status_pedido_existente(t):
        return "status_pedido"

    # CREATE: iniciar o registro de um pedido novo
    # ("quero fazer um pedido", "registrar pedido", "novo pedido"...)
    if re.search(r'\b(registrar|cadastrar|abrir|criar)\b.*\bpedido\b', t) or \
       re.search(r'\b(fazer|faz)\b.*\bpedido\b', t) or \
       re.search(r'\b(novo|outro|mais um|mais) pedido\b', t):
        return "registrar_pedido"

    # Revenda/atacadista vem antes do registro. "quero comprar 500 pra revender"
    # é exploração comercial, não autorização para abrir pedido.
    if re.search(r'revend|atacadista|distribuidor|sacoleira', t):
        return "revenda"

    # CREATE implícito: só começa registro quando há sinal claro de fechamento.
    # "quero comprar 500 camisetas" pode ser cotação; "vou fechar/pode registrar"
    # é pedido de fato.
    if not re.search(r'\bsaber\b|\bver\b|\bconhec\w+|\bsobre\b|informac|d[uú]vida|'
                     r'\bquais\b|\bqual\b|\bcomo\b|\bquanto\b|\bpreco\b|\bpreço\b|'
                     r'\bdesconto\b|\bprazo\b|\btempo\b|\bcor(es)?\b|\btamanhos?\b', t):
        # "vamos fechar" cobre o "bora fechar" pós-normalização (bora→vamos).
        frase_pedido = re.search(
            r'\bvou querer\b|\bvou levar\b|\bvou fechar\b|\bpode fechar\b|'
            r'\bpode registrar\b|\bregistrar esse pedido\b|\bfechar (o )?pedido\b|'
            r'\bencomend\w+|\bquero (fazer|fechar)\b|\bbora fechar\b|'
            r'\bvamos fechar\b|\bfechado\b|\bfecha ai\b', t)
        if frase_pedido:
            return "registrar_pedido"

    # Obs: "avançar etapa" NÃO é ação do cliente (é da produção interna), então
    # não tem regra de chat aqui. A função existe em bot/pedidos/atualizar.py e é
    # exercitada pelos testes e pela demo, mas o cliente não dispara isso conversando.

    # CRÍTICO 5: estoque vence pedido herdado
    if re.search(r'\bestoque\b|\bem estoque\b|\btem (algodao|dry.?fit|malha|jeans|viscose|linho|moletom|suplex|tecido|tencel|alfaiataria|la|rpet)\b', t):
        return "disponibilidade_materiais"

    # READ: consultar/acompanhar o andamento de um pedido (pede o ID depois).
    # Precisa vir aqui em cima pra "status do pedido" não cair no menu genérico
    # etapas_pedido (que casa pela mesma palavra-chave lá embaixo).
    if re.search(r'status d[oae]s? (meu )?pedido|consultar (o )?(meu )?pedido|'
                 r'acompanhar (o )?(meu )?pedido|onde esta (o )?meu pedido|'
                 r'andamento d[oae] (meu )?pedido|fase d[oae] (meu )?pedido|'
                 r'etapa d[oae] (meu )?pedido|saiu do corte|foi para a costura|'
                 r'esta no corte|esta na costura|meu lote|'
                 # formas soltas: "quero acompanhar", "como ta o andamento",
                 # "como ta meu pedido", "ja terminou o pedido"
                 r'\bacompanhar\b|\bandamento\b|como (ta|esta) (o )?(meu )?pedido', t):
        return "status_pedido"

    # ── 1b. Pediram algo FORA do catálogo (moto, sapato, geladeira...) ──
    # Vem cedo, ANTES de "comprar" cair em vendas: o bot precisa NEGAR e reafirmar
    # o que a gente faz, não encaminhar pra vendas nem dar fallback.
    if re.search(FORA_CATALOGO, t):
        return "cat_nao_fazemos"

    # ── 2. Regras por slot DO TURNO ATUAL ─────────────────────────
    # CRÍTICO 5: numero_pedido só dispara se foi mencionado AGORA,
    # não se está só herdado da sessão.
    if slots_turno.get("numero_pedido"):
        # combinação verbo + numero
        if re.search(r'consultar|status|etapa|onde esta|andamento', t):
            return "status_pedido"
        return "status_pedido"

    # consumo de tecido pede produto + metragem + quantidade
    if slots_turno.get("metragem") and slots_efetivos.get("quantidade") and slots_efetivos.get("produto"):
        return "consumo_tecido"

    # ── 3. Intenções compostas (preço/prazo) ─────────────────────
    quantidade = slots_efetivos.get("quantidade")
    produto = slots_efetivos.get("produto")
    if produto and not quantidade and re.search(r'preco|preço|valor|custa|quanto fica|prazo|tempo', t):
        m_qtd_solto = re.search(r'\b(\d{1,6})\b', t)
        if m_qtd_solto:
            quantidade = int(m_qtd_solto.group(1))
            slots_efetivos["quantidade"] = quantidade
    prazo_desejado = slots_efetivos.get("prazo_desejado") or slots_turno.get("prazo_desejado")

    if tipo_turno == "correcao_orcamento":
        qtd = numero_solto_de_correcao(t)
        if qtd and produto:
            slots_efetivos["quantidade"] = qtd
            quantidade = qtd
        if produto and quantidade:
            ultimo = (sessao or {}).get("ultimo_assunto")
            if ultimo in {"combinado_prazo_qtd_produto", "combinado_prazo_personalizacao_produto"}:
                return ultimo
            return "combinado_preco_qtd_produto"

    # ── 3b. Prazo COM personalização ──────────────────────────────
    # "prazo com bordado/silk/dtf" caía em personalizacao_X (a DESCRIÇÃO da técnica)
    # em vez de responder o PRAZO. Se a frase fala de prazo E há uma personalização,
    # é pergunta de prazo-com-personalização (com produto/qtd → a versão combinada).
    tem_prazo = bool(re.search(r'\bprazo\b|quanto tempo|demora|quando fica', t))
    pers = slots_efetivos.get("personalizacao")
    if tem_prazo and pers and pers != "nenhuma":
        if produto or quantidade:
            return "combinado_prazo_personalizacao_produto"
        return "prazo_com_personalizacao"

    # Intenção EXPLÍCITA na frase tem prioridade
    if quantidade and produto:
        if re.search(r'custa|preco|preço|valor|orcamento|quanto fica|sai por', t):
            return "combinado_preco_qtd_produto"
        if re.search(r'prazo|dias|quando|tempo|termina|previsao|fica pronto', t):
            return "combinado_prazo_qtd_produto"

    # ── 4. Viabilidade de produção ────────────────────────────────
    # ALTO 11: viabilidade vence qtd_grande_volume
    if (prazo_desejado or re.search(r'consigo|da pra|conseguimos|viavel|viável', t)) \
       and quantidade:
        return "viabilidade_producao"

    # "capacidade" sozinha NÃO é viabilidade: "capacidade produtiva/da fábrica" é
    # pergunta INFORMATIVA (cai em producao_capacidade na etapa de keyword). Só
    # forçamos viabilidade quando a pessoa pergunta se CONSEGUIMOS produzir algo.
    if re.search(r'consegue(m)? produzir|da p(?:a?ra) produzir|'
                 r'capacidade tecnica|capacidade de produc', t):
        return "viabilidade_producao"

    # ── 5. Follow-up: usuário refinou um slot, herda último assunto ─
    # ALTO 9: se mensagem traz só um slot novo (personalizacao/tecido/cor)
    # e o último assunto era preço/prazo/viabilidade, herda o assunto.
    ULTIMO_ORCAMENTO = {
        "combinado_preco_qtd_produto",
        "combinado_prazo_qtd_produto",
        "combinado_prazo_personalizacao_produto",
        "combinado_preco_personalizacao",
        "viabilidade_producao",
    }
    # Também tratamos como orçamento os casos onde o assunto anterior era GENÉRICO
    # (prazo_padrao, setor_vendas) — cliente que perguntou "quanto tempo pra uma
    # camiseta" e agora diz "e 100?" está claramente pedindo prazo pra 100
    # camisetas. Sem isso, cai em cat_camisetas.
    ULTIMO_QUASE_ORCAMENTO = {
        "prazo_padrao": "combinado_prazo_qtd_produto",
        "prazo_com_personalizacao": "combinado_prazo_personalizacao_produto",
        "prazo_urgente": "combinado_prazo_qtd_produto",
        "setor_vendas": "combinado_preco_qtd_produto",
        # Número solto logo após o CATÁLOGO de um produto = "quanto custa N?"
        # ("moletom tem?" → catálogo → "de 20" → orçamento de 20 moletons).
        "cat_camisetas": "combinado_preco_qtd_produto",
        "cat_moletons": "combinado_preco_qtd_produto",
        "cat_calcas": "combinado_preco_qtd_produto",
        "cat_vestidos": "combinado_preco_qtd_produto",
        "cat_uniformes": "combinado_preco_qtd_produto",
        "produto_detalhe": "combinado_preco_qtd_produto",
    }
    if sessao and sessao.get("ultimo_assunto") in ULTIMO_ORCAMENTO:
        qtd_solta = _numero_solto(t)
        if qtd_solta and produto:
            slots_efetivos["quantidade"] = qtd_solta
            return sessao["ultimo_assunto"]
        slots_novos_chaves = set(slots_turno.keys()) - {"quantidade", "produto"}
        # se a mensagem só adicionou refinamento (sem mudar produto/qtd),
        # e ainda temos qtd+produto no foco, herda o assunto
        if slots_novos_chaves and quantidade and produto:
            return sessao["ultimo_assunto"]

    if sessao and sessao.get("ultimo_assunto") in ULTIMO_QUASE_ORCAMENTO:
        qtd_solta = _numero_solto(t)
        if qtd_solta and produto:
            slots_efetivos["quantidade"] = qtd_solta
            return ULTIMO_QUASE_ORCAMENTO[sessao["ultimo_assunto"]]

    # ── 6. Combinações por slot ───────────────────────────────────
    # Só tratamos como pergunta de COMPATIBILIDADE/DISPONIBILIDADE se a frase
    # tiver um sinal disso ("combina", "posso usar", "dá pra", "tem em"...).
    # Senão, citar um tecido/cor junto de um produto é INFORMATIVO (não um
    # veredito) — aí deixamos cair no catálogo/tecidos, que faz mais sentido.
    sinal_compat = bool(re.search(
        r'combina|casa com|harmoniza|da pra|posso |pode (usar|fazer|ser)|'
        r'fica bo|serve|aceita|recomend|ideal|funciona|\be bom\b|vale a pena|'
        r'adequad|compat|melhor tecido|qual tecido|\btem\b|disponiv|estoque', t
    ))

    if tipo_turno == "compatibilidade" and slots_efetivos.get("tecido") and produto:
        return "combinado_tecido_em_produto"

    if slots_efetivos.get("cor") and slots_efetivos.get("tecido")        and (slots_turno.get("cor") or slots_turno.get("tecido"))        and re.search(r'\bem\b|na cor|tem|disponiv|estoque|da\??', t):
        return "combinado_cor_em_tecido"

    if slots_efetivos.get("tecido") and produto        and (slots_turno.get("tecido") or slots_turno.get("produto"))        and re.search(r'\bem\b|da\??|dá\??|posso|pode|combina|funciona', t):
        return "combinado_tecido_em_produto"

    if produto and slots_efetivos.get("cor") and re.search(r'\btem\b|disponiv|estoque|cor', t):
        return "cores_basicas"

    if slots_efetivos.get("tecido") and slots_efetivos.get("personalizacao") \
       and (slots_turno.get("tecido") or slots_turno.get("personalizacao")) \
       and sinal_compat:
        return "combinado_personalizacao_em_tecido"

    if slots_efetivos.get("tecido") and produto \
       and (slots_turno.get("tecido") or slots_turno.get("produto")) \
       and sinal_compat:
        return "combinado_tecido_em_produto"

    if slots_efetivos.get("cor") and slots_efetivos.get("tecido") \
       and (slots_turno.get("cor") or slots_turno.get("tecido")) \
       and sinal_compat:
        return "combinado_cor_em_tecido"

    if produto and slots_efetivos.get("grade") and slots_turno.get("grade"):
        return "combinado_tamanho_em_produto"

    if produto and slots_efetivos.get("uso") and slots_turno.get("uso"):
        return "combinado_gramatura_produto_uso"

    # ── 7. Número solto sem contexto → fallback ───────────────────
    if re.match(r'^\d+$', mensagem.strip()):
        return "fallback"

    # Só prazo_desejado sem produto/quantidade — pergunta clarificadora
    # (cenário 12: "preciso em 100 dias" sem mais nada)
    if slots_turno.get("prazo_desejado") and not produto and not quantidade:
        return "prazo_sem_contexto"

    # ── 7b. Roteamento fino "produção vs outro setor" ─────────────
    # Os setores (setor_*) têm peso 9, então uma pergunta de PRODUÇÃO que só
    # menciona de passagem uma palavra de outro setor (envio, entrega, desconto,
    # fornecedor) era puxada pra lá — mesmo existindo uma intenção NOSSA com
    # resposta melhor. Aqui a gente segura essas na produção quando o contexto
    # é claramente do nosso setor. (Obs: "veio com defeito" continua indo pra
    # devoluções DE PROPÓSITO — a própria qualidade_defeito encaminha pra lá.)

    # Cuidado POR TECIDO: "como cuido/lavo do jeans" → cuidados_jeans (não o
    # catálogo de calças nem a composição). Exige verbo de cuidado + tecido.
    if re.search(r'cuid|lav|conserv|encolh|desbot|amass|ferro', t):
        for padrao, intent in (
            (r'\balgodao', 'cuidados_algodao'), (r'\bviscose', 'cuidados_viscose'),
            (r'\bpoliester', 'cuidados_poliester'), (r'\blinho', 'cuidados_linho'),
            (r'\bjeans', 'cuidados_jeans'), (r'\bmoletom', 'cuidados_moletom'),
            (r'\bmalha', 'cuidados_malha'), (r'\bla\b', 'cuidados_la'),
        ):
            if re.search(padrao, t):
                return intent

    # Envio de ARTE/arquivo pra personalização (não é logística de entrega).
    if re.search(r'\b(arte|arquivo|layout|vetor|png|cdr|pdf|svg)\b', t) and \
       re.search(r'envi|mand|form|aceit|resoluc', t):
        return "personalizacao_envio_arte"

    # Desconto por VOLUME → temos a tabela de progressão (não encaminha pra vendas).
    if (re.search(r'desconto', t) and re.search(
            r'volume|atacado|progressiv|quantidade|quanto mais|lote|por peca', t)) \
       or re.search(r'quanto mais.*barato', t):
        return "combinado_desconto_volume"

    # Fornecedor/origem DO TECIDO → tec_origem (o setor de compras é pra quem
    # quer VENDER material PRA gente, não pra quem pergunta de onde vem o nosso).
    if re.search(r'(fornecedor|origem|de onde vem).{0,14}tecido|'
                 r'tecido (nacional|importado)|tecelagem|malharia', t):
        return "tec_origem"

    # "pronta entrega" é termo de produção (trabalhamos sob demanda), não logística.
    if re.search(r'pronta.?entrega|peca(s)? pronta|envio imediato', t):
        if re.search(r'\bcor(es)?\b', t):
            return "cores_basicas"
        return "pronta_entrega"

    # "prazo ... da produção/fabricação" é o nosso lead time, não prazo de envio.
    if re.search(r'\bprazo\b', t) and re.search(r'produc|fabricac', t):
        return "prazo_padrao"

    # ── 7c. Tópico perguntado vence o substantivo de produto ──────
    # "qual o prazo de uma camiseta" / "quais tamanhos de polo" caíam no CATÁLOGO
    # do produto (cat_* pesa 6; o menu do tópico pesa 4). Se a pessoa cita um
    # produto mas o que ela PERGUNTA é prazo/tamanho/urgência, respondemos o tópico.
    # (Fica DEPOIS das regras compostas: "prazo de 100 camisetas" com quantidade
    # já virou combinado lá em cima; grade explícita já virou tamanho_em_produto.)
    # (b2b de uniforme empresarial — "uniforme pra empresa com logo e prazo" —
    # não entra aqui: é pedido completo, tratado adiante.)
    contexto_b2b = bool(re.search(r'empresa|b2b|logo', t))
    if produto and not contexto_b2b:
        if re.search(r'\bprazo\b|quando fica|quanto tempo', t):
            return "prazo_padrao"
        if re.search(r'\btamanhos?\b|\bgrade\b|\bnumeracao\b', t):
            return "personalizacao_tamanhos"
        # "como cuido/lavo da camiseta" (cuidado do PRODUTO, sem tecido citado)
        # → menu de manutenção, não o catálogo do produto.
        if re.search(r'\bcuid\w+|\blav\w+|\bconserv\w+|\bencolh\w+|\bdesbot\w+', t):
            return "manutencao"
        if slots_efetivos.get("urgente"):
            return "prazo_urgente"

    # "premium" (a camiseta premium) → detalhe do produto (da tabela produtos.csv),
    # não o catálogo inteiro de camisetas. Basta o extractor ter resolvido o
    # produto como camiseta_premium (cobre "camisas premium", typo "premiun" etc);
    # pedido com quantidade já virou registrar_pedido lá em cima.
    if produto == "camiseta_premium":
        if re.search(r'compara|comparar|diferen[çc]a|basica|básica', t):
            return "comparar_premium_basica"
        if re.search(r'boa|bom|duravel|dura|qualidade|vale a pena|compensa', t):
            return "qualidade_durabilidade"
        sinal_descricao = re.search(
            r'\bpremium\b|\bme conta\b|\bfala\b|\bo que e\b|\bo que é\b|\bsobre\b|\bconhecer\b|\btudo sobre\b',
            t
        )
        sinal_topico = re.search(
            r'preco|preço|valor|prazo|tempo|cor|cores|tecido|tamanho|grade|lav|cuid',
            t
        )
        if sinal_descricao and not sinal_topico:
            return "produto_detalhe"

    # "qual/quais tecido(s) pra <produto>" → lista os tecidos que combinam com o
    # produto. Só quando NENHUM tecido específico foi citado (senão "camiseta de
    # linho" é um veredito pontual, tratado na regra de compatibilidade acima) e
    # NÃO é pergunta de consumo (metros) nem de gramatura (grosso/fino/peso).
    if produto and not slots_efetivos.get("tecido") and re.search(r'\btecidos?\b', t) \
       and not re.search(r'\bmetros?\b|gramatura|\bgrosso\b|\bfino\b|\bpeso\b|\bgrama', t):
        return "combinado_tecidos_disponiveis_para_produto"

    # ── 8. Palavras-chave do CSV (desempate por PESO) ─────────────
    # Antes era "a primeira intenção que bater vence". Agora coletamos TODAS as
    # intenções cuja palavra-chave aparece na frase e ficamos com a de MAIOR PESO.
    #
    # A busca exige FRONTEIRA DE PALAVRA à esquerda da keyword (\b) — senão
    # keywords curtas casam DENTRO de outras palavras e geram respostas absurdas:
    # "mano" dentro de "hu-mano", "vei" dentro de "dura-vei-s"/"sustenta-vei-s",
    # "cad" dentro de "a-cad-emia". O \b só na frente preserva plurais/sufixos
    # ("camiseta" ainda casa "camisetas"); keywords que começam com símbolo
    # (ex: "% algodao") mantêm a busca por substring.
    melhor_peso = -1.0
    melhor_kw = None
    for _, row in intencoes.iterrows():
        keywords = str(row["palavras_chave"]).strip()
        if not keywords or keywords == "nan":
            continue
        for kw in keywords.split("|"):
            kw = normalizar(kw.strip())
            if not kw:
                continue
            padrao = (r'\b' + re.escape(kw)) if kw[0].isalnum() else re.escape(kw)
            if re.search(padrao, t):
                peso = _peso(row)
                if peso > melhor_peso:
                    melhor_peso = peso
                    melhor_kw = row["id_intencao"]
                break  # essa intenção já bateu; não precisa testar as outras kw dela
    if melhor_kw:
        return melhor_kw

    # ── 8b. "roupa(s)" GENÉRICO → catálogo ────────────────────────
    # A palavra mais natural do cliente ("quero uma roupa", "vendem roupas?",
    # "queria uma roupa rosa") não existia no vocabulário: não é produto do
    # extractor, nenhuma keyword genérica casa (só compostos tipo "roupa boa"),
    # e o fuzzy pescava intenção aleatória ("roupa" → qualidade_durabilidade).
    # Fica DEPOIS da etapa de keywords de propósito: "roupa de frio"→sug_inverno,
    # "roupa infantil"→cat_infantil, "roupa de trabalho"→sug_trabalho já saíram
    # lá; aqui só chega roupa genérica. Com cor citada, responde as cores em
    # estoque (ex: "roupa rosa" → confirma que tem rosa e pergunta a peça).
    if re.search(r'\broupas?\b|\bvestuario\b|\blooks?\b|\bpecas? de roupa\b', t) \
       and not re.search(r'cuid|lav|conserv|encolh|desbot|passar|ferro|secadora|manch', t):
        if slots_turno.get("cor"):
            return "cores_basicas"
        return "catalogo"

    # ── 9. Similaridade textual (rapidfuzz), desempate por peso ───
    melhor_score = 0
    melhor_peso = -1.0
    melhor_intencao = None
    melhor_kw = ""
    for _, row in intencoes.iterrows():
        keywords = str(row["palavras_chave"]).strip()
        if not keywords or keywords == "nan":
            continue
        # Intenções que EXIGEM slots (produto/tecido/cor/qtd...) NÃO podem ser
        # alcançadas por fuzzy: um typo tipo "camizeta" casava por similaridade e
        # o responder montava "grade None para None". Elas só vêm pelas regras de
        # slot (etapa 6); aqui a gente pula.
        if row["id_intencao"] in _SO_POR_SLOT:
            continue
        peso = _peso(row)
        for kw in keywords.split("|"):
            kw = normalizar(kw.strip())
            # Keywords curtas (≤4 letras: "silk", "selo", "vei", "dtf", "la") NÃO
            # entram no fuzzy: partial_ratio casa dentro de qualquer palavra longa
            # ("silk" em "bra-sil", "selo" em "sel-ect", "vei" em "sustenta-vei-s")
            # e gera intenção absurda. O match exato dessas já foi feito na etapa
            # 8; aqui elas só dão ruído. Mudei de <4 pra <5 depois do stress test
            # pra fechar os falso-positivos com "brasil"/"select"/"toca musica".
            if len(kw) < 5:
                continue
            # Mensagem MUITO mais curta que a keyword? Pula. Senão um token solto
            # casa 100% dentro de uma keyword composta ("preto" dentro de "tem
            # vestido preto") e cai numa intenção combinada sem os slots (→ "em None").
            # 0.5 bloqueia "preto"(5) vs "tem vestido preto"(17) mas libera
            # "produtos"(8) vs "quais produtos"(14).
            if len(t) < len(kw) * 0.5:
                continue
            score = fuzz.partial_ratio(kw, t)
            # vence o maior score; se empatar no score, vence o maior peso
            if score > melhor_score or (score == melhor_score and peso > melhor_peso):
                melhor_score = score
                melhor_peso = peso
                melhor_intencao = row["id_intencao"]
                melhor_kw = kw

    # Threshold em DUAS FAIXAS depois do stress test:
    # - 90+ com qualquer keyword (curta e específica: "duravel"→"duraveis")
    # - 85+ SÓ se a keyword vencedora é multi-palavra ou tem ≥7 letras
    #   (frases/keywords longas não colidem espúrio; palavras curtas como
    #   "troca"→"toca musica" (88%) ficam bloqueadas)
    if melhor_score >= 90 or \
       (melhor_score >= 85 and (len(melhor_kw) >= 7 or ' ' in melhor_kw)):
        return melhor_intencao

    # ── 10. Antes de desistir: se a pessoa citou um PRODUTO ou TECIDO (sem uma
    # pergunta específica que casasse acima), mostramos o catálogo daquele
    # produto / o menu de tecidos — bem mais útil que o fallback puro.
    _CAT_POR_PRODUTO = {
        "camiseta_basica": "cat_camisetas", "camiseta_premium": "cat_camisetas",
        "polo": "cat_camisetas", "baby_look": "cat_camisetas",
        "regata": "cat_camisetas", "oversized": "cat_camisetas",
        "moletom": "cat_moletons", "jaqueta": "cat_moletons",
        "calca_jeans": "cat_calcas", "calca_alfaiataria": "cat_calcas",
        "legging": "cat_calcas", "bermuda": "cat_calcas", "jogger": "cat_calcas",
        "vestido_midi": "cat_vestidos", "vestido_longo": "cat_vestidos",
        "uniforme_polo": "cat_uniformes", "uniforme_jaleco": "cat_uniformes",
    }
    if slots_turno.get("produto") in _CAT_POR_PRODUTO:
        return _CAT_POR_PRODUTO[slots_turno.get("produto")]
    if slots_turno.get("tecido"):
        return "tecidos"
    if sessao and sessao.get("aguardando_id"):
        return sessao.get("aguardando_id")

    # Fallback CONTEXTUAL: se o foco tem produto herdado (o cliente já falou desse
    # produto antes), cair no catálogo dele em vez de "não entendi" genérico.
    # Efeito prático: cliente diz "e X?" fora de padrão conhecido — em vez de
    # fallback, ele recebe algo útil sobre o que já estava conversando.
    # COR citada NESTE turno vence produto herdado ("e rosa?" depois de falar
    # de camiseta é pergunta sobre a COR, não pedido do catálogo de novo).
    if slots_turno.get("cor"):
        return "cores_basicas"
    foco_produto = slots_efetivos.get("produto")
    if foco_produto in _CAT_POR_PRODUTO:
        return _CAT_POR_PRODUTO[foco_produto]
    if slots_efetivos.get("tecido"):
        return "tecidos"

    # ── 11. CLARIFICAÇÃO por ambiguidade (two-stage confidence gating) ──
    # Se nenhuma regra específica pegou E o score do top-1 é baixo E os top-2
    # estão empatados (diff < 0.05), oferecer as duas opções em vez de escolher
    # arbitrariamente. Padrão de two-stage NLU: alta confiança → executa; média
    # com empate → clarifica; baixa → fallback.
    candidatas = (sessao or {}).get("intencao_candidatas", []) if sessao else []
    if len(candidatas) >= 2 and candidatas[0]["score"] < 0.55:
        diff = candidatas[0]["score"] - candidatas[1]["score"]
        if diff < 0.05 and candidatas[0]["intencao"] != candidatas[1]["intencao"]:
            if sessao is not None:
                sessao["candidatas_ambiguas"] = [
                    candidatas[0]["intencao"], candidatas[1]["intencao"]
                ]
            return "clarificacao"

    return "fallback"
