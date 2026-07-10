"""
Filtro de Segurança — Missão 2.
Roda ANTES de tudo: se a mensagem tem dado sensível, bloqueia o turno.
"""
import re

from bot.normalizar import normalizar


PADROES_SENSIVEIS = [
    r"\bsenha\b",
    r"\bsenhas\b",
    r"\bcvv\b",
    r"\bcvc\b",
    r"\bcodigo de seguranca\b",
    r"\bnumero do cartao\b",
    r"\bnumero de cartao\b",
    # 13 a 16 dígitos seguidos = provável número de cartão
    r"\b(?:\d[ .-]?){13,16}\b",
]

RESPOSTA_BLOQUEIO = (
    "🔒 Por segurança, nunca compartilhe senha, CVV ou número de cartão "
    "aqui no chat. A FashionFlow jamais pede esses dados por mensagem. "
    "Quando for pagar, use sempre o link seguro enviado pelo setor de vendas."
)


def verificar_seguranca(mensagem):
    t = normalizar(mensagem)
    for padrao in PADROES_SENSIVEIS:
        if re.search(padrao, t):
            return RESPOSTA_BLOQUEIO   # achou dado sensível → bloqueia
    return None                        # tudo limpo → segue o pipeline