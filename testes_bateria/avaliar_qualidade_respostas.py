# -*- coding: utf-8 -*-
"""
Avalia qualidade percebida das respostas, não só acerto de intenção.

Notas:
- 2 = boa: responde a necessidade ou encaminha com próximo passo claro.
- 1 = aceitável: útil, mas genérica ou em categoria vizinha.
- 0 = ruim: fallback indevido, placeholder, setor claramente errado ou sem ação.
"""
import csv
import os
import re
from collections import Counter, defaultdict

HERE = os.path.dirname(__file__)
RESULTADOS = os.path.join(HERE, "resultados.csv")
SAIDA = os.path.join(HERE, "qualidade_respostas.csv")

PLACEHOLDER = re.compile(r'\(inserir link\)|\bnone\b|\bnan\b|resposta din[aâ]mica|consultar lookup', re.I)

EXPECTATIVAS = {
    "personalizacao": r'bordad|silk|dtf|arte|personaliz|estampa|etiqueta|modelagem',
    "cores": r'cor|cores|branco|preto|cinza|marinho|royal|vermelho|rosa|tingimento|paleta',
    "tamanhos": r'tamanho|grade|pp|gg|infantil|plus|g1|g2|medidas',
    "sustentabilidade": r'sustent|recic|algodao|org[aâ]nico|rpet|qu[ií]mic|vegano|trabalho|ambient',
    "catalogo": r'camiseta|polo|moletom|cal[çc]a|vestido|uniforme|produto|linha',
    "tecidos": r'tecido|algodao|linho|viscose|dry fit|moletom|jeans|malha|suplex|alfaiataria',
    "prazo": r'prazo|dias|tempo|produção|producao|pedido',
    "prazo_combinado": r'prazo|dias|pe[çc]as|úteis|uteis|lote',
    "preco_combinado": r'pre[çc]o|valor|r\$|estimativa|vendas|quantidade',
    "setor_logistica": r'frete|envio|entrega|rastreio|transportadora|pedido',
    "setor_devolucao": r'troca|devolu|pedido|pe[çc]a|an[aá]lise|defeito',
    "setor_compras": r'compras|fornecedor|fornecer|tecido|material|comercial',
    "pedido_status": r'pedido|ff-\d{4}-\d{4}|andamento|n[uú]mero|consulta',
    "pedido_alterar": r'alterar|mudar|pedido|ff-\d{4}-\d{4}|modelagem',
    "qualidade": r'qualidade|defeito|durabilidade|controle|certifica',
    "sugestao_produto": r'indico|recomendo|sugiro|para|tecido|camiseta|polo|moletom',
}

SETOR_ERRADO = {
    "personalizacao": r'frete|rastreio|transportadora|log[ií]stica',
    "cores": r'frete|rastreio|transportadora|log[ií]stica',
    "tecidos": r'frete|rastreio|transportadora|log[ií]stica',
    "setor_logistica": r'bordado|silk|dtf|tecido ideal|esporte indico',
}


def avaliar_linha(row):
    categoria = row["categoria"]
    pergunta = row["pergunta"].lower()
    intencao = row["intencao"]
    resposta = row["resposta"].lower()
    motivos = []
    nota = 2

    if PLACEHOLDER.search(resposta):
        return 0, "placeholder/lixo tecnico"
    if intencao == "fallback" and categoria != "fallback_ok":
        return 0, "fallback em pergunta real"
    if categoria in SETOR_ERRADO and re.search(SETOR_ERRADO[categoria], resposta):
        return 0, "resposta de setor claramente errado"
    if "0 peças" in resposta or "0 pecas" in resposta:
        return 0, "calculo com quantidade zero"

    esperado = EXPECTATIVAS.get(categoria)
    if esperado and not re.search(esperado, resposta):
        nota = min(nota, 1)
        motivos.append("faltou vocabulario esperado")

    if row["status"] == "MISMATCH":
        nota = min(nota, 1)
        motivos.append("intencao vizinha/mismatch")

    if re.search(r'pedido|defeito|troca|devolu|atras|rastreio|frete|pre[çc]o|or[çc]amento', pergunta):
        if not re.search(r'pedido|ff-\d{4}-\d{4}|me diga|me informe|vendas|foto|pr[oó]ximo|quantidade|produto', resposta):
            nota = min(nota, 1)
            motivos.append("sem proximo passo claro")

    if not motivos:
        motivos.append("boa")
    return nota, "; ".join(motivos)


def main():
    with open(RESULTADOS, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    avaliadas = []
    cont = Counter()
    por_cat = defaultdict(Counter)
    for row in rows:
        nota, motivo = avaliar_linha(row)
        label = {2: "boa", 1: "aceitavel", 0: "ruim"}[nota]
        row = dict(row)
        row["nota_qualidade"] = nota
        row["qualidade"] = label
        row["motivo_qualidade"] = motivo
        avaliadas.append(row)
        cont[label] += 1
        por_cat[row["categoria"]][label] += 1

    campos = list(avaliadas[0].keys())
    with open(SAIDA, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(avaliadas)

    total = len(avaliadas)
    print("=" * 72)
    print("  QUALIDADE PERCEBIDA DAS RESPOSTAS")
    print("=" * 72)
    for label in ("boa", "aceitavel", "ruim"):
        print(f"  {label:<10}: {cont[label]:4d} ({100*cont[label]/total:.1f}%)")
    print("\nCategorias com mais respostas ruins:")
    ruins = sorted(((c, v["ruim"], sum(v.values())) for c, v in por_cat.items()), key=lambda x: -x[1])
    for cat, qtd, total_cat in ruins[:12]:
        if qtd:
            print(f"  {qtd:2d}/{total_cat:<3d} {cat}")
    print(f"\nArquivo: {SAIDA}")


if __name__ == "__main__":
    main()
