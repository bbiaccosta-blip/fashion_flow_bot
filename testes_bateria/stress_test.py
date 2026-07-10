# -*- coding: utf-8 -*-
"""
stress_test.py — Teste de ESTRESSE adversarial: joga entradas malucas no bot pra
achar onde ele QUEBRA (exceção) ou responde mal. Cada turno é protegido por
try/except (um crash é sinalizado, não derruba o teste). pedidos.csv usa cópia
temporária.

Sinaliza:
  CRASH     — o pipeline levantou exceção (o pior)
  VAZIO     — resposta vazia
  LIXO      — resposta com 'None', texto de dev, ou campo com pergunta
  FALLBACK  — não entendeu (tolerado em gibberish puro)
"""
import os
import re
import shutil
import sys
import tempfile
import traceback

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
from bot.cliente import tratar_nome, personalizar
from bot.contexto import (criar_sessao, resetar_sessao, is_despedida, is_casual,
                          merge_com_contexto, atualizar_sessao_pos_turno)
from bot.politica import limpar_menu_se_mudou_assunto

DADOS = carregar_dados()


def run_turn(sessao, msg):
    """Roda 1 turno pelo fluxo do app.py. Devolve (tag, resposta). Nunca crasha."""
    try:
        b = verificar_seguranca(msg)
        if b:
            return "seguranca", b
        rn = tratar_nome(msg, sessao)
        if rn is not None:
            return "nome", rn
        if is_despedida(msg):
            resetar_sessao(sessao); return "despedida", "Até logo!"
        if is_casual(msg) and sessao.get("ativa") and not sessao.get("aguardando_mais_produto"):
            return "casual", "Beleza!"
        limpar_menu_se_mudou_assunto(msg, sessao)
        em = bool(sessao.get("aguardando_opcao"))
        st = extrair_slots(msg, em_menu=em)
        se = merge_com_contexto(st, sessao, msg)
        it = classificar(msg, st, se, DADOS["intencoes"], sessao)
        r = responder(it, se, DADOS, sessao, msg)
        r = personalizar(r, sessao)
        atualizar_sessao_pos_turno(sessao, msg, se, it, r)
        return it, r
    except Exception as e:
        return "CRASH", f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


def flags_da_resposta(tag, r):
    fl = []
    if tag == "CRASH":
        fl.append("CRASH")
        return fl
    if r is None or str(r).strip() == "":
        fl.append("VAZIO")
    rl = str(r).lower()
    if "none" in rl or "nan" in re.findall(r"\bnan\b", rl) or "consultar lookup" in rl \
       or "inserir link" in rl and tag not in ("setor_vendas", "setor_logistica",
                                               "setor_compras", "setor_devolucao"):
        fl.append("LIXO")
    if "resumo:" in rl and re.search(r"resumo:.*\b(quais|qual|quanto|como|produtos|sei la|tanto)\b", rl):
        fl.append("PEDIDO_LIXO")
    return fl


# ───────────────── ENTRADAS ADVERSARIAIS (por categoria) ─────────────────
RODADAS = {
 "vazios/simbolos": ["", " ", "   ", "\n", "\t", "!!!", "???", "...", "---",
                     "@#$%", "***", "///", "()", "[]", "{}", ".", ",", "?!?!"],
 "numeros/estranhos": ["0", "-5", "999999999", "3.14", "1e10", "100000000000000",
                       "0000", "12 34 56", "R$ 50", "50%", "1/2", "2^32"],
 "emoji/unicode": ["😀", "👕👖👗", "🔥🔥🔥", "quero 👕", "❤️", "🤔?", "™®©",
                   "café ☕", "naïve", "ﬀ ligadura", "𝓺𝓾𝓮𝓻𝓸"],
 "typos": ["kero uma kamiseta", "camizeta", "personalizasao", "kanto custa",
           "keria saber do prasu", "moletonn", "vc faz calsa", "estanpa",
           "kuero konprar", "qero saber sobre tesido", "poloo", "vestdo"],
 "caps/pontuacao": ["QUERO UMA CAMISETA AGORA", "quero,uma,camiseta,ja!!!",
                    "P R E C I S O D E C A M I S E T A", "camiseta???!!!",
                    "QUAL O PREÇO???", "me. ajuda. por. favor."],
 "multi-intencao": ["qual o prazo e o preco e voces fazem moletom e como lavo",
                    "quero camiseta mas tambem quero saber de cor e tecido e prazo",
                    "oi tudo bem quero 100 camisetas qual o preco e voces entregam",
                    "cor prazo tecido tamanho preco tudo de uma vez",
                    "quero cancelar e tambem fazer um pedido novo"],
 "contradicao": ["quero e nao quero camiseta", "sim nao talvez",
                 "cancela mas nao cancela", "quero 100 nao 50 camisetas",
                 "preto branco na verdade azul nao sei"],
 "rambling-longo": ["entao assim oi bom dia eu estava pensando aqui que talvez "
                    "quem sabe eu poderia querer fazer um pedido mas nao sei bem "
                    "o que ainda porque depende do preco e do prazo e tambem da cor "
                    "e do tecido mas antes disso me fala tudo sobre voces por favor",
                    "camiseta " * 30, "quero " * 25 + "moletom"],
 "injecao/tecnico": ["'; DROP TABLE pedidos; --", "<script>alert(1)</script>",
                     "{{7*7}}", "${jndi:ldap://x}", "../../etc/passwd",
                     "SELECT * FROM pedidos", "null", "undefined", "NaN", "true"],
 "fora-de-dominio": ["qual a capital da franca", "me conta uma piada",
                     "quanto e 2+2", "voce me ama", "vai chover amanha",
                     "quem descobriu o brasil", "toca uma musica"],
 "provocacao-menu": ["7", "0", "99", "opcao 10", "nenhuma dessas", "outra",
                     "menu", "voltar", "sair do menu", "ajuda"],
}


def main():
    total, crashes, problemas = 0, [], []
    print("=" * 68)
    print("  STRESS TEST — entradas adversariais (1 turno cada, sessão limpa)")
    print("=" * 68)
    for rodada, entradas in RODADAS.items():
        n_fb = n_crash = n_lixo = 0
        for msg in entradas:
            total += 1
            s = criar_sessao(); s["nome_cliente"] = "Bia"; s["ativa"] = True
            tag, r = run_turn(s, msg)
            fl = flags_da_resposta(tag, r)
            if "CRASH" in fl:
                n_crash += 1; crashes.append((msg, r))
            if tag == "fallback":
                n_fb += 1
            if any(f in fl for f in ("VAZIO", "LIXO", "PEDIDO_LIXO")):
                n_lixo += 1; problemas.append((rodada, msg, tag, str(r)[:80], fl))
        print(f"  {rodada:22} {len(entradas):3d} inputs | fallback {n_fb:2d} | "
              f"CRASH {n_crash} | lixo/vazio {n_lixo}")

    print("\n" + "=" * 68)
    print(f"  TOTAL: {total} inputs | CRASHES: {len(crashes)} | "
          f"problemas(lixo/vazio): {len(problemas)}")
    print("=" * 68)
    if crashes:
        print("\n### CRASHES (o pior — corrigir):")
        for msg, tb in crashes[:10]:
            print(f"  🧨 {msg!r}\n     {tb.splitlines()[0]}")
    if problemas:
        print("\n### LIXO/VAZIO:")
        for rod, msg, tag, resp, fl in problemas[:25]:
            print(f"  [{','.join(fl)}] ({rod}) {msg!r:30} -> [{tag}] {resp}")


if __name__ == "__main__":
    main()
