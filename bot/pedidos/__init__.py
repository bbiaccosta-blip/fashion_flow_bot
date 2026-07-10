"""
Pacote bot.pedidos — o CRUD de pedidos do setor de produção.

Um arquivo por operação, pra ficar fácil de ler e explicar:

    criar.py       → CREATE   (registrar_pedido)
    consultar.py   → READ     (consultar_pedido)
    atualizar.py   → UPDATE   (alterar_campo, avancar_etapa)
    cancelar.py    → DELETE   (cancelar_pedido — soft delete)
    persistencia.py → lê e grava o data/pedidos.csv (usado pelos quatro acima)

A ideia: cada CRUD cuida SÓ da sua regra de negócio. Quem mexe no arquivo CSV
de verdade é o persistencia.py. Se um dia trocarmos o CSV por um banco, só o
persistencia.py muda.
"""
