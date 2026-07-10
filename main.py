"""
Loop de chat no terminal — Fashion Flow Bot.
"""
import sys
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


def main():
    # Garante UTF-8 no terminal Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("=" * 60)
    print("  Fashion Flow Bot — Atendimento de Produção")
    print("=" * 60)
    print("Digite sua dúvida. Comandos: 'sair' encerra, '/contexto' mostra a memória.\n")

    dados = carregar_dados()
    sessao = criar_sessao()

    while True:
        try:
            mensagem = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo!")
            break

        if not mensagem:
            continue

        # Filtro de Segurança: bloqueia dados sensíveis antes de tudo
        bloqueio = verificar_seguranca(mensagem)
        if bloqueio:
            print(f"Bot: {bloqueio}\n")
            continue


        if mensagem.lower() in ("sair", "exit", "quit"):
            print("Bot: Até logo! Qualquer dúvida é só chamar.")
            break

        # Comando de debug: mostra o foco atual e o histórico
        if mensagem.startswith("/contexto"):
            print(f"  estado_conversa: {sessao['estado_conversa']}")
            print(f"  objetivo_usuario: {sessao['objetivo_usuario']}")
            print(f"  foco_atual: {sessao['foco_atual']}")
            print(f"  ultimo_assunto: {sessao['ultimo_assunto']}")
            print(f"  aguardando_opcao: {sessao['aguardando_opcao']}")
            print(f"  intencao_escolhida: {sessao.get('intencao_escolhida')}  "
                  f"(confianca {sessao.get('confianca')})")
            print(f"  candidatas (re-ranking por score):")
            for c in sessao.get("intencao_candidatas", []):
                print(f"    {c['score']:.3f}  {c['intencao']}  (por {c['por']})")
            print(f"  historico ({len(sessao['historico_turnos'])} turnos):")
            for i, t in enumerate(sessao["historico_turnos"][-5:], 1):
                print(f"    {i}. [{t['intencao']}] {t['msg']!r}")
            print()
            continue

        # Personalização (Semana 3): no começo da conversa, o bot pergunta e
        # guarda o nome do cliente. Enquanto cuida disso, não roda o fluxo normal.
        resposta_nome = tratar_nome(mensagem, sessao)
        if resposta_nome is not None:
            print(f"Bot: {resposta_nome}\n")
            continue

        # Despedida pura → reseta sessão
        if is_despedida(mensagem):
            print("Bot: Até logo! Se precisar, é só voltar.\n")
            sessao = resetar_sessao(sessao)
            continue

        # Casual ("ok", "blz", "obrigado") → não muda assunto. Exceção: quando
        # estamos perguntando "quer mais um produto?", "sim" inicia o próximo item.
        if is_casual(mensagem) and sessao["ativa"] and not sessao.get("aguardando_mais_produto"):
            print("Bot: Beleza, pode continuar!\n")
            continue

        # Pipeline principal
        limpar_menu_se_mudou_assunto(mensagem, sessao)
        em_menu = bool(sessao.get("aguardando_opcao"))
        slots_turno = extrair_slots(mensagem, em_menu=em_menu)
        slots_efetivos = merge_com_contexto(slots_turno, sessao, mensagem)
        intencao = classificar(mensagem, slots_turno, slots_efetivos, dados["intencoes"], sessao)
        resposta = responder(intencao, slots_efetivos, dados, sessao, mensagem)
        resposta = personalizar(resposta, sessao)   # chama o cliente pelo nome
        atualizar_sessao_pos_turno(sessao, mensagem, slots_efetivos, intencao, resposta)

        print(f"Bot: {resposta}\n")


if __name__ == "__main__":
    main()
