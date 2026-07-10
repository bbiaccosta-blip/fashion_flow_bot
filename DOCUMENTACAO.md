# Documentação do Projeto — Fashion Flow Bot

Documentação completa do chatbot do **setor de produção** da FashionFlow: o que é,
como funciona, e — principalmente — **as decisões de design e o porquê de cada uma**.

> Projeto acadêmico — Prof. Anderson Barbosa (Semanas 1–4 / Prova P3).
> **Equipe:** Alisson Damasceno · Bernardo Mota · Márcia Beatriz Costa · Vinícius (oreddd).

## Índice
1. [Visão geral](#1-visão-geral)
2. [Como rodar](#2-como-rodar)
3. [Arquitetura](#3-arquitetura)
4. [Os dados (CSVs)](#4-os-dados-csvs)
5. [Funcionalidades em detalhe](#5-funcionalidades-em-detalhe)
6. [Decisões de design (e o porquê)](#6-decisões-de-design-e-o-porquê)
7. [Como testar](#7-como-testar)
8. [Limitações conhecidas](#8-limitações-conhecidas)
9. [Mapa de arquivos](#9-mapa-de-arquivos)
10. [Glossário](#10-glossário)

---

## 1. Visão geral

O Fashion Flow Bot é um **chatbot de atendimento do setor de produção** de uma
confecção fictícia. Ele responde dúvidas sobre produção (tecidos, processos,
qualidade, personalização, prazos, cuidados, catálogo, sustentabilidade) e
**gerencia pedidos** (criar, consultar, alterar, cancelar), tudo pela conversa.

Características centrais:
- **Sem IA externa.** O "cérebro" é uma matriz de conhecimento em CSV + regras em
  Python (classificação por intenção, busca dinâmica). É transparente e fácil de manter.
- **Persistência real.** As operações de pedido **alteram os arquivos CSV de verdade**.
- **Memória da conversa.** O bot lembra do contexto, do nome do cliente e do estado
  do diálogo (tema "A Memória do Bot", Semana 3).

**Restrição que guia tudo:** somos **apenas o bot do setor de produção**. Isso
decide o que o bot responde (fabricação) e o que ele encaminha para outro setor
(entrega → logística; preço/pagamento/fechamento → vendas; devolução → devoluções).

---

## 2. Como rodar

```bash
pip install -r requirements.txt
```

| Quero... | Comando |
|---|---|
| Conversar no terminal | `python main.py` |
| Subir a interface web | `python -m uvicorn app:app --reload` → http://localhost:8000 |
| Ver o CRUD funcionando (demo) | `python demo_crud.py` |
| Gerenciar a base de conhecimento (dev) | `python gerenciar_intencoes.py` |
| Rodar os testes | `python -m unittest test_crud -v` |

No terminal, o comando `/contexto` mostra a memória da sessão (estado, objetivo,
foco, histórico) e `sair` encerra.

---

## 3. Arquitetura

### 3.1 O pipeline (o caminho de uma mensagem)

Cada mensagem do usuário passa por esta sequência (em `main.py` e `app.py`):

```
mensagem do usuário
  → verificar_seguranca()      bloqueia senha/CVV/cartão antes de tudo      (seguranca.py)
  → tratar_nome()              no início, pergunta e guarda o nome          (cliente.py)
  → is_despedida / is_casual   atalhos ("tchau", "ok")                      (contexto.py)
  → extrair_slots()            acha produto, cor, numero_pedido...          (extractor.py)
  → merge_com_contexto()       junta com a memória da conversa              (contexto.py)
  → classificar()              decide a intenção (usa os PESOS)             (classifier.py)
  → responder()                monta a resposta; no CRUD chama bot/pedidos/ (responder.py)
        → bot/pedidos/<op>     regra de negócio do CRUD
              → persistencia   lê/grava o pedidos.csv
  → personalizar()             coloca o nome na frente ("Maria, ...")       (cliente.py)
  → atualizar_sessao_pos_turno() atualiza foco, histórico e estados         (contexto.py)
```

### 3.2 Mapa de módulos

| Módulo | Responsabilidade |
|---|---|
| `bot/loader.py` | Carrega todos os CSVs em memória (um DataFrame por tabela). |
| `bot/normalizar.py` | Função única de normalização (minúsculo + sem acento). |
| `bot/seguranca.py` | Filtro que bloqueia dados sensíveis (senha, CVV, cartão). |
| `bot/extractor.py` | Extrai "slots" (dados) da mensagem — produto, cor, quantidade, número do pedido... |
| `bot/contexto.py` | A memória da conversa: foco atual, histórico, estados, despedida/casual. |
| `bot/classifier.py` | Decide a intenção por prioridade de regras + peso das intenções. |
| `bot/responder.py` | Monta a resposta a partir da intenção + dados. |
| `bot/cliente.py` | Nome do cliente: captura no início e personaliza as respostas. |
| `bot/estados.py` | O "mapa de estados": onde a conversa está + o que o usuário quer. |
| `bot/pedidos/` | O **CRUD de pedidos** (um arquivo por operação) — detalhado na seção 5.8. |

### 3.3 Duas interfaces, mesmo cérebro

- `main.py` — terminal (loop `while`, para testes rápidos).
- `app.py` — API REST (FastAPI) que serve o `index.html`. Cada aba é uma sessão isolada
  (dict de sessões por `sessao_id`).

Ambas chamam **o mesmo pipeline** (seção 3.1), então qualquer melhoria vale para as duas.

---

## 4. Os dados (CSVs)

Tudo que o bot "sabe" e "lembra" vive em `data/`. São dois tipos:

### 4.1 Base de conhecimento e slots
- **`intencoes.csv`** — a **matriz de conhecimento** (147 intenções). Colunas:
  `id_intencao, palavras_chave, tipo_resposta, resposta_padrao, pergunta_followup, peso`.
  Cada linha é uma "regra": se a frase bate numa palavra-chave, o bot responde com aquela resposta.
- **`slots.csv`** — documenta os "slots" (dados extraíveis): produto, cor, quantidade,
  `numero_pedido` (formato `FF-AAAA-NNNN`), etc.

### 4.2 Tabelas de referência (lookup)
Respostas dinâmicas (prazo, preço, compatibilidade...) saem de tabelas:
`lookup_prazo`, `lookup_preco`, `lookup_cor_tecido`, `lookup_compat_tecido_produto`,
`lookup_compat_tecido_personalizacao`, `lookup_tamanho_produto`, `lookup_gramatura`,
`lookup_consumo_tecido`, `lookup_capacidade_produtiva`, `lookup_estoque_materiais`, e
**`lookup_etapas.csv`** (as 6 etapas de fabricação + se cada uma permite alteração).

### 4.3 A tabela de pedidos
- **`pedidos.csv`** — os pedidos reais (o "fato"). Colunas:
  `numero_pedido, data_criacao, cliente, produto, quantidade, cor, tamanho, tecido,
  personalizacao, etapa_atual, status, data_prevista, observacao`.
  - `etapa_atual` aponta para uma etapa de `lookup_etapas.csv` (é o **status de fabricação**).
  - `status` = ciclo macro: `em_producao` / `concluido` / `cancelado` / `pausado`.
  - `cliente` = o **dono** do pedido (usado na trava de dono).

---

## 5. Funcionalidades em detalhe

### 5.1 Classificação por intenção + pesos
O `classifier.py` decide a intenção em camadas de prioridade: primeiro regras por
**verbo** (ex.: "cancelar"), depois por **slot** (ex.: um número de pedido), depois
**palavra-chave** do CSV e, por fim, **similaridade** (rapidfuzz). Quando várias
intenções batem na mesma frase, vence a de **maior peso** (coluna `peso`).

### 5.2 Extração de slots
O `extractor.py` é uma função **pura** (não mexe na sessão): lê a mensagem e devolve
os dados encontrados. Trata negação ("sem bordado"), plurais, e extrai o número do
pedido antes da quantidade (pra "FF-2024-0123" não virar "quantidade 2024").

### 5.3 Memória da conversa
O `contexto.py` guarda dois níveis: **`foco_atual`** (o assunto de agora, curto prazo)
e **`historico_turnos`** (tudo que aconteceu, longo prazo). Quando o produto muda, os
slots-filhos (cor, tecido...) do produto antigo são esquecidos do foco — mas o histórico
preserva tudo.

### 5.4 Mapa de estados
O `estados.py` traduz a conversa em dois rótulos, atualizados a cada turno:
- **`estado_conversa`** (onde estamos): `OCIOSO`, `AGUARDANDO_NOME`, `EM_ASSUNTO`,
  `AGUARDANDO_OPCAO`, `AGUARDANDO_ID`, `COLETANDO_PEDIDO`.
- **`objetivo_usuario`** (o que quer): `CONVERSA_SOCIAL`, `TIRAR_DUVIDA`,
  `SIMULAR_PEDIDO`, `GERIR_PEDIDO`, `IR_OUTRO_SETOR`, `INDEFINIDO`.

### 5.5 Personalização
O `cliente.py` pergunta o nome no **começo** da conversa, guarda em `nome_cliente`, e
prefixa o nome nas respostas ("Maria, ..."). Limpa introduções ("me chamo...") e usa só
o primeiro nome.

### 5.6 Filtro de segurança
O `seguranca.py` roda **antes de tudo**: se a mensagem tem senha, CVV ou número de
cartão, o bot bloqueia o turno e orienta a nunca compartilhar esses dados no chat.

### 5.7 Fronteiras de setor
O bot responde só o que é de produção. Para o resto, **encaminha** (intenções `setor_*`):
preço/pagamento → vendas; entrega/frete/rastreio → logística; devolução/defeito →
devoluções; matéria-prima → almoxarifado/compras.

### 5.8 CRUD de pedidos (`bot/pedidos/`)
Um arquivo por operação, todos apoiados num único `persistencia.py`:

| Operação | Arquivo | O que faz |
|---|---|---|
| **CREATE** | `criar.py` | Coleta os dados na conversa, **gera o ID** e grava a linha (nasce em `modelagem`/`em_producao`). |
| **READ** | `consultar.py` | Acha o pedido pelo ID e mostra a etapa atual (ou "não encontrei" = erro 404). |
| **UPDATE** | `atualizar.py` | `alterar_campo` (só na modelagem) e `avancar_etapa` (operador). |
| **DELETE** | `cancelar.py` | **Soft delete**: marca `status=cancelado`, não apaga a linha. |
| (infra) | `persistencia.py` | Único que lê/grava o `pedidos.csv` + `e_dono()` (trava de dono). |

### 5.9 Trava de dono (ownership)
Como o chat é do **cliente**, ele só mexe nos pedidos que estão no nome dele. O nome
(capturado pela personalização) é comparado com a coluna `cliente` do pedido via
`persistencia.e_dono()` (sem ligar pra maiúscula/acento). Não bateu → *"esse pedido não
está no seu nome"*. `avancar_etapa` (operador) não tem essa trava.

### 5.10 CRUD da base de conhecimento (dev)
O `gerenciar_intencoes.py` (na raiz) é uma ferramenta **de desenvolvedor** para
criar/consultar/atualizar/remover intenções do `intencoes.csv` (com o peso). **Não** faz
parte do chat — o bot só **lê** as intenções; quem gerencia são os devs.

---

## 6. Decisões de design (e o porquê)

> Esta é a seção principal: cada decisão importante, com o motivo.

**D1 — Base de conhecimento em CSV (matriz), sem IA externa.**
*Por quê:* é o que o material pede (Semanas 1–4); é transparente e fácil de manter —
adicionar uma linha no CSV já ensina uma resposta nova, sem mexer no código.

**D2 — Pipeline modular (um módulo por responsabilidade).**
*Por quê:* clareza e testabilidade. O projeto é didático e precisa ser **entendido e
explicado**, então separamos extrair / classificar / responder / contexto / segurança.

**D3 — Pesos nas intenções (coluna `peso`).**
*Por quê:* o professor pediu pesos em sala. Servem de **desempate**: quando várias
intenções batem, a de maior peso vence (a específica ganha da genérica). Antes era "a
primeira do arquivo", o que dependia da ordem das linhas.

**D4 — Memória em dois níveis (foco + histórico) com invalidação.**
*Por quê:* tema da Semana 3 ("a memória do bot"). Resolve o bug de "slots grudando" —
quando o cliente troca de produto, o bot não pode continuar respondendo com a cor/tecido
do produto anterior. O histórico guarda tudo; o foco só o assunto de agora.

**D5 — Mapa de estados explícito (`estado_conversa` + `objetivo_usuario`).**
*Por quê:* o professor falou em "mapear estados da conversa e do que o usuário quer". Dar
nome aos estados deixa o contexto inspecionável (`/contexto`) e demonstrável.

**D6 — `SIMULAR_PEDIDO` em vez de "FAZER_ORCAMENTO".**
*Por quê:* "orçamento" fechado (com preço e pagamento) é de **vendas**, não de produção.
A produção só **estima** (prazo, viabilidade, consumo de material, preço indicativo) — o
nome reflete isso e mantém a coerência de setor.

**D7 — `AGUARDANDO_NOME` como estado.**
*Por quê:* depois de adicionar a captura de nome, faltava representar essa fase; sem ela,
o bot aparecia como `OCIOSO` enquanto perguntava o nome.

**D8 — Personalização desde o início.**
*Por quê:* o professor quer interações personalizadas. Encaixa no tema "memória": o bot
guarda o nome e chama o cliente por ele. Perguntamos no começo para personalizar tudo.

**D9 — CRUD de pedidos conversacional e com persistência real.**
*Por quê:* requisito do professor — o CRUD tem que acontecer **ao longo da conversa**,
com as requisições do cliente **alterando o CSV de verdade**.

**D10 — Duas tabelas: `lookup_etapas` (referência) + `pedidos` (dados).**
*Por quê:* o `lookup_pedidos.csv` original era, na verdade, a tabela de **etapas** (não de
pedidos). Separar referência de dado é o padrão limpo; o pedido aponta para a etapa.

**D11 — Um arquivo por operação de CRUD + persistência única (padrão repositório).**
*Por quê:* clareza > DRY num projeto didático. Cada operação fica fácil de ler e explicar;
e como só o `persistencia.py` toca o arquivo, trocar CSV por banco no futuro muda **um**
arquivo só.

**D12 — ID sequencial `FF-AAAA-NNNN` (em vez de aleatório).**
*Por quê:* também é único, mas fica legível e ordenado por ano. (O material usa
`GERAR_ID_ALEATORIO`; ambos resolvem o "gerar ID".)

**D13 — Soft delete (cancelar = mudar status, não apagar).**
*Por quê:* preserva o histórico — mais realista numa fábrica e mais seguro (nada some por
acidente). Tecnicamente, é um UPDATE de status.

**D14 — Alteração travada por etapa (só na `modelagem`).**
*Por quê:* espelha a fábrica real — depois do corte, mudar gera retrabalho e custo. A
regra mora na coluna `pode_alterar` da tabela de etapas.

**D15 — "Status do pedido" = etapa de fabricação.**
*Por quê:* coerência de setor. Produção sabe em que etapa a peça está; **entrega** é com a
logística (o bot avisa isso).

**D16 — "Avançar etapa" é do operador, fora do chat do cliente.**
*Por quê:* o chat é do cliente, e empurrar a peça na esteira é ação **interna** da
produção. Como painel de operador ficou fora do escopo, a função existe e é demonstrada
por testes/demo, mas o cliente não dispara pelo chat.

**D17 — CRUD da base de conhecimento é dev-side.**
*Por quê:* deixar o **usuário do bot** criar/alterar/apagar intenções seria furo de
segurança. O professor usou a técnica dizendo que **os devs** gerenciam as intenções —
por isso virou uma ferramenta separada (`gerenciar_intencoes.py`).

**D18 — Trava de dono por nome (em vez de login).**
*Por quê:* login e tela de autenticação ficaram fora do escopo acadêmico. Reaproveitamos
o nome já capturado: cada pedido tem dono e o cliente só vê/mexe nos seus. (Limitação
conhecida: nome não é prova de identidade — ver seção 8.)

**D19 — Filtro de segurança antes de tudo.**
*Por quê:* dados sensíveis (senha, CVV, cartão) nunca devem ser processados; o bot bloqueia
e orienta, independente do que mais a mensagem tenha.

**D20 — Função `normalizar` única.**
*Por quê:* estava copiada em 5 arquivos. Centralizar garante que todos comparem texto do
mesmo jeito (e evita divergência).

---

## 7. Como testar

- **Testes automatizados:** `python -m unittest test_crud -v` — **42 testes** cobrindo o
  CRUD de pedidos (criar/consultar/alterar/avançar/cancelar, com casos de erro e borda),
  a **trava de dono** e o CRUD de intenções. Rodam em **cópias temporárias** dos CSVs, então
  **não tocam nos dados reais**.
- **Demonstração:** `python demo_crud.py` — roda uma conversa que exercita os 4 CRUDs +
  a trava de dono (um cliente tentando ver o pedido de outro) e mostra o `pedidos.csv`
  antes e depois. Reseta a semente no início (repetível).

---

## 8. Limitações conhecidas

- **Sem autenticação real.** A trava de dono usa o nome informado, que não é prova de
  identidade (alguém poderia dizer o nome de outro). Num sistema real, teria login. Ficou
  como limitação consciente — login/painel estavam fora do escopo acadêmico.
- **Preço é indicativo.** A produção dá estimativa; preço e pagamento fecham com vendas.
- **`data_prevista` usa prazo fixo** (20 dias) no CREATE; poderia puxar do `lookup_prazo`.
- **NLU simples** (palavra-chave + fuzzy): erros de digitação muito fortes podem cair no
  fallback.

---

## 9. Mapa de arquivos

```
fashion_flow_bot/
├── main.py                  # interface de terminal (loop de conversa)
├── app.py                   # API REST (FastAPI) + serve o index.html
├── index.html / index_alt.html  # frontends web
├── demo_crud.py             # demonstração do CRUD + trava de dono
├── gerenciar_intencoes.py   # ferramenta DEV: CRUD da base de conhecimento
├── test_crud.py             # 42 testes automatizados (em cópias temporárias)
├── requirements.txt
├── bot/
│   ├── loader.py            # carrega os CSVs
│   ├── normalizar.py        # normalização de texto (única)
│   ├── seguranca.py         # filtro de dados sensíveis
│   ├── extractor.py         # extrai slots da mensagem (função pura)
│   ├── contexto.py          # memória da conversa (foco, histórico, estados)
│   ├── classifier.py        # decide a intenção (prioridade + pesos)
│   ├── responder.py         # monta a resposta
│   ├── cliente.py           # nome do cliente + personalização
│   ├── estados.py           # mapa de estados (conversa + objetivo)
│   └── pedidos/             # CRUD de pedidos
│       ├── persistencia.py  #   lê/grava pedidos.csv + e_dono (trava de dono)
│       ├── criar.py         #   CREATE
│       ├── consultar.py     #   READ
│       ├── atualizar.py     #   UPDATE (alterar_campo + avancar_etapa)
│       └── cancelar.py      #   DELETE (soft delete)
├── data/
│   ├── intencoes.csv        # matriz de conhecimento (147 intenções, com peso)
│   ├── slots.csv            # documentação dos slots
│   ├── pedidos.csv          # os pedidos reais (com dono)
│   ├── lookup_etapas.csv    # as 6 etapas de fabricação
│   └── lookup_*.csv         # prazo, preço, compatibilidades, estoque, etc.
└── docs/                    # entregáveis .docx + geradores (auditoria, proposta...)
```

Documentos complementares: `GUIA_CRUD_PEDIDOS.md` (referência de código do CRUD),
`RESUMO_APRESENTACAO_CRUD.txt` (roteiro de apresentação), `README.md` (instalação).

---

## 10. Glossário

| Termo | O que é |
|---|---|
| **Intenção** | O objetivo por trás da frase (ex.: "quanto custa?" → preço). |
| **Slot** | Um dado extraído da mensagem (ex.: "200 polos" → quantidade=200, produto=polo). |
| **Matriz de conhecimento** | A tabela `intencoes.csv` (intenção × palavras-chave × resposta). |
| **Peso** | Prioridade da intenção no desempate (maior peso vence). |
| **Foco atual** | Os slots do assunto que está sendo discutido agora. |
| **Estado da conversa** | Onde o diálogo está (ex.: esperando um menu, coletando um pedido). |
| **Objetivo do usuário** | A meta grande por trás da conversa (ex.: tirar dúvida, gerir pedido). |
| **CRUD** | Create, Read, Update, Delete — as 4 operações sobre dados. |
| **Soft delete** | "Apagar" marcando como cancelado, sem remover a linha (preserva histórico). |
| **Trava de dono** | Só o dono do pedido (pelo nome) pode consultá-lo/alterá-lo/cancelá-lo. |
| **Persistência** | Gravar no disco (CSV) para o dado sobreviver depois que o programa fecha. |

---

*Documentação gerada para o projeto Fashion Flow Bot — setor de produção.*
