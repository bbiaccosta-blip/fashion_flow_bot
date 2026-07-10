# -*- coding: utf-8 -*-
"""
cenarios_pedido.py — 50 cenários de PEDIDO multi-turno: vários produtos numa
conversa, dúvidas no meio do registro, cancelamentos e alterações.

Roda pelo pipeline real com o persistencia apontado pra uma CÓPIA temporária
(o pedidos.csv real fica intacto), grava o transcript e sinaliza problemas:
fallback inesperado, pedido gravado com LIXO (valor de campo que é pergunta),
ou loop travado (mesma re-pergunta 3x seguidas).
"""
import os
import re
import shutil
import sys
import tempfile

BOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BOT)

from bot.pedidos import persistencia
_TMP = tempfile.mkdtemp()
_COPIA = os.path.join(_TMP, "pedidos.csv")
shutil.copy(persistencia.CAMINHO_CSV, _COPIA)
persistencia.CAMINHO_CSV = _COPIA

from bot.loader import carregar_dados
from bot.extractor import extrair_slots
from bot.classifier import classificar
from bot.responder import responder
from bot.seguranca import verificar_seguranca
from bot.cliente import tratar_nome, personalizar
from bot.contexto import (criar_sessao, resetar_sessao, is_despedida, is_casual,
                          merge_com_contexto, atualizar_sessao_pos_turno)

DADOS = carregar_dados()


def run_turn(sessao, msg):
    if verificar_seguranca(msg):
        return "(seguranca)", verificar_seguranca(msg)
    rn = tratar_nome(msg, sessao)
    if rn is not None:
        return "(nome)", rn
    if is_despedida(msg):
        resetar_sessao(sessao); return "(despedida)", "Até logo!"
    if is_casual(msg) and sessao["ativa"] and not sessao.get("aguardando_mais_produto"):
        return "(casual)", "Beleza, pode continuar!"
    em = bool(sessao.get("aguardando_opcao"))
    st = extrair_slots(msg, em_menu=em)
    se = merge_com_contexto(st, sessao, msg)
    it = classificar(msg, st, se, DADOS["intencoes"], sessao)
    r = responder(it, se, DADOS, sessao, msg)
    r = personalizar(r, sessao)
    atualizar_sessao_pos_turno(sessao, msg, se, it, r)
    return it, r


P = "quero 100 camisas de linho"  # atalho comum
CENARIOS = [
 # ── A. Multi-produto (12) ────────────────────────────────────────
 ("2 produtos, finaliza com nao", ["oi","Ana","quero 100 camisetas","preto","M","algodao","nenhuma","sim, 50 polos","branco","G","algodao","bordado","nao"]),
 ("3 produtos", ["oi","Bia","quero 50 camisetas pretas","M","algodao","nenhuma","mais 30 moletons","cinza","G","moletom flanelado","silk","e 20 regatas","branco","P","algodao","nenhuma","so isso"]),
 ("produto ja no inicio, add mais", ["oi","Leo","quero fazer um pedido","camiseta","100","preto","M","algodao","nenhuma","quero adicionar polos tambem","50","branco","G","algodao","nenhuma","nada mais"]),
 ("add produto sem quantidade", ["oi","Rui","quero 40 bermudas","preta","G","jeans","nenhuma","sim","mais uma camiseta","30","branco","M","algodao","nenhuma","nao"]),
 ("finaliza com 'pode fechar'", ["oi","Dora","quero 200 uniformes","marinho","G","algodao","bordado","pode fechar"]),
 ("dois iguais cores diferentes", ["oi","Vi","quero 100 camisetas pretas","M","algodao","nenhuma","mais 100 camisetas brancas","M","algodao","nenhuma","chega"]),
 ("add depois de dizer nao... muda ideia", ["oi","Tom","quero 60 moletons","cinza","G","moletom flanelado","silk","nao","quero mais um pedido de camisetas","50","preto","M","algodao","nenhuma","nao"]),
 ("varios com personalizacao", ["oi","Sam","quero 100 polos bordados","branco","G","algodao","bordado","mais 50 camisetas com silk","preto","M","algodao","silk","era so"]),
 ("finaliza logo (1 so)", ["oi","Rita","quero 100 camisetas","preto","M","algodao","nenhuma","nao"]),
 ("4 produtos seguidos", ["oi","Gu","quero 30 camisetas","preto","M","algodao","nenhuma","30 polos","branco","G","algodao","nenhuma","30 regatas","azul","P","algodao","nenhuma","30 moletons","cinza","GG","moletom flanelado","nenhuma","finalizar"]),
 ("mistura infantil", ["oi","Bel","quero 50 camisetas infantil","amarelo","infantil","algodao","nenhuma","mais 20 moletons infantil","rosa","infantil","moletom flanelado","nenhuma","nao"]),
 ("plus size no pedido", ["oi","Nal","quero 40 camisetas plus size","preto","plus size","algodao","nenhuma","nao"]),

 # ── B. Dúvida NO MEIO do registro (13) ───────────────────────────
 ("pergunta produtos no meio", ["oi","Ceu",P,"quais outros produtos tem","preto","M","nenhuma","nao"]),
 ("pergunta preco no meio", ["oi","Duda",P,"quanto custa","preto","M","nenhuma","nao"]),
 ("pergunta prazo no meio", ["oi","Edu",P,"qual o prazo","preto","M","nenhuma","nao"]),
 ("pergunta cor disponivel no meio", ["oi","Fael",P,"quais cores tem","preto","M","nenhuma","nao"]),
 ("pergunta tecido no meio", ["oi","Gi",P,"quais tecidos","preto","M","nenhuma","nao"]),
 ("resposta sem sentido no campo", ["oi","Hel",P,"sei la","preto","M","nenhuma","nao"]),
 ("digita numero no lugar da cor", ["oi","Ian",P,"12345","preto","M","nenhuma","nao"]),
 ("pergunta sobre premium no meio", ["oi","Ju",P,"me fala da premium","preto","M","nenhuma","nao"]),
 ("saudacao no meio", ["oi","Kau",P,"oi tudo bem","preto","M","nenhuma","nao"]),
 ("pergunta manutencao no meio", ["oi","Lia",P,"como lavar","preto","M","nenhuma","nao"]),
 ("tanto faz na cor e no tecido", ["oi","Mel","quero 80 camisetas","tanto faz","M","tanto faz","nenhuma","nao"]),
 ("pergunta e depois responde certo", ["oi","ना","quero 90 polos","voces entregam?","branco","G","algodao","nenhuma","nao"]),
 ("elogio no meio", ["oi","Ori",P,"voce e otimo","preto","M","nenhuma","nao"]),

 # ── C. Cancelamentos (12) ────────────────────────────────────────
 ("cancela no comeco", ["oi","Pat","quero fazer um pedido","cancelar"]),
 ("cancela no meio (desistir)", ["oi","Rai",P,"desistir"]),
 ("cancela com 'deixa pra la'", ["oi","Sol",P,"preto","deixa pra la"]),
 ("cancela e comeca de novo", ["oi"," Th",P,"cancelar","quero 30 polos","branco","G","algodao","nenhuma","nao"]),
 ("cancela pedido ja existente (dono)", ["oi","Ana Costa","quero cancelar o pedido FF-2026-0003"]),
 ("cancela pedido de outro (trava)", ["oi","Zé","quero cancelar o pedido FF-2026-0001"]),
 ("cancela sem numero, informa depois", ["oi","Ana Costa","quero cancelar meu pedido","FF-2026-0003"]),
 ("cancela no meio do 2o produto", ["oi","Bru","quero 50 camisetas","preto","M","algodao","nenhuma","mais 30 polos","cancelar"]),
 ("cancela e finaliza o que tinha", ["oi","Cau","quero 50 camisetas","preto","M","algodao","nenhuma","sim","desistir"]),
 ("cancela pedido inexistente", ["oi","Dan","quero cancelar o pedido FF-2026-9999"]),
 ("cancela com 'esquece'", ["oi","Eli",P,"esquece"]),
 ("cancela e pergunta outra coisa", ["oi","Fe",P,"cancelar","quais produtos tem"]),

 # ── D. Alterações (8) ────────────────────────────────────────────
 ("altera cor (Joao Souza, modelagem)", ["oi","Joao Souza","quero mudar a cor do pedido pra vermelho","FF-2026-0002"]),
 ("altera tecido", ["oi","Joao Souza","quero mudar o tecido para viscose","FF-2026-0002"]),
 ("altera quantidade", ["oi","Joao Souza","quero alterar a quantidade para 120","FF-2026-0002"]),
 ("altera sem numero, informa depois", ["oi","Joao Souza","quero alterar a cor","FF-2026-0002"]),
 ("altera pedido ja no corte (nao pode)", ["oi","Maria Silva","mudar cor pra azul","FF-2026-0001"]),
 ("altera de outro dono (trava)", ["oi","Estranho","mudar a cor pra verde","FF-2026-0002"]),
 ("altera pedido inexistente", ["oi","Xu","alterar cor pra preto","FF-2026-9999"]),
 ("registra e ja quer alterar", ["oi","Yas","quero 50 camisetas","preto","M","algodao","nenhuma","nao","quero mudar a cor pra branco"]),

 # ── E. Mistas / edge (5) ─────────────────────────────────────────
 ("typo no produto", ["oi","Ada","quero 100 camists","preto","M","algodao","nenhuma","nao"]),
 ("muda de ideia no produto", ["oi","Ben","quero 100 camisetas","na verdade quero moletons","cinza","G","moletom flanelado","nenhuma","nao"]),
 ("pergunta status no meio de registro", ["oi","Ci",P,"qual o status do meu pedido","preto","M","nenhuma","nao"]),
 ("registra, status, novo pedido", ["oi","Ana Costa","quero 20 polos","branco","G","algodao","nenhuma","nao","qual o status do FF-2026-0003","FF-2026-0003"]),
 ("despedida no meio do pedido", ["oi","Duh",P,"tchau"]),
]


def problemas_do_transcript(turns):
    flags = []
    reasks = 0
    last_reask = None
    for msg, it, r in turns:
        if it == "fallback":
            flags.append(f"FALLBACK em {msg!r}")
        if "não parece" in r:
            key = r[:40]
            reasks = reasks + 1 if key == last_reask else 1
            last_reask = key
            if reasks >= 3:
                flags.append(f"LOOP travado perto de {msg!r}")
        else:
            reasks = 0; last_reask = None
        # pedido gravado com lixo?
        m = re.search(r"Resumo: (.+?)\. Ele começa", r)
        if m:
            resumo = normalizar_resumo(m.group(1))
            if re.search(r"\b(quais|qual|quanto|como|produtos|tanto|sei la|status)\b", resumo):
                flags.append(f"PEDIDO COM LIXO: {m.group(1)[:70]}")
    return flags


def normalizar_resumo(s):
    return s.lower()


def main():
    linhas, todos_flags = [], []
    for i, (tema, turnos) in enumerate(CENARIOS, 1):
        s = criar_sessao()
        registro = []
        linhas.append(f"\n{'='*70}\nCENARIO {i:02d} — {tema}\n{'='*70}")
        for msg in turnos:
            it, r = run_turn(s, msg)
            registro.append((msg, it, r))
            linhas.append(f"  🧑 {msg}\n  🤖 [{it}] {r}")
        flags = problemas_do_transcript(registro)
        if flags:
            todos_flags.append((i, tema, flags))

    out = os.path.join(os.path.dirname(__file__), "cenarios_pedido.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print("=" * 70)
    print(f"  50 CENARIOS DE PEDIDO — {len(CENARIOS)} cenarios")
    print("=" * 70)
    if not todos_flags:
        print("  ✅ Nenhum problema sinalizado (sem fallback, lixo ou loop).")
    else:
        print(f"  ⚠️  {len(todos_flags)} cenarios com sinal:")
        for i, tema, flags in todos_flags:
            print(f"  #{i:02d} {tema}")
            for fl in flags:
                print(f"       - {fl}")
    print(f"\nTranscript: {out}")


if __name__ == "__main__":
    main()
