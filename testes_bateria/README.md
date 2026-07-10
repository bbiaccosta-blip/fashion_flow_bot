# Bateria de perguntas — teste de coerência do bot

Roda ~1000 perguntas comuns contra o pipeline REAL do bot (o mesmo do `app.py`)
e sinaliza respostas incoerentes. É a "bateria grande" combinada como próximo passo
de qualidade das respostas.

## Como funciona

Cada pergunta roda numa **sessão isolada** com o nome já definido ("Bia") — assim o
teste mede só a **qualidade da classificação**, sem contaminação de contexto entre
perguntas nem a etapa de captura de nome. A intenção classificada é comparada com o
conjunto de intenções **aceitáveis** daquela categoria (mapa em `testar_bot.py`).

## Arquivos

| arquivo | o que é |
|---|---|
| `gerar_perguntas.py` | gera as perguntas (por categoria, com gíria/typo/minúsculas) → `perguntas.csv` |
| `testar_bot.py` | roda a bateria → `resultados.csv` + `problemas.csv` + relatório no terminal |
| `perguntas.csv` | as ~1000 perguntas: `categoria,pergunta` |
| `resultados.csv` | toda pergunta com `intencao`, `status` (OK/FALLBACK/MISMATCH), `resposta` |
| `problemas.csv` | só as sinalizadas — é por onde a gente corrige os padrões |

## Rodar

```bash
cd fashion_flow_bot
.venv/bin/python testes_bateria/gerar_perguntas.py   # regenera perguntas.csv
.venv/bin/python testes_bateria/testar_bot.py        # roda e gera o relatório
```

## Status (última rodada)

- **90,1%** das perguntas caem numa intenção coerente (era 83,0% antes das correções).
- Fallback (bot não entendeu): de 37 → **4** perguntas (0,4%).
- Os 42 testes do CRUD seguem verdes — nenhuma regressão.

Correções aplicadas (tudo verificado pela bateria):

1. **`bot/classifier.py` — 2 bugs estruturais de match:**
   - keyword por substring → agora exige fronteira de palavra (`\b`), senão "mano"
     casava dentro de "hu**mano**", "vei" em "dura**vei**s"/"sustenta**vei**s".
   - fuzzy casava tokens ≤3 letras dentro de palavras longas → agora ignorados no fuzzy.
2. **`bot/classifier.py` — 2 regras novas:**
   - prazo + personalização → `prazo_com_personalizacao` (antes "prazo com silk" só
     descrevia o silk, não respondia o prazo).
   - "capacidade" sozinha vira `producao_capacidade` (info), não `viabilidade_producao`.
3. **`data/intencoes.csv` — 62 palavras-chave** adicionadas a 21 intenções (frases
   comuns que caíam em fallback: "opa", "customizar", "png/cdr", "tingem", "que horas"…).
   Ver `adicionar_keywords.py` pra a lista exata (script idempotente, já aplicado).

Restante (~101 near-misses): sub-tópico vizinho (ex.: "como cuido do jeans" → menu de
calças em vez do cuidado específico) e decisões de "isso é produção ou outro setor?"
(ex.: "veio com defeito" → devolução; "prazo de entrega" → logística). Ver `problemas.csv`.
