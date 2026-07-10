# -*- coding: utf-8 -*-
"""
conversas_simuladas.py — Simula 50 conversas multi-turno pelo pipeline REAL do bot.

Diferente da bateria (pergunta isolada), aqui cada conversa mantém a MESMA sessão
entre os turnos — então testa o que a bateria não pega: memória de contexto
(foco_atual), personalização por nome, navegação de menu, fluxo de CRUD de pedido
e roteamento de setor dentro de um diálogo.

Roda o mesmo fluxo do app.py por turno (segurança → nome → despedida → casual →
pipeline → personalizar) e grava o transcript em conversas_simuladas.txt, além de
um placar automático de qualidade no terminal.
"""
import os
import shutil
import sys
import tempfile

BOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BOT)

from bot.loader import carregar_dados
from bot.extractor import extrair_slots
from bot.classifier import classificar
from bot.responder import responder
from bot.seguranca import verificar_seguranca
from bot.cliente import tratar_nome, personalizar, primeiro_nome
from bot.contexto import (
    criar_sessao, resetar_sessao, is_despedida, is_casual,
    merge_com_contexto, atualizar_sessao_pos_turno,
)

DADOS = carregar_dados()

# ⚠️ Segurança dos dados: as conversas de CRUD gravam/cancelam pedidos. Apontamos
# o persistencia pra uma CÓPIA temporária, igual o test_crud faz — o
# data/pedidos.csv REAL nunca é tocado (mesma higiene do resto do projeto).
from bot.pedidos import persistencia
_TMP = tempfile.mkdtemp()
_COPIA = os.path.join(_TMP, "pedidos.csv")
shutil.copy(persistencia.CAMINHO_CSV, _COPIA)
persistencia.CAMINHO_CSV = _COPIA


def run_turn(sessao, msg):
    """Roda 1 turno pelo fluxo do app.py. Retorna (resposta, tag)."""
    bloqueio = verificar_seguranca(msg)
    if bloqueio:
        return bloqueio, "seguranca"

    resposta_nome = tratar_nome(msg, sessao)
    if resposta_nome is not None:
        return resposta_nome, "captura_nome"

    if is_despedida(msg):
        resetar_sessao(sessao)
        return "Até logo! Se precisar, é só voltar.", "despedida"

    if is_casual(msg) and sessao["ativa"]:
        return "Beleza, pode continuar!", "casual"

    em_menu = bool(sessao.get("aguardando_opcao"))
    st = extrair_slots(msg, em_menu=em_menu)
    se = merge_com_contexto(st, sessao, msg)
    intencao = classificar(msg, st, se, DADOS["intencoes"], sessao)
    resposta = responder(intencao, se, DADOS, sessao, msg)
    resposta = personalizar(resposta, sessao)
    atualizar_sessao_pos_turno(sessao, msg, se, intencao, resposta)
    return resposta, intencao


# ─────────────────────────────────────────────────────────────────────
# 50 CONVERSAS — cada uma é (tema, [turnos do usuário])
# ─────────────────────────────────────────────────────────────────────
CONVERSAS = [
 # ── A. Produção + follow-up de contexto ──────────────────────────
 ("Tecido por produto, troca de produto",
  ["oi", "Ana", "qual tecido pra camiseta", "e pra moletom?", "valeu"]),
 ("Prazo e refino com personalização",
  ["bom dia", "Rafael", "qual o prazo de uma camiseta", "e com bordado?", "obrigado"]),
 ("Cores e cor em tecido",
  ["ola", "Julia", "quais cores voces tem", "tem em viscose?", "tchau"]),
 ("Tamanho e plus size",
  ["oi", "Marcos", "quais tamanhos de polo", "tem plus size?"]),
 ("Tecido por estação",
  ["oi", "Bia", "qual tecido pra verao", "e pra inverno?"]),
 ("Personalização: tipos → silk → prazo",
  ["oi", "Leo", "quais tipos de personalizacao", "me explica o silk", "qual o prazo com silk"]),
 ("Sugestão academia → tecido → cor",
  ["eai", "Duda", "me sugere uma peca pra academia", "qual tecido é melhor", "e as cores?"]),
 ("Gramatura por produto",
  ["oi", "Hugo", "qual gramatura pra moletom", "e pra camiseta?"]),

 # ── B. Menus guiados ─────────────────────────────────────────────
 ("Menu qualidade → durabilidade",
  ["oi", "Paula", "quero saber da qualidade", "durabilidade"]),
 ("Menu sustentabilidade → vegano",
  ["oi", "Igor", "voces sao sustentaveis?", "tem produto vegano?"]),
 ("Menu manutenção → lavar → algodão",
  ["oi", "Sofia", "como cuido das pecas", "como lavar", "e o algodao?"]),
 ("Menu tecidos → composição",
  ["oi", "Bruno", "quais tecidos voces tem", "qual a composicao"]),
 ("Catálogo → camisetas → oversized",
  ["oi", "Lara", "o que voces produzem", "me fala das camisetas", "tem oversized?"]),
 ("Menu personalização → cores → tingimento",
  ["oi", "Caio", "quero personalizar", "quais cores disponiveis", "fazem tingimento?"]),

 # ── C. Orçamento / simulação ─────────────────────────────────────
 ("Preço → prazo → desconto de 100 camisetas",
  ["oi", "Vitor", "quanto custa 100 camisetas", "e o prazo delas?", "tem desconto por volume?"]),
 ("Viabilidade grande em prazo curto",
  ["oi", "Nina", "consigo 500 camisetas em 10 dias?"]),
 ("Consumo de tecido",
  ["oi", "Tiago", "quantos metros de tecido pra 200 moletons"]),
 ("Preço com personalização",
  ["oi", "Beatriz Rocha", "quanto fica 50 polos com bordado"]),
 ("Prazo de pedido grande",
  ["oi", "Rita", "qual o prazo pra 1000 pecas"]),
 ("Pedido urgente",
  ["oi", "Gabi", "preciso de 30 camisetas urgente"]),
 ("B2B uniforme completo",
  ["oi", "Sr Almeida", "uniforme pra empresa com logo, preco e prazo"]),
 ("Progressão de desconto",
  ["oi", "Fernando", "quanto mais eu compro mais barato fica?"]),

 # ── D. CRUD de pedidos ───────────────────────────────────────────
 ("Registrar pedido completo",
  ["oi", "Bia", "quero registrar um pedido", "camiseta", "100", "preto", "M", "algodao", "bordado"]),
 ("Registrar com dados já ditos",
  ["oi", "Bia", "quero fazer um pedido de 50 moletons pretos", "M", "moletom flanelado", "nenhuma"]),
 ("Status com ID (dono certo)",
  ["oi", "Maria Silva", "qual o status do meu pedido", "FF-2026-0001"]),
 ("Status sem ID depois com ID",
  ["oi", "Joao Souza", "quero acompanhar meu pedido", "FF-2026-0002"]),
 ("Alterar cor (em modelagem)",
  ["oi", "Joao Souza", "quero alterar a cor do pedido pra vermelho", "FF-2026-0002"]),
 ("Cancelar pedido (dono certo)",
  ["oi", "Ana Costa", "quero cancelar meu pedido", "FF-2026-0003"]),
 ("Cancelar pedido de outro (trava de dono)",
  ["oi", "Bia", "quero cancelar o pedido FF-2026-0001"]),
 ("Registrar e desistir no meio",
  ["oi", "Bia", "quero fazer um pedido", "camiseta", "desistir"]),

 # ── E. Encaminhamento de setor ───────────────────────────────────
 ("Preço/pagamento → vendas",
  ["oi", "Pedro", "quais as formas de pagamento?", "aceita cartao?"]),
 ("Frete → logística",
  ["oi", "Carla", "voces entregam em todo brasil?", "qual o valor do frete?"]),
 ("Devolução → devoluções",
  ["oi", "Bruna", "veio o tamanho errado, quero trocar"]),
 ("Fornecedor → compras",
  ["oi", "Distribuidora XPTO", "quero ser fornecedor de voces"]),
 ("Revenda (produção responde, não vendas)",
  ["oi", "Sandra", "quero revender as pecas de voces"]),
 ("Falar com humano",
  ["oi", "Otavio", "quero falar com um atendente de verdade"]),

 # ── F. Social + personalização ───────────────────────────────────
 ("Saudação, elogio e despedida",
  ["oi tudo bem?", "Aline", "voces fazem um trabalho otimo!", "era so isso, tchau"]),
 ("Gíria",
  ["salve mano", "Wesley", "e ai firmeza, voces fazem moletom?"]),
 ("Ofensa",
  ["oi", "Anon", "que bot horrivel, voce e inutil"]),
 ("Agradecimento no meio (não pode resetar)",
  ["oi", "Cris", "quais tecidos tem", "obrigado, e o prazo padrao?"]),
 ("Despedida reseta e volta",
  ["oi", "Dani", "quais cores tem", "tchau", "oi de novo", "Dani", "quais tamanhos"]),
 ("'não entendi' não vira casual",
  ["oi", "Rodrigo", "nao entendi"]),

 # ── G. Específicos ───────────────────────────────────────────────
 ("Sustentabilidade: químicos",
  ["oi", "Helena", "a tinta que voces usam faz mal a saude?"]),
 ("Qualidade: defeito → devoluções",
  ["oi", "Marcio", "minha peca chegou com defeito"]),
 ("Manutenção: encolheu",
  ["oi", "Fabi", "minha camiseta encolheu na lavagem"]),
 ("Tecido pra pele sensível",
  ["oi", "Val", "tenho pele sensivel, qual tecido voces indicam?"]),

 # ── H. Edge / segurança ──────────────────────────────────────────
 ("Segurança: número de cartão",
  ["oi", "Lucas", "meu cartao é 4111 1111 1111 1111, pode cobrar"]),
 ("Segurança: senha",
  ["oi", "Ester", "minha senha do site é 12345, guarda pra mim"]),
 ("Gibberish → fallback → reformula",
  ["oi", "Rui", "asdkjhaskd xpto", "quero saber dos prazos"]),
 ("Troca abrupta de assunto",
  ["oi", "Dora", "quais tecidos pra camiseta", "quero cancelar o pedido FF-2026-0009", "e a cor branca, tem?"]),
]


def main():
    linhas = []
    placar = []

    for i, (tema, turnos) in enumerate(CONVERSAS, 1):
        sessao = criar_sessao()
        linhas.append(f"\n{'='*72}\nCONVERSA {i:02d} — {tema}\n{'='*72}")
        nome_dado = None
        n_fallback = 0
        n_person_elegivel = 0
        n_person_ok = 0
        tags = []

        for msg in turnos:
            resp, tag = run_turn(sessao, msg)
            tags.append(tag)
            linhas.append(f"  🧑 {msg}")
            linhas.append(f"  🤖 [{tag}] {resp}")

            if tag == "fallback":
                n_fallback += 1
            # personalização: respostas de pipeline (não os atalhos sem nome)
            if sessao.get("nome_cliente") and tag not in (
                    "captura_nome", "casual", "despedida", "seguranca"):
                n_person_elegivel += 1
                pn = primeiro_nome(sessao["nome_cliente"])
                if resp.startswith(pn + ","):
                    n_person_ok += 1

        placar.append({
            "i": i, "tema": tema, "turnos": len(turnos),
            "fallback": n_fallback,
            "person": f"{n_person_ok}/{n_person_elegivel}",
            "tags": tags,
        })

    # grava transcript
    out = os.path.join(os.path.dirname(__file__), "conversas_simuladas.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    # placar
    print("=" * 72)
    print("  PLACAR — 50 CONVERSAS SIMULADAS")
    print("=" * 72)
    tot_turnos = sum(p["turnos"] for p in placar)
    tot_fb = sum(p["fallback"] for p in placar)
    print(f"  Conversas: {len(placar)} | Turnos: {tot_turnos} | Fallbacks: {tot_fb}")
    print()
    print(f"  {'#':>2}  {'fb':>2}  {'person':>7}  tema")
    for p in placar:
        flag = "  ⚠️" if p["fallback"] else ""
        print(f"  {p['i']:>2}  {p['fallback']:>2}  {p['person']:>7}  {p['tema']}{flag}")
    print(f"\nTranscript completo: {out}")


if __name__ == "__main__":
    main()
