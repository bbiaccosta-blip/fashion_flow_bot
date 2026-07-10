# -*- coding: utf-8 -*-
"""
testar_bot.py — Roda as ~1000 perguntas de perguntas.csv pelo pipeline REAL do bot
(o mesmo do app.py) e verifica se cada uma cai numa intenção coerente.

Cada pergunta roda numa sessao ISOLADA com o nome ja definido ("Bia") — assim
o teste mede a QUALIDADE DA CLASSIFICACAO, sem contaminacao de contexto entre
perguntas nem a etapa de captura de nome.

Saidas:
  - resultados.csv   : toda pergunta com intencao + resposta
  - problemas.csv     : so as sinalizadas (fallback inesperado ou intencao fora do esperado)
  - relatorio no stdout
"""
import csv
import os
import sys
from collections import Counter, defaultdict

BOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BOT_DIR)

from bot.loader import carregar_dados
from bot.extractor import extrair_slots
from bot.classifier import classificar
from bot.responder import responder
from bot.seguranca import verificar_seguranca
from bot.contexto import (
    criar_sessao, is_despedida, is_casual,
    merge_com_contexto, atualizar_sessao_pos_turno,
)

HERE = os.path.dirname(__file__)


# ── Conjunto de intencoes ACEITAVEIS por categoria esperada ──────────
# Marcadores especiais: (despedida)/(casual)/(seguranca) sao interceptados
# antes do classifier (nao passam pelo classificar()).
MAPA = {
    "saudacao": {"saudacao", "saudacao_girias1", "saudacao_girias2"},
    "saudacao_giria": {"saudacao", "saudacao_girias1", "saudacao_girias2"},
    "despedida": {"(despedida)"},
    "agradecimento": {"(casual)", "despedida", "agradecimento_continuo"},
    "elogio": {"elogios1", "elogios2"},
    "ofensa": {"ofensas"},
    "qualidade": {"qualidade", "qualidade_originalidade", "qualidade_durabilidade",
                  "qualidade_controle", "qualidade_defeito", "qualidade_certificacoes"},
    "personalizacao": {"personalizacao", "personalizacao_tipos", "personalizacao_silkscreen",
                       "personalizacao_dtf", "personalizacao_bordado", "personalizacao_etiqueta",
                       "personalizacao_modelagem_exclusiva", "personalizacao_cores",
                       "personalizacao_tamanhos", "personalizacao_quantidade",
                       "personalizacao_prazo", "personalizacao_envio_arte",
                       "prazo_com_personalizacao", "cores_basicas"},
    "cores": {"personalizacao_cores", "cores_basicas", "cores_sob_demanda", "cores_combinacao",
              "cores_limite_tecnica", "tec_cores_estoque"},
    "tamanhos": {"personalizacao_tamanhos", "tamanhos_adulto", "tamanhos_infantil",
                 "tamanhos_plus_size", "tamanhos_tabela_medidas", "combinado_tamanho_em_produto"},
    "quantidade_minima": {"personalizacao_quantidade", "qtd_minima_personalizacao",
                          "qtd_minima_cor", "qtd_grande_volume", "qtd_pequena_volume"},
    "sustentabilidade": {"sustentabilidade", "sustent_aproveitamento", "sustent_materiais_eco",
                         "sustent_reciclagem", "sustent_quimicos", "sustent_trabalho",
                         "sustent_vegano", "sustent_logistica"},
    "manutencao": {"manutencao", "manut_lavar", "manut_ferro", "manut_secadora", "manut_alvejante",
                   "manut_mancha", "manut_por_tecido", "cuidados_algodao", "cuidados_viscose",
                   "cuidados_poliester", "cuidados_linho", "cuidados_jeans", "cuidados_la",
                   "cuidados_malha", "cuidados_moletom", "manut_encolhimento", "manut_desbotamento"},
    "producao": {"producao", "producao_etapas", "producao_onde", "producao_capacidade",
                 "producao_tecnologia", "producao_equipe", "producao_modelagem",
                 "producao_corte_costura"},
    "catalogo": {"catalogo", "cat_camisetas", "cat_moletons", "cat_calcas", "cat_vestidos",
                 "cat_uniformes", "cat_infantil", "cat_nao_fazemos", "produto_detalhe"},
    "sugestao_produto": {"sugestao_produto", "sug_casual", "sug_trabalho", "sug_esporte",
                        "sug_festa", "sug_inverno", "sug_verao", "sug_uniforme", "sug_presente"},
    "tecidos": {"tecidos", "tec_disponiveis", "tec_composicao", "tec_origem", "tec_pele_sensivel",
                "tec_couro", "sug_tecido_uso", "sug_tec_quente", "sug_tec_frio", "sug_tec_diario",
                "sug_tec_esporte", "sug_tec_formal", "tec_cores_estoque"},
    "disponibilidade": {"disponibilidade_materiais", "reposicao_estoque", "pronta_entrega"},
    "prazo": {"previsao_prazo", "prazo_padrao", "prazo_com_personalizacao", "prazo_urgente",
              "prazo_grande_pedido", "prazo_atraso", "prazo_sem_contexto"},
    "prazo_combinado": {"combinado_prazo_qtd_produto", "combinado_prazo_personalizacao_produto",
                        "previsao_prazo", "prazo_padrao", "prazo_com_personalizacao"},
    "preco_combinado": {"combinado_preco_qtd_produto", "combinado_preco_personalizacao",
                        "setor_vendas"},
    "desconto": {"combinado_desconto_volume"},
    "compat_tecido_produto": {"combinado_tecido_em_produto",
                             "combinado_tecidos_disponiveis_para_produto", "tecidos",
                             "cat_camisetas", "cat_moletons", "cat_calcas", "cat_vestidos"},
    "compat_pers_tecido": {"combinado_personalizacao_em_tecido", "personalizacao_bordado",
                          "personalizacao_silkscreen"},
    "compat_cor_tecido": {"combinado_cor_em_tecido", "combinado_cores_disponiveis_para_tecido",
                         "cores_basicas", "tec_cores_estoque", "disponibilidade_materiais"},
    "compat_tamanho_produto": {"combinado_tamanho_em_produto", "tamanhos_plus_size"},
    "gramatura": {"combinado_gramatura_produto_uso", "tecidos"},
    "viabilidade": {"viabilidade_producao"},
    "consumo": {"consumo_tecido"},
    "pedido_status": {"status_pedido", "etapas_pedido", "etapa_consulta", "acompanhamento"},
    "pedido_alterar": {"alterar_pedido", "alterar_pedido_especifico"},
    "pedido_cancelar": {"cancelar_pedido"},
    "pedido_registrar": {"registrar_pedido"},
    "b2b": {"atende_empresa", "private_label", "revenda", "uniforme_escolar",
            "combinado_b2b_uniforme_completo", "cat_uniformes"},
    "bot_meta": {"sobre_o_bot", "atendente_humano", "horario_atendimento"},
    "setor_vendas": {"setor_vendas", "combinado_preco_qtd_produto", "combinado_preco_personalizacao"},
    "setor_logistica": {"setor_logistica"},
    "setor_devolucao": {"setor_devolucao"},
    "setor_compras": {"setor_compras"},
    "setor_almoxarifado": {"setor_almoxarifado", "disponibilidade_materiais"},
    # especiais (avaliadas por regra propria abaixo)
    "fallback_ok": {"fallback"},
    "saudacao_composta": set(),  # passa desde que nao seja fallback
}


def responder_uma(dados, pergunta):
    """Roda UMA pergunta pelo mesmo fluxo do app.py, em sessao isolada."""
    sessao = criar_sessao()
    sessao["nome_cliente"] = "Bia"   # pula a captura de nome
    sessao["ativa"] = True

    bloqueio = verificar_seguranca(pergunta)
    if bloqueio:
        return "(seguranca)", bloqueio

    if is_despedida(pergunta):
        return "(despedida)", "Até logo! Se precisar, é só voltar."

    if is_casual(pergunta):
        return "(casual)", "Beleza, pode continuar!"

    slots_turno = extrair_slots(pergunta, em_menu=False)
    slots_efetivos = merge_com_contexto(slots_turno, sessao, pergunta)
    intencao = classificar(pergunta, slots_turno, slots_efetivos, dados["intencoes"], sessao)
    resposta = responder(intencao, slots_efetivos, dados, sessao, pergunta)
    return intencao, resposta


def avaliar(categoria, intencao):
    """Retorna (status, motivo). status in {OK, FALLBACK, MISMATCH, SPURIOUS}."""
    aceitos = MAPA.get(categoria, set())

    if categoria == "saudacao_composta":
        return ("FALLBACK", "saudacao+pergunta caiu em fallback") if intencao == "fallback" else ("OK", "")

    if categoria == "fallback_ok":
        if intencao == "fallback":
            return ("OK", "")
        return ("SPURIOUS", f"gibberish/fora casou com '{intencao}'")

    if intencao in aceitos:
        return ("OK", "")
    if intencao == "fallback":
        return ("FALLBACK", "esperava resposta, caiu em fallback")
    return ("MISMATCH", f"esperava {categoria}, classificou '{intencao}'")


def main():
    dados = carregar_dados()

    with open(os.path.join(HERE, "perguntas.csv"), encoding="utf-8") as f:
        perguntas = list(csv.DictReader(f))

    resultados = []
    for row in perguntas:
        cat, perg = row["categoria"], row["pergunta"]
        intencao, resposta = responder_uma(dados, perg)
        status, motivo = avaliar(cat, intencao)
        resultados.append({
            "categoria": cat, "pergunta": perg, "intencao": intencao,
            "status": status, "motivo": motivo,
            "resposta": resposta.replace("\n", " ⏎ "),
        })

    # ── grava CSVs ────────────────────────────────────────────────
    campos = ["categoria", "pergunta", "intencao", "status", "motivo", "resposta"]
    with open(os.path.join(HERE, "resultados.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(resultados)

    problemas = [r for r in resultados if r["status"] in ("FALLBACK", "MISMATCH")]
    with open(os.path.join(HERE, "problemas.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(problemas)

    # ── relatorio ─────────────────────────────────────────────────
    total = len(resultados)
    cont = Counter(r["status"] for r in resultados)
    ok = cont["OK"]
    print("=" * 64)
    print(f"  BATERIA DE {total} PERGUNTAS — Fashion Flow Bot")
    print("=" * 64)
    print(f"  OK        : {cont['OK']:4d}  ({100*cont['OK']/total:.1f}%)")
    print(f"  FALLBACK  : {cont['FALLBACK']:4d}  (esperava resposta, nao entendeu)")
    print(f"  MISMATCH  : {cont['MISMATCH']:4d}  (classificou em intencao errada)")
    print(f"  SPURIOUS  : {cont['SPURIOUS']:4d}  (gibberish casou com intencao real)")
    print(f"  -> coerentes (OK+SPURIOUS toleravel): "
          f"{100*(cont['OK'])/total:.1f}% estrito\n")

    # problemas por categoria
    prob_por_cat = defaultdict(lambda: [0, 0])  # [n_problemas, n_total]
    for r in resultados:
        prob_por_cat[r["categoria"]][1] += 1
        if r["status"] in ("FALLBACK", "MISMATCH"):
            prob_por_cat[r["categoria"]][0] += 1
    print("PROBLEMAS POR CATEGORIA (so as que tem >0):")
    for cat, (np_, nt) in sorted(prob_por_cat.items(), key=lambda x: -x[1][0]):
        if np_:
            print(f"  {np_:3d}/{nt:<3d}  {cat}")

    # amostra de problemas
    print("\n" + "=" * 64)
    print("  AMOSTRA DE PROBLEMAS (ate 60)")
    print("=" * 64)
    for r in problemas[:60]:
        print(f"[{r['status']:8}] ({r['categoria']}) {r['pergunta']!r}")
        print(f"           -> {r['intencao']}  | {r['motivo']}")

    print(f"\nArquivos: resultados.csv ({total}), problemas.csv ({len(problemas)})")


if __name__ == "__main__":
    main()
