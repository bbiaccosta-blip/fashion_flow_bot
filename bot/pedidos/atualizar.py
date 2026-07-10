"""
atualizar.py — UPDATE do CRUD de pedidos.

Tem duas formas de atualizar um pedido:

    alterar_campo  → o cliente muda um dado do pedido (cor, tamanho, quantidade,
                     personalização). SÓ é permitido enquanto o pedido está na
                     etapa 'modelagem' (regra pode_alterar da lookup_etapas).

    avancar_etapa  → move o pedido pra próxima etapa de produção
                     (modelagem → corte → ...). É uma ação de operador/fábrica.

Toda alteração é gravada no CSV (real).

Pseudocódigo equivalente (Semana 3 — UPDATE = READ + alterar + SALVAR):

    INÍCIO DO PROCESSO "Avançar Etapa"
      RECEBER numero_pedido
      linha = BUSCAR NA TABELA "pedidos.csv" ONDE numero_pedido É IGUAL A ...
      SE linha EXISTE ENTÃO:
        linha[etapa_atual] = PROXIMA_ETAPA
        SALVAR TABELA "pedidos.csv"   # <- linha OBRIGATÓRIA depois de todo UPDATE
        RETORNAR "Pedido avançou de etapa."
      FIM SE
    FIM DO PROCESSO
"""
from bot.pedidos import persistencia

# Campos que o cliente pode alterar (enquanto está na modelagem).
# tecido entra aqui: na modelagem (antes do corte) trocar o pano ainda é viável.
CAMPOS_ALTERAVEIS = ["cor", "tamanho", "quantidade", "personalizacao", "tecido"]


def _etapas_em_ordem():
    """Lista as etapas na ordem do processo (a ordem das linhas do CSV)."""
    return persistencia.carregar_etapas()["etapa"].tolist()


def _pode_alterar(etapa):
    """True se a etapa permite alteração (só a modelagem, hoje)."""
    df = persistencia.carregar_etapas()
    linha = df[df["etapa"] == etapa]
    return (not linha.empty) and linha.iloc[0]["pode_alterar"] == "sim"


def alterar_campo(numero, campo, novo_valor, nome_cliente=None):
    """
    Altera um campo do pedido, se a etapa permitir.

    Retorna {"sucesso": bool, "mensagem": str, "pedido": dict | None}.
    """
    # 1. O campo é alterável?
    if campo not in CAMPOS_ALTERAVEIS:
        return {
            "sucesso": False,
            "mensagem": f"Não dá pra alterar '{campo}'. Posso mudar: "
                        + ", ".join(CAMPOS_ALTERAVEIS) + ".",
            "pedido": None,
        }

    # 2. O pedido existe?
    df, indice, linha = persistencia.buscar_por_id(numero)
    if linha is None:
        return {
            "sucesso": False,
            "mensagem": f"Não encontrei o pedido {numero}. Confere o número?",
            "pedido": None,
        }

    # É desse cliente? (trava de dono)
    if not persistencia.e_dono(linha, nome_cliente):
        return {
            "sucesso": False,
            "mensagem": f"O pedido {numero} não está no seu nome.",
            "pedido": None,
        }

    # 3. Está cancelado?
    if linha["status"] == "cancelado":
        return {
            "sucesso": False,
            "mensagem": f"O pedido {numero} está cancelado, não dá pra alterar.",
            "pedido": None,
        }

    # 4. A etapa atual permite alteração?
    if not _pode_alterar(linha["etapa_atual"]):
        return {
            "sucesso": False,
            "mensagem": f"O pedido {numero} já está na etapa "
                        f"'{linha['etapa_atual'].replace('_', ' ')}' — alterações só são "
                        "possíveis enquanto está em modelagem. Mudar agora geraria "
                        "retrabalho e custo.",
            "pedido": None,
        }

    # 5. Aplica a alteração e salva no arquivo (real).
    valor_antigo = linha[campo]
    df.loc[indice, campo] = str(novo_valor)
    persistencia.salvar(df)

    return {
        "sucesso": True,
        "mensagem": f"Pronto! No pedido {numero}, '{campo}' mudou de "
                    f"'{valor_antigo}' para '{novo_valor}'.",
        "pedido": df.loc[indice].to_dict(),
    }


def avancar_etapa(numero):
    """
    Move o pedido para a próxima etapa de produção. Quando passa da última etapa,
    marca o pedido como 'concluido'. (Ação de operador.)
    """
    df, indice, linha = persistencia.buscar_por_id(numero)
    if linha is None:
        return {
            "sucesso": False,
            "mensagem": f"Não encontrei o pedido {numero}.",
            "pedido": None,
        }

    # Não faz sentido avançar a produção de um pedido cancelado.
    if linha["status"] == "cancelado":
        return {
            "sucesso": False,
            "mensagem": f"O pedido {numero} está cancelado — não dá pra avançar de etapa.",
            "pedido": None,
        }

    ordem = _etapas_em_ordem()
    atual = linha["etapa_atual"]
    if atual not in ordem:
        return {
            "sucesso": False,
            "mensagem": f"Etapa atual '{atual}' desconhecida.",
            "pedido": None,
        }

    posicao = ordem.index(atual)
    if posicao >= len(ordem) - 1:
        # já estava na última etapa → conclui o pedido
        df.loc[indice, "status"] = "concluido"
        persistencia.salvar(df)
        return {
            "sucesso": True,
            "mensagem": f"Pedido {numero} chegou ao fim da produção (concluído).",
            "pedido": df.loc[indice].to_dict(),
        }

    nova_etapa = ordem[posicao + 1]
    df.loc[indice, "etapa_atual"] = nova_etapa
    persistencia.salvar(df)
    return {
        "sucesso": True,
        "mensagem": f"Pedido {numero} avançou de '{atual}' para '{nova_etapa}'.",
        "pedido": df.loc[indice].to_dict(),
    }
