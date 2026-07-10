# Fashion Flow Bot 🧵

Chatbot de atendimento do **setor de produção** da FashionFlow. Responde dúvidas
sobre produção (tecidos, processos, qualidade, personalização, prazos, cuidados,
catálogo, sustentabilidade) e **gerencia pedidos** (criar, consultar, alterar,
cancelar) — tudo pela conversa, usando arquivos **CSV** como base de conhecimento
(sem IA externa).

> 🎓 Projeto acadêmico — Prof. Anderson Barbosa (Semanas 1–4 / Prova P3).

## 👥 Equipe

- **Alisson Damasceno**
- **Bernardo Mota**
- **Márcia Beatriz Costa**
- **Vinícius** (oreddd)

## ✨ O que ele faz

- **Classificação por intenção** com **pesos** (a intenção mais específica vence no desempate).
- **Memória da conversa**: lembra do contexto, do **nome do cliente** e do estado do diálogo.
- **Respostas personalizadas** desde o início ("Maria, ...").
- **CRUD de pedidos** acontecendo na conversa, com **persistência real** (altera o CSV de verdade).
- **Trava de dono**: cada cliente só mexe nos pedidos que estão no nome dele.
- **Filtro de segurança**: bloqueia senha, CVV e número de cartão.
- **Fronteiras de setor**: encaminha o que não é de produção (preço → vendas, entrega → logística...).

## 🚀 Como rodar

```bash
# 1. (recomendado) ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1

# 2. dependências
pip install -r requirements.txt
```

| Quero... | Comando |
|---|---|
| 💬 Conversar no terminal | `python main.py` |
| 🌐 Subir a interface web | `python -m uvicorn app:app --reload` → http://localhost:8000 |
| 🎬 Ver o CRUD funcionando (demo) | `python demo_crud.py` |
| 🛠️ Gerenciar a base de conhecimento (dev) | `python gerenciar_intencoes.py` |
| ✅ Rodar os testes | `python -m unittest test_crud -v` |

No terminal, `/contexto` mostra a memória da sessão e `sair` encerra.

## 🧪 Testes

```bash
python -m unittest test_crud -v
```

São **42 testes** cobrindo o CRUD de pedidos (com casos de erro e borda), a trava
de dono e o CRUD de intenções. Eles rodam em **cópias temporárias** dos CSVs, então
**não tocam nos dados reais**.

## 🗂️ Estrutura

```
fashion_flow_bot/
├── main.py / app.py         # interface de terminal / API web (FastAPI)
├── demo_crud.py             # demonstração do CRUD + trava de dono
├── gerenciar_intencoes.py   # ferramenta DEV: CRUD da base de conhecimento
├── test_crud.py             # 42 testes automatizados
├── bot/                     # o "cérebro": loader, extractor, classifier,
│   │                        #   contexto, responder, cliente, estados, seguranca
│   └── pedidos/             # CRUD de pedidos (criar, consultar, atualizar, cancelar)
├── data/                    # base de conhecimento e dados (CSV)
└── docs/                    # documentação e entregáveis
```

## 📖 Documentação completa

A documentação detalhada — arquitetura, dados, funcionalidades e **as decisões de
design com o porquê de cada uma** — está em:

- **[DOCUMENTACAO.md](DOCUMENTACAO.md)** (versão para leitura no GitHub)
- **[docs/documentacao_projeto.docx](docs/documentacao_projeto.docx)** (versão para entrega)

Guias complementares: [GUIA_CRUD_PEDIDOS.md](GUIA_CRUD_PEDIDOS.md) (referência de
código do CRUD) e `RESUMO_APRESENTACAO_CRUD.txt` (roteiro de apresentação).

## ☁️ Deploy

O backend é uma API FastAPI que precisa de um **servidor persistente** (que fica
rodando e escreve em disco) — porque o CRUD grava no `pedidos.csv` e a memória da
conversa vive no processo. Plataformas recomendadas: **Render** (mais direto),
**Hugging Face Spaces**, **Railway** ou **Fly.io**. O `Procfile` e o `render.yaml`
já estão prontos, e a interface web detecta a URL da API sozinha.

> ⚠️ **Vercel não serve** para este projeto: é *serverless* (sistema de arquivos
> somente-leitura e sem estado entre requisições), então o CRUD não conseguiria
> gravar no CSV e o bot perderia a memória da conversa.

### Render (grátis)

1. [render.com](https://render.com) → login com GitHub → **New +** → **Blueprint**.
2. Conecte o repositório `fashion_flow_bot` — o Render lê o `render.yaml` e já
   configura o build e o start. Clique em **Apply**.
3. Aguarde o build (~2–3 min). Abra a URL gerada — o chat funciona sozinho.

> No plano grátis o serviço dorme após ~15 min parado (a 1ª mensagem depois
> demora ~30s) e o disco é efêmero (o `pedidos.csv` reseta ao reiniciar).
