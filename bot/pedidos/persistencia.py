"""
persistencia.py — Camada de acesso ao arquivo data/pedidos.csv.

Este é o ÚNICO arquivo que lê e escreve o pedidos.csv. Os quatro arquivos de
CRUD (criar, consultar, atualizar, cancelar) chamam as funções daqui para nunca
duplicarem a lógica de abrir/salvar o arquivo. Isso é o padrão "repositório".

Detalhe importante (o "de forma real" que o professor pediu): toda função aqui
lê do disco na hora e grava no disco na hora. Não guardamos o pedido só na
memória — a alteração vai pro arquivo CSV imediatamente.
"""
import pandas as pd
from pathlib import Path
from datetime import date

from bot.normalizar import normalizar

# Caminho do data/pedidos.csv a partir de bot/pedidos/persistencia.py
# (sobe 3 níveis: persistencia.py -> pedidos -> bot -> raiz do projeto)
CAMINHO_CSV = Path(__file__).resolve().parent.parent.parent / "data" / "pedidos.csv"

# Caminho da tabela de ETAPAS (referência: quais etapas existem e se pode alterar).
CAMINHO_ETAPAS = Path(__file__).resolve().parent.parent.parent / "data" / "lookup_etapas.csv"

# Ordem oficial das colunas. Usada ao criar uma linha nova, pra garantir que os
# valores entrem na ordem certa.
COLUNAS = [
    "numero_pedido", "item", "data_criacao", "cliente", "produto", "quantidade",
    "cor", "tamanho", "tecido", "personalizacao", "etapa_atual", "status",
    "data_prevista", "observacao",
]


def carregar():
    """
    Lê o pedidos.csv inteiro e devolve um DataFrame do pandas.

    Lemos tudo como texto (dtype=str) pra evitar que o pandas transforme, por
    exemplo, a quantidade '150' em 150.0 (float). O .fillna('') troca células
    vazias por string vazia, evitando 'NaN' nas respostas.
    """
    df = pd.read_csv(CAMINHO_CSV, dtype=str).fillna("")
    return df


def carregar_etapas():
    """
    Lê a tabela de ETAPAS (lookup_etapas.csv): quais etapas existem, em ordem, e
    se cada uma permite alteração (coluna pode_alterar). É uma tabela de
    referência — o consultar.py e o atualizar.py usam isto em vez de cada um
    abrir o arquivo por conta própria.
    """
    return pd.read_csv(CAMINHO_ETAPAS).fillna("")


def salvar(df):
    """
    Grava o DataFrame de volta no pedidos.csv (sobrescreve o arquivo).
    É AQUI que a alteração vira permanente no disco.
    """
    df.to_csv(CAMINHO_CSV, index=False)


def buscar_por_id(numero):
    """
    Procura um pedido pelo ID (ex: 'FF-2026-0001').

    Devolve uma tripla: (df, indice, linha)
        - achou      → (df, índice_da_linha, dict_com_os_dados)
        - não achou  → (df, None, None)

    Devolvemos o df junto para quem chamou poder alterar e salvar sem ter que
    ler o arquivo de novo.
    """
    df = carregar()
    numero = (numero or "").strip().upper()
    indices = df.index[df["numero_pedido"].str.upper() == numero].tolist()
    if not indices:
        return df, None, None
    i = indices[0]
    return df, i, df.loc[i].to_dict()


def buscar_itens_por_id(numero):
    """
    Como um pedido pode ter VÁRIOS itens (várias linhas com o mesmo numero_pedido),
    devolve TODOS os itens: (df, [índices], [dicts das linhas]) — ordenados por item.
    Vazio se não achar.
    """
    df = carregar()
    numero = (numero or "").strip().upper()
    indices = df.index[df["numero_pedido"].str.upper() == numero].tolist()
    indices.sort(key=lambda i: str(df.loc[i].get("item", "")))
    linhas = [df.loc[i].to_dict() for i in indices]
    return df, indices, linhas


def gerar_id(df=None, ano=None):
    """
    Gera o próximo ID no formato FF-AAAA-NNNN, sequencial por ano.

    Pega o maior NNNN já usado no ano e soma 1. Se não houver nenhum pedido do
    ano, começa em 0001. Ex: se já existe FF-2026-0005, o próximo é FF-2026-0006.
    """
    if df is None:
        df = carregar()
    if ano is None:
        ano = date.today().year

    prefixo = f"FF-{ano}-"
    do_ano = df[df["numero_pedido"].str.startswith(prefixo)]
    if do_ano.empty:
        seq = 1
    else:
        # os 4 últimos caracteres são o número sequencial
        seq = do_ano["numero_pedido"].str[-4:].astype(int).max() + 1
    return f"{prefixo}{seq:04d}"


def e_dono(linha, nome_cliente):
    """
    Diz se o pedido (linha) pertence a esse cliente. Compara o campo 'cliente'
    do pedido com o nome guardado na conversa, SEM ligar pra maiúscula nem acento.

    Se nome_cliente for None (uso interno/operador ou teste), NÃO checa e devolve
    True — a trava de dono só vale quando há um nome informado.
    """
    if not nome_cliente:
        return True
    return normalizar(str(linha.get("cliente", ""))) == normalizar(str(nome_cliente))
