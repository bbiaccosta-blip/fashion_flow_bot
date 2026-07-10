# -*- coding: utf-8 -*-
"""
bateria_premium.py — 100 perguntas sobre a linha PREMIUM, em muitas formas, pra
achar os buracos (o cliente pergunta de premium de mil jeitos e nem sempre recebe
a info da premium). Roda pelo pipeline real e categoriza a resposta.
"""
import os
import sys

BOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BOT)

from bot.loader import carregar_dados
from bot.extractor import extrair_slots
from bot.classifier import classificar
from bot.responder import responder
from bot.contexto import criar_sessao, merge_com_contexto, atualizar_sessao_pos_turno

DADOS = carregar_dados()

# 100 perguntas de premium, em formas variadas
PERGUNTAS = [
    # diretas
    "premium", "a premium", "camiseta premium", "camisa premium", "camisas premium",
    "camisetas premium", "linha premium", "modelo premium", "a linha premium",
    "quero saber da premium", "me fala da premium", "me fala sobre a premium",
    "me explica a premium", "explica a camiseta premium", "o que e a premium",
    "o que e a camiseta premium", "como e a premium", "sobre a premium",
    "sobre a linha premium", "detalhes da premium", "me da detalhes da premium",
    "informacao da premium", "quero informacao sobre a premium",
    # diferença básica x premium
    "qual a diferenca da premium", "diferenca entre premium e basica",
    "premium ou basica", "premium vs basica", "premium e basica diferenca",
    "por que a premium e mais cara", "vale a pena a premium",
    "a premium e melhor que a basica", "qual a vantagem da premium",
    "premium compensa", "a premium e melhor",
    # tecido/composição da premium
    "de que tecido e a premium", "qual tecido da premium", "premium e de algodao?",
    "a premium e algodao pima?", "composicao da premium", "do que e feita a premium",
    "premium e 100% algodao?", "que material a premium usa",
    # qualidade/durabilidade da premium
    "a premium e duravel", "premium dura mais", "a premium encolhe",
    "a premium desbota", "qualidade da premium", "a premium e resistente",
    "premium e macia", "a premium tem boa gramatura",
    # cores/tamanhos da premium
    "quais cores da premium", "cores da camiseta premium", "premium tem plus size",
    "tamanhos da premium", "premium tem tamanho gg", "a premium vem em preto",
    "premium tem cor branca", "premium infantil tem",
    # preço/prazo da premium (esperado: vendas / combinado)
    "quanto custa a premium", "preco da premium", "qual o valor da premium",
    "quanto sai a camiseta premium", "preco de 100 premium",
    "quanto custa 50 camisetas premium", "prazo da premium",
    "qual o prazo da camiseta premium", "prazo de 100 premium",
    "premium tem desconto",
    # personalização na premium
    "posso bordar na premium", "da pra fazer silk na premium", "premium aceita estampa",
    "personalizar a premium", "premium com bordado",
    # pedido de premium (esperado: registrar/combinado)
    "quero uma camiseta premium", "quero comprar premium", "quero 100 camisetas premium",
    "vou querer premium", "quero fazer um pedido de premium",
    "quero 50 camisas premium bordadas",
    # compatibilidade/uso
    "premium serve pra uniforme", "premium e boa pra revenda", "premium pra empresa",
    "a premium e pra que tipo de uso", "quando usar a premium",
    # perguntas coloquiais / com typo
    "essa premium ai", "fala da premium ai", "premiun", "camiseta premiun",
    "quero saber da premim", "a tal da premium", "essa linha premium e boa?",
    "premium eh melhor mesmo?", "vale mais a pena premium ne",
    # premium de outros produtos (pegadinha: premium é da camiseta)
    "moletom premium", "polo premium", "tem calca premium", "premium de moletom",
    # contexto (depois de falar de camisetas)
    "e a premium?", "e a versao premium?", "tem a opcao premium?",
    "qual a mais top", "a mais cara qual e",
]


def responder_uma(pergunta, contexto_camiseta=False):
    s = criar_sessao(); s["nome_cliente"] = "Bia"; s["ativa"] = True
    if contexto_camiseta:
        s["foco_atual"] = {"produto": "camiseta_basica"}
    st = extrair_slots(pergunta, em_menu=False)
    se = merge_com_contexto(st, s, msg)
    it = classificar(pergunta, st, se, DADOS["intencoes"], s)
    r = responder(it, se, DADOS, s, pergunta)
    return it, r


def categoriza(it, r):
    if it == "produto_detalhe":
        return "OK_premium"
    if it in ("setor_vendas", "combinado_preco_qtd_produto", "combinado_preco_personalizacao"):
        return "preco"        # ok se a pergunta era de preço
    if it in ("combinado_prazo_qtd_produto", "prazo_padrao", "prazo_com_personalizacao",
              "combinado_prazo_personalizacao_produto"):
        return "prazo"
    if it == "registrar_pedido":
        return "pedido"
    if it in ("cat_camisetas",):
        # catálogo genérico: menciona premium mas não foca — buraco parcial
        return "catalogo_generico"
    if it == "fallback":
        return "FALLBACK"
    return f"outro:{it}"


def main():
    from collections import Counter
    linhas = []
    cont = Counter()
    for p in PERGUNTAS:
        it, r = responder_uma(p)
        cat = categoriza(it, r)
        cont[cat] += 1
        linhas.append((p, it, cat, r))

    print("=" * 60)
    print(f"  BATERIA PREMIUM — {len(PERGUNTAS)} perguntas")
    print("=" * 60)
    for cat, n in cont.most_common():
        print(f"  {n:3d}  {cat}")
    print()
    print("=== BURACOS (catalogo generico, fallback, outro) ===")
    for p, it, cat, r in linhas:
        if cat in ("catalogo_generico", "FALLBACK") or cat.startswith("outro"):
            print(f"  [{cat:16}] {p!r:38} -> {it}")

    out = os.path.join(os.path.dirname(__file__), "premium_resultados.csv")
    import csv
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pergunta", "intencao", "categoria", "resposta"])
        for p, it, cat, r in linhas:
            w.writerow([p, it, cat, r.replace("\n", " ")])
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
