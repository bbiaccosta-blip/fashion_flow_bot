"""
normalizar.py — Função ÚNICA de normalização de texto.

Usada por vários módulos (classifier, extractor, contexto, responder, seguranca).
Deixa o texto "comparável": tudo em minúsculo e SEM acento, pra que "Olá" e
"ola" sejam tratados como iguais na hora de procurar palavras-chave.

Antes essa mesma função estava copiada em 5 arquivos; agora mora só aqui.
"""
import re
import unicodedata


# Typos fonéticos frequentes (identificados no stress test). Substituição
# palavra-por-palavra (\b) pra a keyword certa ser encontrada nas etapas
# seguintes. Só entram formas SEM ambiguidade — nada que possa colidir com
# palavra real do domínio.
TYPOS_FONETICOS = {
    # Typos fonéticos identificados no stress test.
    r"prasus?": "prazo",
    r"tesidos?": "tecido",
    r"vestdos?": "vestido",
    r"calsas?": "calca",
    r"estanpas?": "estampa",
    r"konprar": "comprar",
    r"konpra": "compra",
    r"kueros?": "quero",
    r"keria": "queria",
    r"kanto": "quanto",
    # Abreviações e gírias frequentes em WhatsApp (identificadas no stress
    # cliente-real). Traduzir aqui evita ter que espalhar keyword em cada
    # intenção do CSV.
    r"blza|blz": "beleza",
    r"vlws?": "valeu",
    r"pfvr?|pfv": "por favor",
    r"vc": "voce",
    r"vcs": "voces",
    r"tb|tbm": "tambem",
    r"tmj": "estamos juntos",
    r"eae|iae": "e ai",
    r"\boq\b": "o que",
    r"\bpq\b": "por que",
    r"\bcmg\b": "comigo",
    r"\bhj\b": "hoje",
    r"\bagr\b": "agora",
    r"\bmsm\b": "mesmo",
    r"\bmn\b": "manda",
    r"bora": "vamos",
    r"manero|maneiro": "legal",
    # Gírias de fechamento (importante pra "bora fechar", "fecha ai")
    r"fecha ai": "fechar pedido",
}
# (?:...) agrupa a alternância: sem isso, "\btb|tbm\b" aplicaria o \b só na
# primeira/última alternativa e "tbm" virava "tambemm" (casava \btb e sobrava o m).
_RE_TYPOS = [(re.compile(rf"\b(?:{p})\b"), v) for p, v in TYPOS_FONETICOS.items()]


def normalizar(texto):
    """
    Passa o texto pra minúsculo e remove os acentos. Ex: "Coração" -> "coracao".
    Também corrige typos fonéticos frequentes (kero→quero, calsa→calca, etc.).
    """
    texto = texto.lower()
    # NFD separa a letra do acento (ex: 'á' vira 'a' + '´'); aí descartamos os
    # acentos (categoria 'Mn' = "mark, nonspacing", ou seja, sinal sobre a letra).
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    for rx, repl in _RE_TYPOS:
        texto = rx.sub(repl, texto)
    return texto
