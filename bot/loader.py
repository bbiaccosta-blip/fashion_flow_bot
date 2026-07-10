import pandas as pd
from pathlib import Path

# Caminho para a pasta data/ a partir de qualquer lugar que o bot seja executado
DATA_DIR = Path(__file__).parent.parent / "data"

def carregar_dados():
    """
    Lê todos os CSVs da pasta data/ e retorna um dicionário
    onde cada chave é o nome da tabela e o valor é o DataFrame.
    """
    tabelas = {
        "intencoes":                    "intencoes.csv",
        "produtos":                     "produtos.csv",
        "slots":                        "slots.csv",
        "prazo":                        "lookup_prazo.csv",
        "preco":                        "lookup_preco.csv",
        "compat_tecido_produto":        "lookup_compat_tecido_produto.csv",
        "compat_tecido_personalizacao": "lookup_compat_tecido_personalizacao.csv",
        "cor_tecido":                   "lookup_cor_tecido.csv",
        "tamanho_produto":              "lookup_tamanho_produto.csv",
        "gramatura":                    "lookup_gramatura.csv",
        "etapas":                       "lookup_etapas.csv",
        "capacidade_produtiva":         "lookup_capacidade_produtiva.csv",
        "consumo_tecido":               "lookup_consumo_tecido.csv",
        "estoque_materiais":            "lookup_estoque_materiais.csv",
    }

    dados = {}
    for nome, arquivo in tabelas.items():
        caminho = DATA_DIR / arquivo
        dados[nome] = pd.read_csv(caminho)

    return dados
