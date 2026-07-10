"""
test_crud.py — Testes EXTENSIVOS do CRUD.

Cobre:
  - o CRUD de PEDIDOS  (bot/pedidos/: criar, consultar, atualizar, cancelar + persistencia)
  - o CRUD de INTENÇÕES (gerenciar_intencoes.py — a ferramenta de dev)

Cada teste cobre caminho feliz, erros e casos de borda.

⚠️ Segurança dos dados: os testes rodam em CÓPIAS TEMPORÁRIAS dos CSVs (criadas
   numa pasta temp). Os arquivos reais (data/pedidos.csv, data/intencoes.csv)
   NÃO são tocados. Por isso "apontamos" o caminho do persistencia/gi para a cópia
   no setUp e devolvemos no tearDown.

Execute:  python -m unittest test_crud -v
      ou:  python test_crud.py
"""
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from bot.pedidos import persistencia, criar, consultar, atualizar, cancelar
import gerenciar_intencoes as gi

DATA = Path(__file__).parent / "data"

# Usamos o ano de HOJE pra montar os IDs do seed, assim o gerar_id (que usa o ano
# atual) fica previsível independente do ano em que o teste rodar.
ANO = date.today().year


def pid(n):
    """Monta um número de pedido do ano corrente. Ex: pid(1) -> 'FF-2026-0001'."""
    return f"FF-{ANO}-{n:04d}"


# Quatro pedidos-semente cobrindo TODOS os estados que o CRUD precisa enxergar:
#   0001 modelagem/em_producao  -> alterável, cancelável, pode avançar
#   0002 corte/em_producao      -> alteração BLOQUEADA (passou da modelagem)
#   0003 embalagem/concluido    -> não cancela (já concluído)
#   0004 modelagem/cancelado    -> já cancelado
SEED_PEDIDOS = (
    "numero_pedido,item,data_criacao,cliente,produto,quantidade,cor,tamanho,tecido,"
    "personalizacao,etapa_atual,status,data_prevista,observacao\n"
    f"{pid(1)},1,{ANO}-06-01,Maria Silva,camiseta_basica,100,preto,M,algodao_pima,bordado,"
    f"modelagem,em_producao,{ANO}-07-01,alteravel\n"
    f"{pid(2)},1,{ANO}-06-01,Joao Souza,polo,200,branco,G,algodao_penteado,silkscreen,"
    f"corte,em_producao,{ANO}-07-02,no corte\n"
    f"{pid(3)},1,{ANO}-05-01,Ana Costa,legging,50,preto,M,suplex,dtf,"
    f"embalagem_expedicao,concluido,{ANO}-06-01,pronto\n"
    f"{pid(4)},1,{ANO}-06-01,Carlos Lima,moletom,80,marinho,GG,moletom_flanelado,nenhuma,"
    f"modelagem,cancelado,{ANO}-07-10,cancelado antes\n"
)


# ════════════════════════════ CRUD DE PEDIDOS ════════════════════════════
class TestCrudPedidos(unittest.TestCase):

    def setUp(self):
        # cria uma pasta temporária e um pedidos.csv só pra este teste
        self.tmp = Path(tempfile.mkdtemp())
        self.csv = self.tmp / "pedidos.csv"
        self.csv.write_text(SEED_PEDIDOS, encoding="utf-8")
        # redireciona o persistencia pra cópia temporária (etapas continua real)
        self._orig = persistencia.CAMINHO_CSV
        persistencia.CAMINHO_CSV = self.csv

    def tearDown(self):
        persistencia.CAMINHO_CSV = self._orig
        shutil.rmtree(self.tmp)

    # ---------- persistência ----------
    def test_gerar_id_sequencial(self):
        # maior do ano é 0004 -> próximo é 0005
        self.assertEqual(persistencia.gerar_id(ano=ANO), pid(5))

    def test_gerar_id_ano_sem_pedidos(self):
        # nenhum pedido de 1999 -> começa em 0001
        self.assertEqual(persistencia.gerar_id(ano=1999), "FF-1999-0001")

    def test_buscar_por_id_encontra(self):
        _, i, linha = persistencia.buscar_por_id(pid(1))
        self.assertIsNotNone(i)
        self.assertEqual(linha["produto"], "camiseta_basica")

    def test_buscar_por_id_nao_encontra(self):
        _, i, linha = persistencia.buscar_por_id("FF-2099-9999")
        self.assertIsNone(i)
        self.assertIsNone(linha)

    def test_buscar_por_id_ignora_maiuscula(self):
        _, i, _ = persistencia.buscar_por_id(pid(1).lower())
        self.assertIsNotNone(i)

    # ---------- CREATE ----------
    def test_criar_sucesso(self):
        dados = {"produto": "camiseta_basica", "quantidade": 100, "cor": "branco",
                 "tamanho": "G", "tecido": "algodao_pima", "personalizacao": "bordado"}
        r = criar.registrar_pedido(dados)
        self.assertTrue(r["sucesso"])
        self.assertEqual(r["pedido"]["numero_pedido"], pid(5))      # ID gerado
        self.assertEqual(r["pedido"]["etapa_atual"], "modelagem")   # nasce na modelagem
        self.assertEqual(r["pedido"]["status"], "em_producao")
        # gravou MESMO no arquivo? relê do disco e confere
        self.assertEqual(len(persistencia.carregar()), 5)

    def test_criar_falta_campo(self):
        dados = {"produto": "polo", "quantidade": 50}  # faltam cor, tamanho, tecido...
        r = criar.registrar_pedido(dados)
        self.assertFalse(r["sucesso"])
        self.assertIn("faltam", r["mensagem"].lower())
        self.assertEqual(len(persistencia.carregar()), 4)  # nada foi gravado

    def test_criar_dois_gera_ids_diferentes(self):
        base = {"produto": "polo", "quantidade": 10, "cor": "preto",
                "tamanho": "M", "tecido": "algodao_basico", "personalizacao": "nenhuma"}
        r1 = criar.registrar_pedido(dict(base))
        r2 = criar.registrar_pedido(dict(base))
        self.assertEqual(r1["pedido"]["numero_pedido"], pid(5))
        self.assertEqual(r2["pedido"]["numero_pedido"], pid(6))

    # ---------- READ ----------
    def test_consultar_existente(self):
        r = consultar.consultar_pedido(pid(1))
        self.assertTrue(r["sucesso"])
        self.assertIn("camiseta basica", r["mensagem"])
        self.assertIn("modelagem", r["mensagem"])

    def test_consultar_inexistente(self):
        r = consultar.consultar_pedido("FF-2099-9999")
        self.assertFalse(r["sucesso"])
        self.assertIn("não encontrei", r["mensagem"].lower())

    def test_consultar_cancelado_nao_diz_alteravel(self):
        r = consultar.consultar_pedido(pid(4))
        self.assertIn("CANCELADO", r["mensagem"])
        # bug que corrigimos: cancelado NÃO pode dizer "ainda dá pra alterar"
        self.assertNotIn("ainda dá pra alterar", r["mensagem"].lower())

    def test_consultar_concluido(self):
        r = consultar.consultar_pedido(pid(3))
        self.assertIn("CONCLUÍDO", r["mensagem"])

    # ---------- UPDATE: alterar_campo ----------
    def test_alterar_permitido_na_modelagem(self):
        r = atualizar.alterar_campo(pid(1), "cor", "vermelho")
        self.assertTrue(r["sucesso"])
        # conferindo a persistência real
        _, _, linha = persistencia.buscar_por_id(pid(1))
        self.assertEqual(linha["cor"], "vermelho")

    def test_alterar_bloqueado_apos_modelagem(self):
        r = atualizar.alterar_campo(pid(2), "cor", "preto")  # está no corte
        self.assertFalse(r["sucesso"])
        self.assertIn("modelagem", r["mensagem"].lower())
        # não mudou nada
        _, _, linha = persistencia.buscar_por_id(pid(2))
        self.assertEqual(linha["cor"], "branco")

    def test_alterar_pedido_cancelado(self):
        r = atualizar.alterar_campo(pid(4), "cor", "preto")
        self.assertFalse(r["sucesso"])
        self.assertIn("cancelado", r["mensagem"].lower())

    def test_alterar_campo_invalido(self):
        # 'produto' não está na lista de campos alteráveis
        r = atualizar.alterar_campo(pid(1), "produto", "polo")
        self.assertFalse(r["sucesso"])

    def test_alterar_inexistente(self):
        r = atualizar.alterar_campo("FF-2099-9999", "cor", "preto")
        self.assertFalse(r["sucesso"])

    # ---------- UPDATE: avancar_etapa ----------
    def test_avancar_um_passo(self):
        r = atualizar.avancar_etapa(pid(1))  # modelagem -> corte
        self.assertTrue(r["sucesso"])
        self.assertEqual(r["pedido"]["etapa_atual"], "corte")

    def test_avancar_ate_concluir(self):
        # avança várias vezes; ao passar da última etapa, vira 'concluido'
        r = None
        for _ in range(10):
            r = atualizar.avancar_etapa(pid(1))
            if r["pedido"]["status"] == "concluido":
                break
        self.assertEqual(r["pedido"]["status"], "concluido")

    def test_avancar_inexistente(self):
        r = atualizar.avancar_etapa("FF-2099-9999")
        self.assertFalse(r["sucesso"])

    def test_avancar_pedido_cancelado_recusa(self):
        # pedido 0004 está cancelado -> avançar deve recusar (trava nova)
        r = atualizar.avancar_etapa(pid(4))
        self.assertFalse(r["sucesso"])
        self.assertIn("cancelado", r["mensagem"].lower())

    # ---------- DELETE: cancelar (soft delete) ----------
    def test_cancelar_sucesso(self):
        r = cancelar.cancelar_pedido(pid(1))
        self.assertTrue(r["sucesso"])
        # soft delete: a linha CONTINUA no arquivo, só com status 'cancelado'
        _, _, linha = persistencia.buscar_por_id(pid(1))
        self.assertEqual(linha["status"], "cancelado")
        self.assertEqual(len(persistencia.carregar()), 4)  # nada foi apagado

    def test_cancelar_ja_cancelado(self):
        r = cancelar.cancelar_pedido(pid(4))
        self.assertFalse(r["sucesso"])
        self.assertIn("já estava cancelado", r["mensagem"].lower())

    def test_cancelar_concluido_recusa(self):
        r = cancelar.cancelar_pedido(pid(3))
        self.assertFalse(r["sucesso"])
        self.assertIn("concluído", r["mensagem"].lower())

    def test_cancelar_inexistente(self):
        r = cancelar.cancelar_pedido("FF-2099-9999")
        self.assertFalse(r["sucesso"])

    def test_cancelar_grava_motivo(self):
        cancelar.cancelar_pedido(pid(1), motivo="cliente desistiu")
        _, _, linha = persistencia.buscar_por_id(pid(1))
        self.assertIn("cliente desistiu", linha["observacao"])

    # ---------- TRAVA DE DONO (ownership pelo nome) ----------
    def test_consultar_dono_certo(self):
        # pid(1) é da "Maria Silva" -> ela consegue ver
        r = consultar.consultar_pedido(pid(1), "Maria Silva")
        self.assertTrue(r["sucesso"])

    def test_consultar_dono_errado(self):
        r = consultar.consultar_pedido(pid(1), "Outra Pessoa")
        self.assertFalse(r["sucesso"])
        self.assertIn("não está no seu nome", r["mensagem"].lower())

    def test_dono_ignora_maiuscula_e_acento(self):
        # "maria silva" (minúsculo) bate com "Maria Silva"
        r = consultar.consultar_pedido(pid(1), "maria silva")
        self.assertTrue(r["sucesso"])

    def test_sem_nome_nao_checa_dono(self):
        # sem nome (uso interno/operador) -> a trava não se aplica
        r = consultar.consultar_pedido(pid(1))
        self.assertTrue(r["sucesso"])

    def test_alterar_dono_errado(self):
        r = atualizar.alterar_campo(pid(1), "cor", "verde", "Outra Pessoa")
        self.assertFalse(r["sucesso"])
        self.assertIn("não está no seu nome", r["mensagem"].lower())

    def test_cancelar_dono_errado(self):
        r = cancelar.cancelar_pedido(pid(1), "Outra Pessoa")
        self.assertFalse(r["sucesso"])
        self.assertIn("não está no seu nome", r["mensagem"].lower())

    def test_criar_grava_o_dono(self):
        dados = {"produto": "polo", "quantidade": 10, "cor": "preto",
                 "tamanho": "M", "tecido": "algodao_basico", "personalizacao": "nenhuma",
                 "cliente": "Fulano de Tal"}
        r = criar.registrar_pedido(dados)
        self.assertEqual(r["pedido"]["cliente"], "Fulano de Tal")

    # ---------- pedido com VÁRIOS itens (mesmo número) ----------
    def _itens_exemplo(self):
        return [
            {"produto": "camiseta_basica", "quantidade": 100, "cor": "preto",
             "tamanho": "M", "tecido": "algodao_basico", "personalizacao": "nenhuma"},
            {"produto": "polo", "quantidade": 50, "cor": "branco",
             "tamanho": "G", "tecido": "algodao_basico", "personalizacao": "bordado"},
        ]

    def test_lote_um_numero_varios_itens(self):
        r = criar.registrar_pedido_lote(self._itens_exemplo(), cliente="Bia")
        self.assertTrue(r["sucesso"])
        _, indices, linhas = persistencia.buscar_itens_por_id(r["numero"])
        self.assertEqual(len(linhas), 2)                      # 2 itens, 1 número
        self.assertEqual({l["item"] for l in linhas}, {"1", "2"})
        self.assertEqual({l["numero_pedido"] for l in linhas}, {r["numero"]})
        self.assertEqual(linhas[1]["produto"], "polo")

    def test_lote_vazio_recusa(self):
        r = criar.registrar_pedido_lote([], cliente="Bia")
        self.assertFalse(r["sucesso"])

    def test_consultar_mostra_varios_itens(self):
        r = criar.registrar_pedido_lote(self._itens_exemplo(), cliente="Bia")
        c = consultar.consultar_pedido(r["numero"], nome_cliente="Bia")
        self.assertTrue(c["sucesso"])
        self.assertEqual(len(c["itens"]), 2)
        self.assertIn("2 itens", c["mensagem"])

    def test_cancelar_multi_item_cancela_tudo(self):
        r = criar.registrar_pedido_lote(self._itens_exemplo(), cliente="Bia")
        cancelar.cancelar_pedido(r["numero"], nome_cliente="Bia")
        _, _, linhas = persistencia.buscar_itens_por_id(r["numero"])
        self.assertTrue(all(l["status"] == "cancelado" for l in linhas))


# ═══════════════════════════ CRUD DE INTENÇÕES ═══════════════════════════
class TestCrudIntencoes(unittest.TestCase):

    def setUp(self):
        # copia o intencoes.csv REAL pra uma cópia temporária e aponta o gi pra ela
        self.tmp = Path(tempfile.mkdtemp())
        self.csv = self.tmp / "intencoes.csv"
        shutil.copy(DATA / "intencoes.csv", self.csv)
        self._orig = gi.CAMINHO
        gi.CAMINHO = self.csv
        self.total = len(gi.carregar())

    def tearDown(self):
        gi.CAMINHO = self._orig
        shutil.rmtree(self.tmp)

    # ---------- CREATE ----------
    def test_criar_intencao(self):
        r = gi.criar("teste_frete", "frete|entrega", "Frete R$ 15", peso=9)
        self.assertTrue(r["sucesso"])
        df = gi.carregar()
        self.assertEqual(len(df), self.total + 1)
        self.assertTrue((df["id_intencao"] == "teste_frete").any())

    def test_criar_duplicada_recusa(self):
        r = gi.criar("saudacao", "oi", "Olá")  # já existe
        self.assertFalse(r["sucesso"])
        self.assertIn("já existe", r["mensagem"].lower())

    # ---------- READ (listar) ----------
    def test_listar_com_filtro(self):
        res = gi.listar("saudacao")
        self.assertGreaterEqual(len(res), 1)
        self.assertTrue(res["id_intencao"].str.contains("saudacao").all())

    # ---------- UPDATE ----------
    def test_atualizar_resposta(self):
        gi.criar("teste_up", "x", "antiga")
        r = gi.atualizar("teste_up", "resposta_padrao", "NOVA resposta")
        self.assertTrue(r["sucesso"])
        df = gi.carregar()
        linha = df[df["id_intencao"] == "teste_up"].iloc[0]
        self.assertEqual(linha["resposta_padrao"], "NOVA resposta")

    def test_atualizar_peso(self):
        gi.criar("teste_peso", "x", "y", peso=6)
        gi.atualizar("teste_peso", "peso", "10")
        linha = gi.carregar()
        linha = linha[linha["id_intencao"] == "teste_peso"].iloc[0]
        self.assertEqual(linha["peso"], "10")

    def test_atualizar_inexistente(self):
        r = gi.atualizar("nao_existe_xyz", "resposta_padrao", "x")
        self.assertFalse(r["sucesso"])

    def test_atualizar_campo_invalido(self):
        # não deixamos mexer no id_intencao (a "chave")
        r = gi.atualizar("saudacao", "id_intencao", "outro")
        self.assertFalse(r["sucesso"])

    # ---------- DELETE ----------
    def test_deletar_intencao(self):
        gi.criar("teste_del", "x", "y")
        r = gi.deletar("teste_del")
        self.assertTrue(r["sucesso"])
        df = gi.carregar()
        self.assertEqual(len(df), self.total)  # voltou ao tamanho original
        self.assertFalse((df["id_intencao"] == "teste_del").any())

    def test_deletar_inexistente(self):
        r = gi.deletar("nao_existe_xyz")
        self.assertFalse(r["sucesso"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
