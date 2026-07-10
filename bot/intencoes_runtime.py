"""
Categorias de intenções usadas em tempo de execução.

O CSV continua sendo base de conhecimento/keywords. Este arquivo explicita quais
intenções são fluxo interno, CRUD, resposta calculada ou menu para o responder
não deixar uma ação importante cair em texto genérico do CSV por acidente.
"""

INTERNAS = {
    "selecao_opcao",
    "multi_intencao",
    "finalizar_pedidos",
    "prazo_sem_contexto",
    "produto_detalhe",
    "comparar_premium_basica",
    "manut_amaciante",
    "sobre_marca_tempo",
    "sustent_algodao_organico",
    "sustent_fibra_reciclada",
    "atualizar_ultimo_item",   # correção de perso do item anterior no carrinho
    "clarificacao",             # confidence gating (R4)
    "negociacao_pedido",        # perguntas de negociação B2B (P7)
}

CRUD = {
    "registrar_pedido",
    "finalizar_pedidos",
    "status_pedido",
    "alterar_pedido_especifico",
    "alterar_pedido",
    "cancelar_pedido",
}

# Intenções que consultam lookup/CSV operacional ou executam cálculo no código.
CALCULADAS = {
    "combinado_prazo_qtd_produto",
    "combinado_prazo_personalizacao_produto",
    "combinado_preco_qtd_produto",
    "combinado_preco_personalizacao",
    "combinado_tecido_em_produto",
    "combinado_personalizacao_em_tecido",
    "combinado_tecidos_disponiveis_para_produto",
    "combinado_cor_em_tecido",
    "combinado_cores_disponiveis_para_tecido",
    "combinado_tamanho_em_produto",
    "combinado_gramatura_produto_uso",
    "viabilidade_producao",
    "consumo_tecido",
}

MENUS = {
    "qualidade",
    "personalizacao",
    "personalizacao_tipos",
    "personalizacao_cores",
    "personalizacao_tamanhos",
    "personalizacao_quantidade",
    "sustentabilidade",
    "manutencao",
    "manut_por_tecido",
    "producao",
    "catalogo",
    "sugestao_produto",
    "tecidos",
    "sug_tecido_uso",
    "previsao_prazo",
    "etapas_pedido",
}

EXIGE_HANDLER = INTERNAS | CRUD | CALCULADAS
