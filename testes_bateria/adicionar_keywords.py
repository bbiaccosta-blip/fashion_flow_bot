# -*- coding: utf-8 -*-
"""
adicionar_keywords.py — Adiciona palavras-chave comuns (achadas na bateria) a
intenções existentes do intencoes.csv. Idempotente: só adiciona o que ainda não
existe. Preserva o formato EXATO do CSV (QUOTE_ALL + LF) — só as linhas alteradas
mudam no diff.
"""
import csv
import sys
sys.path.insert(0, "/Users/marciabeatriz/Documents/Faculdade/fashion_flow_bot")
from bot.normalizar import normalizar

CSV = "/Users/marciabeatriz/Documents/Faculdade/fashion_flow_bot/data/intencoes.csv"

# id_intencao -> novas palavras-chave (frases comuns que caíam em fallback)
ADICOES = {
    "saudacao": ["opa", "salve", "hey"],
    "qualidade_durabilidade": ["dura muito", "dura bastante", "dura por quanto tempo"],
    "qualidade_controle": ["verificam as pecas", "verificam a peca", "conferem as pecas"],
    "qualidade_defeito": ["chegou com problema", "chegou com defeito", "veio com problema"],
    "personalizacao": ["personalizar", "customizar", "tipos de estampa"],
    "personalizacao_prazo": ["demora pra personalizar", "demora pra estampar",
                             "quanto tempo pra personalizar", "prazo pra estampar",
                             "prazo pra personalizar"],
    "personalizacao_envio_arte": ["png", "cdr", "pdf", "mandar arquivo",
                                  "mando o arquivo", "aceita arquivo"],
    "cores_sob_demanda": ["tingem", "tinge"],
    "qtd_grande_volume": ["alto volume"],
    "sustent_quimicos": ["tinta toxica", "tinta faz mal", "faz mal a saude"],
    "manutencao": ["como cuido", "cuido da peca", "cuidar da peca"],
    "manut_ferro": ["temperatura", "temperatura do ferro"],
    "prazo_urgente": ["urgencia", "tenho urgencia"],
    "atendente_humano": ["com uma pessoa", "pra uma pessoa", "falar com uma pessoa",
                         "pessoa de verdade"],
    "horario_atendimento": ["que horas"],
    "setor_vendas": ["quanto sai", "quanto cobram", "quanto voces cobram"],
    "setor_devolucao": ["devolvo", "dinheiro de volta", "reembolso"],
    "sugestao_produto": ["o que voce indica", "me indica", "indica um produto",
                        "sugere uma peca"],
    "sug_inverno": ["quentinho", "epoca fria", "algo quente"],
    "sug_verao": ["fresquinho", "algo fresco", "algo leve", "leve e fresco"],
    "disponibilidade_materiais": ["material disponivel", "tem material"],
}

with open(CSV, encoding="utf-8", newline="") as f:
    rows = list(csv.reader(f))

header, dados = rows[0], rows[1:]
i_id = header.index("id_intencao")
i_kw = header.index("palavras_chave")

total_add = 0
for row in dados:
    novas = ADICOES.get(row[i_id])
    if not novas:
        continue
    atuais = row[i_kw].split("|")
    atuais_norm = {normalizar(k.strip()) for k in atuais}
    add = [k for k in novas if normalizar(k) not in atuais_norm]
    if add:
        row[i_kw] = row[i_kw] + "|" + "|".join(add)
        total_add += len(add)
        print(f"  {row[i_id]:28} +{len(add)}: {', '.join(add)}")

with open(CSV, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(header)
    w.writerows(dados)

print(f"\nTotal: {total_add} palavras-chave adicionadas em {len(ADICOES)} intenções.")
