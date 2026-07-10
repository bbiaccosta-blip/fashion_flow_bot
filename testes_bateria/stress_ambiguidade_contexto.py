# -*- coding: utf-8 -*-
"""
Stress test de ambiguidade, contexto e resolução de problema.
Mede se o bot ajuda o cliente a resolver algo, ou se só devolve menu/fallback/setor.
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
MENU = re.compile(r"\n\s+1\. ")
BAD = re.compile(r"consultar lookup|resposta din[aâ]mica|\bnone\b|\bnan\b|\(inserir link\)", re.I)


def sessao_nomeada():
    s = criar_sessao()
    s["ativa"] = True
    s["nome_cliente"] = "Bia"
    return s


def run_turn(sessao, msg):
    try:
        b = verificar_seguranca(msg)
        if b:
            return "seguranca", b, {}, dict(sessao.get("foco_atual", {}))
        if is_despedida(msg):
            resetar_sessao(sessao)
            return "despedida", "Até logo!", {}, {}
        if is_casual(msg) and sessao.get("ativa") and not sessao.get("aguardando_mais_produto"):
            return "casual", "Beleza, pode continuar!", {}, dict(sessao.get("foco_atual", {}))
        limpar_menu_se_mudou_assunto(msg, sessao)
        st = extrair_slots(msg, em_menu=bool(sessao.get("aguardando_opcao")))
        se = merge_com_contexto(st, sessao, msg)
        it = classificar(msg, st, se, DADOS["intencoes"], sessao)
        resp = responder(it, se, DADOS, sessao, msg)
        resp = personalizar(resp, sessao)
        atualizar_sessao_pos_turno(sessao, msg, se, it, resp)
        return it, resp, st, dict(sessao.get("foco_atual", {}))
    except Exception as e:
        return "CRASH", f"{type(e).__name__}: {e}", {}, dict(sessao.get("foco_atual", {}))


def step(msg, goal, expect=None, must=None, forbid=None, note=""):
    return {
        "msg": msg,
        "goal": goal,  # solve, clarify, preserve_context, reset_context, avoid_harm
        "expect": set(expect or []),
        "must": [x.lower() for x in (must or [])],
        "forbid": [x.lower() for x in (forbid or [])],
        "note": note,
    }

SCENARIOS = {
    "pronome_produto_premium": [
        step("me fala da camiseta premium", "preserve_context", {"produto_detalhe"}, ["pima"]),
        step("ela tem quais tecidos?", "solve", {"combinado_tecidos_disponiveis_para_produto"}, ["pima"], ["fallback"]),
        step("e quanto custa 100 dela?", "solve", {"combinado_preco_qtd_produto"}, ["100", "premium", "r$"]),
        step("e o prazo?", "solve", {"combinado_prazo_qtd_produto"}, ["100", "premium"]),
        step("ela tem azul?", "solve", {"cores_basicas", "combinado_cor_em_tecido", "personalizacao_cores"}, ["azul"], ["total estimado"], "cor nao deve repetir preço"),
    ],
    "troca_produto_limpa_filhos": [
        step("quanto custa 100 camisetas pretas de algodao", "preserve_context", {"combinado_preco_qtd_produto"}, ["100"]),
        step("e de moletom?", "reset_context", {"cat_moletons", "combinado_preco_qtd_produto"}, ["moletom"], ["algodao", "preto em"], "ao trocar produto, filhos cor/tecido antigos nao devem contaminar"),
        step("qual tecido dele?", "solve", {"combinado_tecidos_disponiveis_para_produto", "tecidos"}, ["moletom"], ["camiseta"]),
        step("tem cinza?", "solve", {"cores_basicas", "combinado_cor_em_tecido", "personalizacao_cores"}, ["cinza"], ["camiseta"]),
    ],
    "contexto_cor_nao_contamina_tecido_produto": [
        step("preto em algodao tem?", "solve", {"combinado_cor_em_tecido"}, ["preto", "algodao"]),
        step("linho em camiseta da?", "solve", {"combinado_tecido_em_produto"}, ["linho", "camiseta"], ["preto"]),
        step("e viscose?", "solve", {"combinado_tecido_em_produto", "tecidos"}, ["viscose"], ["preto"]),
    ],
    "pedido_atrasado_sem_numero": [
        step("meu pedido atrasou", "clarify", {"prazo_atraso", "status_pedido"}, ["pedido"], ["menu"]),
        step("nao sei o numero", "clarify", {"status_pedido", "prazo_atraso"}, ["número"], ["fallback"]),
        step("acho que era FF-2026-0001", "solve", {"status_pedido"}, ["pedido"]),
        step("posso acelerar?", "clarify", {"prazo_urgente", "status_pedido", "setor_vendas"}, ["prazo"], ["fallback"]),
    ],
    "defeito_cliente_irritado": [
        step("minha peça veio com defeito", "solve", {"qualidade_defeito", "setor_devolucao"}, ["defeito"], ["inserir link", "menu"]),
        step("a costura veio torta", "solve", {"qualidade_defeito"}, ["defeito"], ["corte automatizado", "esporte"]),
        step("quero resolver isso", "clarify", {"qualidade_defeito", "setor_devolucao", "status_pedido"}, ["pedido"], ["fallback"]),
    ],
    "cliente_nao_sabe_o_que_quer": [
        step("preciso de roupa pra evento da empresa mas nao sei qual", "clarify", {"sug_trabalho", "sugestao_produto", "cat_uniformes", "multi_intencao"}, ["empresa"], ["fallback"]),
        step("vai ser em local quente", "solve", {"sug_verao", "sug_tec_quente", "sug_tecido_uso"}, ["quente"], ["fallback"]),
        step("tem que ter logo", "solve", {"personalizacao_bordado", "personalizacao_silkscreen", "personalizacao"}, ["logo"], ["fallback"]),
        step("qual fica mais barato?", "clarify", {"setor_vendas", "combinado_preco_personalizacao", "combinado_preco_qtd_produto"}, ["valor", "preço", "vendas"], ["fallback"]),
    ],
    "orcamento_com_correcoes": [
        step("quero 100 camisetas", "clarify", {"registrar_pedido", "cat_camisetas", "combinado_preco_qtd_produto"}, ["camiseta"]),
        step("na verdade 150", "preserve_context", {"registrar_pedido", "combinado_preco_qtd_produto", "fallback"}, ["150"], [], "deveria corrigir quantidade sem perder produto"),
        step("quanto fica?", "solve", {"combinado_preco_qtd_produto"}, ["150", "r$"]),
        step("troca pra polo", "reset_context", {"cat_camisetas", "combinado_preco_qtd_produto", "alterar_pedido_especifico"}, ["polo"], ["camiseta basica"]),
        step("e 200?", "solve", {"combinado_preco_qtd_produto"}, ["200", "polo"]),
    ],
    "registro_interrompido_e_retomado": [
        step("quero fazer pedido", "clarify", {"registrar_pedido"}, ["qual produto"]),
        step("moletom", "clarify", {"registrar_pedido"}, ["quantas"]),
        step("qual tecido é melhor pra frio?", "solve", {"sug_tec_frio", "sug_inverno", "tecidos"}, ["frio"], ["anotei o item"]),
        step("50", "clarify", {"registrar_pedido"}, ["qual cor"]),
        step("cinza", "clarify", {"registrar_pedido"}, ["tamanho"]),
        step("moletom flanelado", "preserve_context", {"registrar_pedido"}, ["tamanho"], [], "deveria confirmar tecido anotado"),
        step("G", "clarify", {"registrar_pedido"}, ["personalização"]),
        step("sem estampa", "solve", {"registrar_pedido"}, ["anotei"]),
        step("nao", "solve", {"finalizar_pedidos"}, ["pedido registrado"]),
    ],
    "ambiguidade_menu_e_texto": [
        step("personalização", "solve", {"personalizacao"}, ["bordado"], ["1."]),
        step("tipos", "clarify", {"personalizacao_tipos"}, ["silkscreen"], [], "aqui menu pode aparecer se pediu tipos"),
        step("bordado", "solve", {"personalizacao_bordado"}, ["bordado"]),
        step("e prazo?", "solve", {"prazo_com_personalizacao", "combinado_prazo_personalizacao_produto"}, ["bordado", "prazo"]),
    ],
    "fora_dominio_sem_atrapalhar": [
        step("qual a capital da franca", "avoid_harm", {"fallback"}, [], ["produção no brasil", "silk", "pedido registrado"]),
        step("ok mas e camiseta premium?", "solve", {"produto_detalhe", "cat_camisetas"}, ["premium"], ["fallback"]),
        step("ela custa quanto pra 100?", "solve", {"combinado_preco_qtd_produto"}, ["100", "premium"]),
    ],
}

failures=[]
score=Counter()
examples=[]
for name, steps in SCENARIOS.items():
    sessao = sessao_nomeada()
    prev_resp = None
    for idx, e in enumerate(steps, 1):
        it, resp, st, foco = run_turn(sessao, e['msg'])
        resp_l = resp.lower()
        issues=[]
        if it == 'CRASH':
            issues.append('CRASH')
        if e['expect'] and it not in e['expect']:
            issues.append(f'intent={it}, esperado={sorted(e["expect"])}')
        for m in e['must']:
            if m.lower() not in resp_l:
                issues.append(f'faltou:{m}')
        for f in e['forbid']:
            if f.lower() in resp_l:
                issues.append(f'proibido:{f}')
        if BAD.search(resp):
            issues.append('placeholder/link/None')
        if it == 'fallback' and e['goal'] != 'avoid_harm':
            issues.append('fallback_em_problema_real')
        if prev_resp and resp == prev_resp and e['goal'] != 'preserve_context':
            issues.append('resposta_repetida')
        if MENU.search(resp) and e['goal'] in ('solve','preserve_context','reset_context') and 'tipos' not in e['msg'] and 'opções' not in e['msg']:
            issues.append('menu_atrapalhou')
        if issues:
            failures.append((name, idx, e, it, resp[:220].replace('\n',' | '), issues, dict(foco)))
            for issue in issues:
                score[issue.split(':')[0].split('=')[0]] += 1
        prev_resp = resp

print('='*100)
print('STRESS AMBIGUIDADE + RESOLUÇÃO DE PROBLEMAS + COERÊNCIA DE CONTEXTO')
print('='*100)
print(f'Cenários: {len(SCENARIOS)}')
print(f'Turnos: {sum(len(v) for v in SCENARIOS.values())}')
print(f'Falhas detectadas: {len(failures)}')
print('\nTipos de falha:')
for k,v in score.most_common():
    print(f'  {v:2d}  {k}')
print('\nFalhas detalhadas:')
for name, idx, e, it, resp, issues, foco in failures[:80]:
    print(f"\n[{name} t{idx}] objetivo={e['goal']} msg={e['msg']!r}")
    print(f"  intent: {it}")
    print(f"  resp: {resp}")
    print(f"  foco: {foco}")
    for issue in issues:
        print(f"  - {issue}")
    if e['note']:
        print(f"  nota: {e['note']}")
