# -*- coding: utf-8 -*-
"""
Bateria de estresse multi-turno focada em comportamento real de cliente.
Roda contra a worktree atual e sinaliza fricções de UX, não só crashes.
"""
import os
import re
import sys
import shutil
import tempfile
from collections import Counter, defaultdict

BOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BOT)

from bot.pedidos import persistencia
_TMP = tempfile.mkdtemp()
_C = os.path.join(_TMP, "pedidos.csv")
shutil.copy(persistencia.CAMINHO_CSV, _C)
persistencia.CAMINHO_CSV = _C

from bot.loader import carregar_dados
from bot.extractor import extrair_slots
from bot.classifier import classificar
from bot.responder import responder
from bot.seguranca import verificar_seguranca
from bot.cliente import personalizar
from bot.contexto import (criar_sessao, resetar_sessao, is_despedida, is_casual,
                          merge_com_contexto, atualizar_sessao_pos_turno)
from bot.politica import limpar_menu_se_mudou_assunto

DADOS = carregar_dados()
PLACEHOLDER = re.compile(r"consultar lookup|resposta dinamica|resposta dinâmica|\bnone\b|\bnan\b", re.I)
MENU_LIKE = re.compile(r"\n\s+1\. ")


def nova_sessao():
    s = criar_sessao()
    s["nome_cliente"] = "Bia"
    s["ativa"] = True
    return s


def run_turn(sessao, msg):
    try:
        bloqueio = verificar_seguranca(msg)
        if bloqueio:
            return "seguranca", bloqueio
        if is_despedida(msg):
            resetar_sessao(sessao)
            return "despedida", "Até logo!"
        if is_casual(msg) and sessao.get("ativa") and not sessao.get("aguardando_mais_produto"):
            return "casual", "Beleza, pode continuar!"
        limpar_menu_se_mudou_assunto(msg, sessao)
        st = extrair_slots(msg, em_menu=bool(sessao.get("aguardando_opcao")))
        se = merge_com_contexto(st, sessao, msg)
        it = classificar(msg, st, se, DADOS["intencoes"], sessao)
        r = responder(it, se, DADOS, sessao, msg)
        r = personalizar(r, sessao)
        atualizar_sessao_pos_turno(sessao, msg, se, it, r)
        return it, r
    except Exception as e:
        return "CRASH", f"{type(e).__name__}: {e}"


CENARIOS = {
    "cliente_apressado_preco_prazo_pers": [
        "oi", "preciso de 100 camisetas pretas", "quanto custa?", "e o prazo?",
        "com bordado muda?", "e se forem 200?", "frete voces veem?", "beleza vou pensar",
    ],
    "revendedor_exploratorio": [
        "quero comprar 500 camisetas pra revender", "tem desconto no atacado?",
        "posso escolher varias cores?", "e misturar tamanhos?", "qual prazo pra 500?",
        "a premium vale mais pra revenda?", "compara com a basica", "vou analisar",
    ],
    "pedido_existente_sem_id_no_inicio": [
        "fiz um pedido semana passada", "quero saber como ta", "FF-2026-0001",
        "posso mudar a cor?", "trocar pra azul", "nao tenho certeza do numero", "voltar",
    ],
    "registro_com_duvidas_no_meio": [
        "quero fazer um pedido", "camiseta premium", "quantas cores tem?",
        "100", "preto", "algodao pima", "M", "quanto custa o bordado?",
        "beleza bordado entao", "nao quero mais produto",
    ],
    "menus_ignorados_naturalmente": [
        "me fala de personalizacao", "quero bordado", "quanto demora?",
        "e silk?", "quais cores tem?", "preto em algodao da?", "voltar",
        "como lavar camiseta?", "amaciante pode?", "e ferro?",
    ],
    "premium_followups": [
        "quero saber tudo sobre camiseta premium", "ela e boa mesmo?",
        "compara com a basica pra mim", "quanto custa 100 premium?", "e 200?",
        "tem azul?", "qual tecido dela?", "vou pensar",
    ],
    "rajada_curta": [
        "preco", "prazo", "cor", "tecido", "tamanho", "personalizacao",
        "qualidade", "lavar", "sustentabilidade", "catalogo",
    ],
    "empresa_uniforme_longo": [
        "sou de uma escola", "preciso de uniforme", "polo com nosso logo",
        "200 pecas", "tem infantil e adulto?", "mistura tamanho?", "prazo?",
        "e preco?", "quero fazer pedido", "polo", "200", "marinho", "algodao", "adulto", "bordado", "nao",
    ],
    "curioso_marca_e_sustentabilidade": [
        "voces sao brasileiros?", "onde ficam?", "quanto tempo de mercado?",
        "voces se preocupam com meio ambiente?", "trabalham com fibra reciclada?",
        "o algodao e organico?", "a tinta e toxica?", "usam couro animal?",
        "legal obrigado",
    ],
    "maratona_45_turnos": [
        "oi", "catalogo", "camiseta", "premium", "ela e boa?", "preco 100 camisetas",
        "e 200?", "prazo", "com bordado?", "quero saber de qualidade", "durabilidade",
        "defeito como funciona", "personalizacao", "tipos", "bordado", "dtf", "cores",
        "preto em algodao", "tecidos", "algodao pima", "linho em camiseta da?",
        "sustentabilidade", "material reciclado", "tinta toxica", "como lavar", "amaciante pode",
        "secadora?", "quero fazer pedido", "camiseta premium", "100", "preto", "algodao pima",
        "M", "bordado", "quero mais produto", "moletom", "50", "cinza", "moletom flanelado",
        "G", "sem estampa", "nao", "FF-2026-0001", "tchau",
    ],
}


def analisar_turnos(nome, linhas):
    problemas = []
    last_resp = None
    last_ints = []
    menu_aberto_turno = None
    for i, row in enumerate(linhas, 1):
        msg, intent, resp, foco, estado, aguardando = row
        low = resp.lower()
        if intent == "CRASH":
            problemas.append(("CRASH", i, msg, resp[:120]))
        if intent == "fallback" and foco:
            problemas.append(("FALLBACK_COM_FOCO", i, msg, f"foco={foco}"))
        if PLACEHOLDER.search(resp):
            problemas.append(("LIXO_PLACEHOLDER", i, msg, resp[:140]))
        if last_resp and resp == last_resp and intent not in ("casual", "despedida"):
            problemas.append(("RESPOSTA_REPETIDA", i, msg, intent))
        if intent == "registrar_pedido" and re.search(r"\?|quanto|qual|prazo|preco|preço|posso", msg.lower()):
            problemas.append(("PERGUNTA_VIROU_REGISTRO", i, msg, resp[:140]))
        if MENU_LIKE.search(resp):
            menu_aberto_turno = i
        elif menu_aberto_turno and i == menu_aberto_turno + 1 and not re.fullmatch(r"\s*\d+\s*", msg):
            # menu foi ignorado; só é problema se virou selecao_opcao/fallback
            if intent in ("selecao_opcao", "fallback"):
                problemas.append(("MENU_PRENDEU", i, msg, intent))
            menu_aberto_turno = None
        last_ints.append(intent)
        if len(last_ints) > 4:
            last_ints.pop(0)
        if len(last_ints) == 4 and len(set(last_ints)) == 1 and intent not in ("registrar_pedido", "casual"):
            problemas.append(("INTENCAO_TRAVADA", i, msg, intent))
        last_resp = resp
    return problemas


def main(verbose=False):
    resumo = Counter()
    problemas_por_tipo = defaultdict(list)
    intents = Counter()
    total_turnos = total_menus = total_fallback = total_crash = 0
    for nome, msgs in CENARIOS.items():
        sessao = nova_sessao()
        linhas = []
        if verbose:
            print("\n" + "=" * 80 + f"\n{nome}\n" + "=" * 80)
        for msg in msgs:
            total_turnos += 1
            it, resp = run_turn(sessao, msg)
            intents[it] += 1
            total_fallback += it == "fallback"
            total_crash += it == "CRASH"
            total_menus += bool(MENU_LIKE.search(resp))
            linhas.append((msg, it, resp, dict(sessao.get("foco_atual", {})), sessao.get("estado_conversa"), sessao.get("aguardando_opcao")))
            if verbose:
                clean = resp.replace("\n", " | ")[:180]
                print(f"> {msg}\n[{it}] {clean}")
        for tipo, i, msg, detalhe in analisar_turnos(nome, linhas):
            problemas_por_tipo[tipo].append((nome, i, msg, detalhe))
            resumo[tipo] += 1
    print("=" * 80)
    print("BATERIA LONGA — CLIENTE REAL + MENUS")
    print("=" * 80)
    print(f"cenários: {len(CENARIOS)}")
    print(f"turnos: {total_turnos}")
    print(f"menus abertos: {total_menus}")
    print(f"fallbacks: {total_fallback}")
    print(f"crashes: {total_crash}")
    print("\nTOP intenções:")
    for intent, n in intents.most_common(12):
        print(f"  {n:3d}  {intent}")
    print("\nPROBLEMAS:")
    if not resumo:
        print("  nenhum problema automático detectado")
    for tipo, n in resumo.most_common():
        print(f"\n- {tipo}: {n}")
        for nome, i, msg, detalhe in problemas_por_tipo[tipo][:8]:
            print(f"  [{nome}] t{i}: {msg!r} -> {detalhe}")


if __name__ == "__main__":
    main(verbose="--verbose" in sys.argv)
