"""
gerenciar_intencoes.py — Ferramenta de DEV para o CRUD da Base de Conhecimento.

⚠️  ATENÇÃO: isto é para os DESENVOLVEDORES, NÃO para o usuário do bot.
    O bot (main.py) só LÊ as intenções. Quem cria, atualiza e remove intenções
    somos nós, os devs, por aqui. (Deixar o cliente final editar a base de
    conhecimento pelo chat seria um risco de segurança — qualquer um poderia
    apagar ou alterar as respostas do bot.)

É a "Base Dinâmica CRUD" da Semana 4 do professor, aplicada à MATRIZ DE
CONHECIMENTO (data/intencoes.csv): cada linha é uma intenção com suas
palavras-chave, a resposta e o PESO (prioridade no desempate).

Execute:  python gerenciar_intencoes.py
"""
import csv
import pandas as pd
from pathlib import Path

CAMINHO = Path(__file__).parent / "data" / "intencoes.csv"

# Ordem oficial das colunas da base de conhecimento.
COLUNAS = [
    "id_intencao", "palavras_chave", "tipo_resposta",
    "resposta_padrao", "pergunta_followup", "peso",
]


# ───────────────────────────── persistência ─────────────────────────────
def carregar():
    """Lê o intencoes.csv inteiro (a matriz de conhecimento)."""
    return pd.read_csv(CAMINHO, dtype=str).fillna("")


def salvar(df):
    """
    Grava a matriz de volta no arquivo. Usamos QUOTE_ALL pra manter o estilo
    do CSV (todos os campos entre aspas), igual o bot já espera.
    """
    df.to_csv(CAMINHO, index=False, quoting=csv.QUOTE_ALL)


def _existe(df, id_intencao):
    return (df["id_intencao"] == id_intencao).any()


# ─────────────────────────────── READ ───────────────────────────────────
def listar(filtro=""):
    """
    READ — lê a base e devolve as intenções (opcionalmente filtrando por um
    texto no id ou nas palavras-chave). É o que o bot faz internamente ao
    classificar, mas aqui é pra o dev inspecionar.
    """
    df = carregar()
    if filtro:
        f = filtro.lower()
        df = df[df["id_intencao"].str.lower().str.contains(f)
                | df["palavras_chave"].str.lower().str.contains(f)]
    return df[["id_intencao", "tipo_resposta", "peso", "palavras_chave"]]


# ─────────────────────────────── CREATE ─────────────────────────────────
def criar(id_intencao, palavras_chave, resposta, tipo="direta",
          followup="", peso=6):
    """
    CREATE — adiciona uma intenção NOVA na base (ex: cadastrar 'frete').
    Pseudocódigo (Semana 4): RECEBER dados -> SE já existe: erro
                             -> SENÃO: INSERIR linha -> SALVAR TABELA.
    """
    df = carregar()
    if _existe(df, id_intencao):
        return {"sucesso": False,
                "mensagem": f"Já existe uma intenção '{id_intencao}'. Use atualizar()."}

    nova = {
        "id_intencao": id_intencao,
        "palavras_chave": palavras_chave,
        "tipo_resposta": tipo,
        "resposta_padrao": resposta,
        "pergunta_followup": followup,
        "peso": str(peso),
    }
    df.loc[len(df)] = [nova[c] for c in COLUNAS]
    salvar(df)
    return {"sucesso": True,
            "mensagem": f"Intenção '{id_intencao}' criada (peso {peso})."}


# ─────────────────────────────── UPDATE ─────────────────────────────────
def atualizar(id_intencao, campo, novo_valor):
    """
    UPDATE — altera um campo de uma intenção existente (ex: mudar a resposta,
    ou o peso). Pseudocódigo: BUSCAR -> SE existe: muda campo -> SALVAR TABELA.
    """
    if campo not in COLUNAS or campo == "id_intencao":
        return {"sucesso": False,
                "mensagem": f"Campo inválido. Posso alterar: "
                            + ", ".join(c for c in COLUNAS if c != "id_intencao") + "."}

    df = carregar()
    if not _existe(df, id_intencao):
        return {"sucesso": False,
                "mensagem": f"Não encontrei a intenção '{id_intencao}'."}

    i = df.index[df["id_intencao"] == id_intencao][0]
    antigo = df.loc[i, campo]
    df.loc[i, campo] = str(novo_valor)
    salvar(df)
    return {"sucesso": True,
            "mensagem": f"'{id_intencao}': {campo} mudou de '{antigo}' para '{novo_valor}'."}


# ─────────────────────────────── DELETE ─────────────────────────────────
def deletar(id_intencao):
    """
    DELETE — remove uma intenção da base (ex: tirar a 'promo' que acabou).
    Aqui é DELETE de verdade (remove a linha), pois é o dev quem decide —
    diferente do soft delete dos pedidos, que é dado do cliente.
    """
    df = carregar()
    if not _existe(df, id_intencao):
        return {"sucesso": False,
                "mensagem": f"Não encontrei a intenção '{id_intencao}'."}

    df = df[df["id_intencao"] != id_intencao]
    salvar(df)
    return {"sucesso": True,
            "mensagem": f"Intenção '{id_intencao}' removida da base."}


# ─────────────────────────── menu interativo ────────────────────────────
def menu():
    """Loop simples pro dev usar o CRUD no terminal."""
    print("=" * 60)
    print("  Base de Conhecimento — CRUD de Intenções (ferramenta DEV)")
    print("=" * 60)
    while True:
        print("\n1) Listar   2) Criar   3) Atualizar   4) Deletar   5) Sair")
        op = input("Opção: ").strip()

        if op == "1":
            filtro = input("Filtro (enter = todas): ").strip()
            print(listar(filtro).to_string(index=False))

        elif op == "2":
            id_int = input("id da intenção (ex: frete): ").strip()
            palavras = input("palavras-chave (separadas por |): ").strip()
            resposta = input("resposta do bot: ").strip()
            peso = input("peso (enter = 6): ").strip() or "6"
            print(criar(id_int, palavras, resposta, peso=int(peso))["mensagem"])

        elif op == "3":
            id_int = input("id da intenção: ").strip()
            campo = input("campo (resposta_padrao / peso / palavras_chave...): ").strip()
            valor = input("novo valor: ").strip()
            print(atualizar(id_int, campo, valor)["mensagem"])

        elif op == "4":
            id_int = input("id da intenção a remover: ").strip()
            print(deletar(id_int)["mensagem"])

        elif op in ("5", "sair"):
            print("Até logo!")
            break

        else:
            print("Opção inválida.")


if __name__ == "__main__":
    menu()
