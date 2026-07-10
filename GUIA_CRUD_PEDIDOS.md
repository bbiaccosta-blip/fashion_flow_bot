# Guia do CRUD de Pedidos — Fashion Flow Bot

Este guia explica **onde** o CRUD de pedidos está no código e **como** cada
operação funciona. CRUD = as 4 operações sobre a tabela `data/pedidos.csv`:
**C**reate (registrar), **R**ead (consultar), **U**pdate (alterar / avançar
etapa) e **D**elete (cancelar — soft delete).

O CRUD é acionado por **linguagem natural** na conversa — não há botão nem
comando especial. O usuário digita e o classificador reconhece a intenção.

---

## 1. Mapa rápido: onde está cada coisa

| Operação | Frase que ativa (exemplo) | Intenção | Arquivo da lógica → função |
|---|---|---|---|
| **CREATE** | "quero fazer um pedido" | `registrar_pedido` | `bot/pedidos/criar.py` → `registrar_pedido()` |
| **READ** | "status do pedido FF-2026-0001" | `status_pedido` | `bot/pedidos/consultar.py` → `consultar_pedido()` |
| **UPDATE (campo)** | "mudar a cor do pedido X para preto" | `alterar_pedido_especifico` | `bot/pedidos/atualizar.py` → `alterar_campo()` |
| **UPDATE (etapa)** | "avançar a etapa do pedido X" | `avancar_etapa` | `bot/pedidos/atualizar.py` → `avancar_etapa()` |
| **DELETE** | "cancelar o pedido X" | `cancelar_pedido` | `bot/pedidos/cancelar.py` → `cancelar_pedido()` |

Estrutura do pacote do CRUD:

```
bot/pedidos/
├── __init__.py
├── persistencia.py   ← único que lê/grava o pedidos.csv (compartilhado)
├── criar.py          ← CREATE   registrar_pedido()
├── consultar.py      ← READ     consultar_pedido()
├── atualizar.py      ← UPDATE   alterar_campo() + avancar_etapa()
└── cancelar.py       ← DELETE   cancelar_pedido()  (soft delete)
```

E as duas tabelas CSV em `data/`:

- **`lookup_etapas.csv`** — tabela de *referência*: as 6 etapas e se cada uma
  permite alteração (`pode_alterar`). Quase nunca muda.
- **`pedidos.csv`** — tabela de *dados*: os pedidos reais. É ela que o CRUD muda.

---

## 2. Como uma mensagem vira CRUD (o caminho)

Todo turno de conversa passa por este pipeline (em `main.py` e `app.py`):

```
mensagem do usuário
  → extrair_slots()        (bot/extractor.py)   acha numero_pedido, produto, cor...
  → merge_com_contexto()   (bot/contexto.py)    junta com a memória da conversa
  → classificar()          (bot/classifier.py)  decide a intenção (qual CRUD)
  → responder()            (bot/responder.py)   executa: chama bot/pedidos/*
        → bot/pedidos/<operação>.py             a regra de negócio do CRUD
              → persistencia.py                 lê / grava o pedidos.csv
  → atualizar_sessao_pos_turno()  (contexto.py) guarda o que aconteceu
```

Dois pontos do `classifier.py` fazem o CRUD "fluir" na conversa:

- **Registro em andamento** (`bot/classifier.py`, ~linha 37): enquanto há um
  `registro_pedido` aberto na sessão, toda mensagem continua sendo
  `registrar_pedido` (para coletar os campos um a um).
- **Esperando um ID** (`bot/classifier.py`, ~linha 41): se antes pedimos o ID e
  ele chega agora, a ação guardada em `sessao["aguardando_id"]` é executada
  (consultar / cancelar / alterar / avançar) — o usuário não precisa repetir o verbo.

---

## 3. A camada de persistência (`bot/pedidos/persistencia.py`)

É o **único** arquivo que abre o `pedidos.csv`. Os 4 CRUDs chamam estas funções
para nunca duplicar leitura/escrita (padrão "repositório"):

| Função | O que faz |
|---|---|
| `carregar()` (linha 29) | Lê o `pedidos.csv` do disco e devolve um DataFrame (tudo como texto). |
| `salvar(df)` (linha 41) | Grava o DataFrame de volta no arquivo. **É aqui que a mudança vira permanente.** |
| `buscar_por_id(numero)` (linha 49) | Procura a linha do pedido. Devolve `(df, índice, linha)` ou `(df, None, None)`. |
| `gerar_id(df, ano)` (linha 69) | Gera o próximo ID `FF-AAAA-NNNN`, sequencial por ano (pega o maior e soma 1). |

Regra de ouro do professor: **todo UPDATE termina com SALVAR TABELA.** No nosso
código, isso é a chamada `persistencia.salvar(df)` no fim de cada operação que muda algo.

---

## 4. Cada operação em detalhe

### C — CREATE (registrar um pedido)

**Ativa em:** `bot/classifier.py` ~linha 60 (verbo `registrar/cadastrar/abrir/criar/fazer` + "pedido", ou "novo pedido").

**Caminho:** `responder.py:136` → `_fluxo_registrar()` (responder.py:59) → `criar.registrar_pedido()` (criar.py:43).

**Lógica:**
1. Como precisa de vários dados, é multi-turno. O `_fluxo_registrar()` pergunta
   **campo por campo**: produto → quantidade → cor → tamanho → tecido → personalização.
   O que já foi dito fica guardado em `sessao["registro_pedido"]`.
2. Cada resposta é lida pelo `extrair_slots`; se ele não reconhecer (ex: "100",
   "M", "nenhuma"), usamos o texto cru via `_valor_cru()` (responder.py:43).
3. Quando todos os campos estão preenchidos, chama `criar.registrar_pedido()`, que:
   - **gera o ID** (`persistencia.gerar_id`),
   - monta a linha com `etapa_atual="modelagem"`, `status="em_producao"` e uma
     previsão simples (hoje + 20 dias),
   - **insere** a linha (`df.loc[len(df)] = ...`) e **salva** o CSV,
   - retorna a confirmação com o número gerado.
4. Para abortar no meio: "cancelar", "sair", "deixa pra lá".

**Pseudocódigo do professor (CREATE):** RECEBER dados → `novo_id = GERAR_ID()` →
INSERIR nova_linha NA TABELA → RETORNAR "Pedido criado! Número: " + novo_id.

---

### R — READ (consultar um pedido pelo ID)

**Ativa em:** `bot/classifier.py` ~linha 81 (frases "status do pedido",
"consultar/acompanhar pedido", "andamento/etapa do pedido") **ou** ~linha 89
(quando o usuário manda só um número `FF-AAAA-NNNN`).

**Caminho:** `responder.py:381` → `consultar.consultar_pedido()` (consultar.py:44).

**Lógica:**
1. Se a mensagem **não** trouxe o ID, o bot pergunta e marca
   `sessao["aguardando_id"] = "status_pedido"`. A próxima mensagem com o número completa.
2. `consultar_pedido()` faz `buscar_por_id`:
   - **SE não achou** → devolve "Não encontrei o pedido..." (o "erro 404" que o
     professor ensina — todo READ precisa de um plano B).
   - **SENÃO** → monta a resposta com a **etapa atual de fabricação** e se ainda
     dá pra alterar. (Status de *entrega* fica com a logística — o bot avisa.)

**Pseudocódigo do professor (READ):** BUSCAR linha ONDE id = X → `SE linha É
VAZIO ENTÃO` erro `SENÃO` retorna o status. Está em `consultar.py`.

---

### U — UPDATE 1 (alterar um campo do pedido)

**Ativa em:** `bot/classifier.py` ~linha 53 (`alterar/mudar/trocar` + `cor/tamanho/quantidade/pedido`).

**Caminho:** `responder.py:396` → `_detectar_alteracao()` (responder.py:105) → `atualizar.alterar_campo()` (atualizar.py:53).

**Lógica:**
1. `_detectar_alteracao()` descobre **qual campo** mudar (cor / tamanho /
   quantidade / personalização) e **para qual valor**.
2. Se faltar o ID, o bot pergunta e guarda a alteração em
   `sessao["alteracao_pendente"]` até o número chegar.
3. `alterar_campo()` faz `buscar_por_id` e só altera **se a etapa permitir**
   (`_pode_alterar`, que lê o `lookup_etapas.csv` — só a `modelagem` permite).
   Depois grava com `salvar`.

**Pseudocódigo do professor (UPDATE = READ + alterar + SALVAR):** BUSCAR linha →
`SE existe`: muda a coluna → **SALVAR TABELA** → retorna confirmação.

---

### U — UPDATE 2 (avançar a etapa de fabricação)

> Esta é a **operação-assinatura do setor de Produção** segundo o material da
> Semana 3 ("Produção: UPDATE → avança a etapa de fabricação").

**Ativa em:** `bot/classifier.py` ~linha 67 ("avançar etapa", "próxima etapa",
"concluir etapa", "terminei a costura"...).

**Caminho:** `responder.py:431` → `atualizar.avancar_etapa()` (atualizar.py:109).

**Lógica:**
1. Pega o ID (ou pergunta).
2. `avancar_etapa()` acha a posição da etapa atual na ordem
   `modelagem → corte → costura → personalizacao → qualidade → embalagem_expedicao`
   e move para a próxima. Se já estava na última, marca `status="concluido"`.
   Depois **salva**.

---

### D — DELETE (cancelar — soft delete)

**Ativa em:** `bot/classifier.py` ~linha 48 (`cancelar` / `cancelamento`). É a
**primeira** regra de verbo, então "cancelar" vence qualquer outra interpretação.

**Caminho:** `responder.py:337` → `cancelar.cancelar_pedido()` (cancelar.py:28).

**Lógica:**
1. Pega o ID (ou pergunta).
2. `cancelar_pedido()` faz `buscar_por_id`, recusa se já estiver cancelado ou
   concluído, e senão faz o **soft delete**: muda `status="cancelado"` (e grava o
   motivo na `observacao`) — **não apaga a linha**. Depois **salva**.

**Por que soft delete:** preserva o histórico (mais seguro e auditável). O
professor ensina exatamente isso: soft delete é tecnicamente um UPDATE de status.

---

## 5. A memória da conversa (estados na sessão)

Em `bot/contexto.py`, a sessão guarda 4 campos que fazem o CRUD funcionar ao
longo de vários turnos:

| Campo da sessão | Para que serve |
|---|---|
| `registro_pedido` | Os dados que já coletamos no CREATE (ou `None`). |
| `registro_campo_pendente` | Qual campo estamos perguntando agora no CREATE. |
| `aguardando_id` | A ação que está esperando o ID ("status_pedido", "cancelar_pedido"...). |
| `alteracao_pendente` | O `{campo, valor}` guardado enquanto pedimos o ID no UPDATE. |

---

## 6. As tabelas CSV

**`data/lookup_etapas.csv`** (referência — as 6 etapas):

| coluna | exemplo |
|---|---|
| `etapa` | `modelagem` |
| `pode_alterar` | `sim` (só na modelagem) / `nao` |
| `descricao`, `observacao` | texto explicativo |

**`data/pedidos.csv`** (dados — os pedidos reais):

`numero_pedido, data_criacao, produto, quantidade, cor, tamanho, tecido,
personalizacao, etapa_atual, status, data_prevista, observacao`

- `etapa_atual` = o **status de fabricação** (aponta para uma etapa da lookup).
- `status` = ciclo macro: `em_producao` / `concluido` / `cancelado` / `pausado`.

---

## 7. Como rodar e testar

Demonstração automática (roda uma conversa exercitando os 4 CRUDs + avançar
etapa, e mostra o `pedidos.csv` antes/depois):

```bash
python demo_crud.py
```

Conversa de verdade pelo terminal:

```bash
python main.py
```

Interface web:

```bash
python -m uvicorn app:app --reload   # abre http://localhost:8000
```

---

## 8. Resumo de uma linha por operação

- **CREATE** → coleta na conversa, gera ID, insere linha, salva. (`criar.py`)
- **READ** → busca por ID; achou mostra a etapa, não achou avisa (erro 404). (`consultar.py`)
- **UPDATE campo** → busca, altera se a etapa permitir, salva. (`atualizar.py`)
- **UPDATE etapa** → busca, avança para a próxima etapa, salva. (`atualizar.py`)
- **DELETE** → busca, marca `status=cancelado` (soft delete), salva. (`cancelar.py`)
