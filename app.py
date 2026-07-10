"""
API REST do Fashion Flow Bot (FastAPI).
Cada cliente identifica sua sessão pelo sessao_id.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from bot.loader import carregar_dados
from bot.extractor import extrair_slots
from bot.classifier import classificar
from bot.politica import limpar_menu_se_mudou_assunto
from bot.responder import responder
from bot.seguranca import verificar_seguranca
from bot.cliente import tratar_nome, personalizar
from bot.contexto import (
    criar_sessao, resetar_sessao,
    is_despedida, is_casual,
    merge_com_contexto, atualizar_sessao_pos_turno,
)


app = FastAPI(title="Fashion Flow Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dados carregados uma vez
dados = carregar_dados()

# Sessões em memória — cada sessao_id tem seu próprio contexto
sessoes = {}


class MensagemRequest(BaseModel):
    sessao_id: str
    mensagem: str


@app.post("/chat")
def chat(req: MensagemRequest):
    sessao_id = req.sessao_id
    mensagem = req.mensagem.strip()

    if sessao_id not in sessoes:
        sessoes[sessao_id] = criar_sessao()
    sessao = sessoes[sessao_id]

    if not mensagem:
        return {"resposta": ""}
    
    # Filtro de Segurança: bloqueia dados sensíveis antes de tudo
    bloqueio = verificar_seguranca(mensagem)
    if bloqueio:
        return {"resposta": bloqueio, "intencao": "bloqueio_seguranca"}

    # Personalização: no início da conversa, pergunta e guarda o nome do cliente.
    resposta_nome = tratar_nome(mensagem, sessao)
    if resposta_nome is not None:
        return {"resposta": resposta_nome, "intencao": "captura_nome"}

    if is_despedida(mensagem):
        sessoes[sessao_id] = resetar_sessao(sessao)
        return {"resposta": "Até logo! Se precisar, é só voltar."}

    # "sim/ok" curto vira "pode continuar" — MAS não quando estamos perguntando
    # "quer mais um produto?" (aí "sim" tem que iniciar o próximo item).
    if is_casual(mensagem) and sessao["ativa"] and not sessao.get("aguardando_mais_produto"):
        return {"resposta": "Beleza, pode continuar!"}

    limpar_menu_se_mudou_assunto(mensagem, sessao)
    em_menu = bool(sessao.get("aguardando_opcao"))
    slots_turno = extrair_slots(mensagem, em_menu=em_menu)
    slots_efetivos = merge_com_contexto(slots_turno, sessao, mensagem)
    intencao = classificar(mensagem, slots_turno, slots_efetivos, dados["intencoes"], sessao)
    resposta = responder(intencao, slots_efetivos, dados, sessao, mensagem)
    resposta = personalizar(resposta, sessao)
    atualizar_sessao_pos_turno(sessao, mensagem, slots_efetivos, intencao, resposta)

    return {"resposta": resposta, "intencao": intencao}


@app.get("/sessao/{sessao_id}")
def get_sessao(sessao_id: str):
    """Retorna o estado atual de uma sessão (útil pra debug e demo)."""
    if sessao_id not in sessoes:
        return {"erro": "sessão não encontrada"}
    s = sessoes[sessao_id]
    return {
        "estado_conversa": s.get("estado_conversa"),
        "objetivo_usuario": s.get("objetivo_usuario"),
        "foco_atual": s["foco_atual"],
        "ultimo_assunto": s["ultimo_assunto"],
        "aguardando_opcao": s["aguardando_opcao"],
        "intencao_escolhida": s.get("intencao_escolhida"),
        "confianca": s.get("confianca"),
        "intencao_candidatas": s.get("intencao_candidatas", []),
        "qtd_turnos": len(s["historico_turnos"]),
        "historico": s["historico_turnos"],
    }


INDEX_HTML = Path(__file__).parent / "index.html"
INDEX_ALT_HTML = Path(__file__).parent / "index_alt.html"


@app.get("/")
def root():
    """Serve o frontend HTML principal (Bernardo, paleta verde)."""
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return {"status": "Fashion Flow Bot online"}


@app.get("/alt")
def alt():
    """Frontend alternativo (Vinicius/oreddd, paleta azul)."""
    if INDEX_ALT_HTML.exists():
        return FileResponse(str(INDEX_ALT_HTML))
    return {"erro": "index_alt.html não encontrado"}


@app.get("/status")
def status():
    return {"status": "Fashion Flow Bot online", "sessoes_ativas": len(sessoes)}
