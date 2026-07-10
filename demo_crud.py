"""
demo_crud.py — Demonstração do CRUD de pedidos acontecendo NA CONVERSA.

Roda uma conversa simulada pelo mesmo pipeline do bot (tratar_nome → extrair_slots
→ classificar → responder → personalizar) e mostra o data/pedidos.csv ANTES e
DEPOIS, provando que as requisições do cliente alteram o CSV de verdade.

Também mostra a TRAVA DE DONO: um cliente só mexe nos pedidos que estão no nome dele.

Execute: python demo_crud.py
"""
from pathlib import Path

from bot.loader import carregar_dados
from bot.extractor import extrair_slots
from bot.classifier import classificar
from bot.responder import responder
from bot.cliente import tratar_nome, personalizar
from bot.contexto import criar_sessao, merge_com_contexto, atualizar_sessao_pos_turno
from bot.pedidos import atualizar

CSV = Path(__file__).parent / "data" / "pedidos.csv"

# Estado inicial conhecido (a coluna 'cliente' é o DONO de cada pedido).
SEED = """numero_pedido,data_criacao,cliente,produto,quantidade,cor,tamanho,tecido,personalizacao,etapa_atual,status,data_prevista,observacao
FF-2026-0001,2026-06-01,Maria Silva,camiseta_basica,150,preto,M,algodao_pima,bordado,corte,em_producao,2026-07-06,uniforme PJ
FF-2026-0002,2026-06-10,Joao Souza,moletom,80,marinho,G,moletom_flanelado,silkscreen,modelagem,em_producao,2026-07-15,ainda em modelagem
FF-2026-0003,2026-05-28,Ana Costa,polo,200,branco,GG,algodao_penteado,bordado,costura,em_producao,2026-07-02,uniforme corporativo
FF-2026-0004,2026-06-05,Carlos Lima,vestido_midi,30,vinho,P,viscose,nenhuma,qualidade,em_producao,2026-06-22,sem personalizacao
FF-2026-0005,2026-05-20,Beatriz Rocha,legging,120,preto,M,suplex,dtf,embalagem_expedicao,concluido,2026-06-12,pronto para envio
"""


def resetar_seed():
    """Volta o pedidos.csv pro estado inicial, pra demo ser repetível."""
    CSV.write_text(SEED, encoding="utf-8")


def mostrar_csv(titulo):
    print(f"\n===== {titulo} =====")
    print(CSV.read_text(encoding="utf-8").strip())
    print("=" * (12 + len(titulo)))


def conversa(mensagens, nome=None):
    """
    Roda uma lista de mensagens numa única sessão, igual ao main.py
    (tratar_nome → pipeline → personalizar).

    Se 'nome' for dado, simula que o cliente já se identificou (pula a pergunta
    do nome) — útil pra mostrar as operações já como um cliente conhecido.
    """
    dados = carregar_dados()
    sessao = criar_sessao()
    if nome:
        sessao["nome_cliente"] = nome
        sessao["ativa"] = True
    for msg in mensagens:
        # captura de nome no início (igual no main.py)
        resp_nome = tratar_nome(msg, sessao)
        if resp_nome is not None:
            print(f"\nVocê: {msg}")
            print(f"Bot: {resp_nome}")
            continue
        em_menu = bool(sessao.get("aguardando_opcao"))
        slots_turno = extrair_slots(msg, em_menu=em_menu)
        slots_efetivos = merge_com_contexto(slots_turno, sessao, msg)
        intencao = classificar(msg, slots_turno, slots_efetivos, dados["intencoes"], sessao)
        resposta = personalizar(responder(intencao, slots_efetivos, dados, sessao, msg), sessao)
        atualizar_sessao_pos_turno(sessao, msg, slots_efetivos, intencao, resposta)
        print(f"\nVocê: {msg}")
        print(f"Bot [{intencao}]: {resposta}")


resetar_seed()
mostrar_csv("pedidos.csv ANTES")

print("\n\n########## PERSONALIZAÇÃO — o bot pergunta e guarda o nome ##########")
conversa(["oi", "me chamo Maria Silva", "qual a durabilidade da peça?"])

print("\n\n########## R — Maria consulta um pedido DELA (FF-2026-0001) ##########")
conversa(["qual o status do pedido FF-2026-0001"], nome="Maria Silva")

print("\n\n########## R — TRAVA DE DONO: Maria tenta ver o pedido do João (FF-2026-0002) ##########")
conversa(["status do pedido FF-2026-0002"], nome="Maria Silva")

print("\n\n########## C — Maria registra um pedido novo (vira dela) ##########")
conversa([
    "quero fazer um pedido",
    "camiseta",
    "100",
    "branco",
    "G",
    "algodao pima",
    "bordado",
], nome="Maria Silva")

print("\n\n########## U — ALTERAR (permitido: pedido novo da Maria está na modelagem) ##########")
conversa(["mudar a cor do pedido FF-2026-0006 para preto"], nome="Maria Silva")

print("\n\n########## U — AVANÇAR ETAPA (ação do OPERADOR, NÃO do cliente) ##########")
# Avançar etapa não passa pelo chat do cliente — é ação interna da produção.
print("Operador avança a etapa do FF-2026-0006:")
print("  ", atualizar.avancar_etapa("FF-2026-0006")["mensagem"])

print("\n\n########## U — ALTERAR (bloqueado: FF-2026-0006 já saiu da modelagem) ##########")
conversa(["quero mudar a cor do pedido FF-2026-0006 para marinho"], nome="Maria Silva")

print("\n\n########## D — Maria cancela um pedido DELA (FF-2026-0001) ##########")
conversa(["quero cancelar o pedido FF-2026-0001"], nome="Maria Silva")

print("\n\n########## R — consultando o que foi cancelado ##########")
conversa(["status do pedido FF-2026-0001"], nome="Maria Silva")

mostrar_csv("pedidos.csv DEPOIS")
