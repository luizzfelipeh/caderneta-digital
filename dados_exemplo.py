"""
Cria clientes e lançamentos FICTÍCIOS para demonstração e prints do protótipo.
Assim nenhum dado real de cliente do mercadinho aparece no trabalho (LGPD).

Uso:  python dados_exemplo.py
Atenção: só use em um banco de testes. Para apagar tudo, exclua o arquivo
instance/caderneta.db e rode o criar_usuario.py novamente.
"""
from datetime import timedelta
from decimal import Decimal

from app import create_app
from models import Cliente, Compra, Pagamento, agora, db

EXEMPLOS = [
    # nome, telefone, [(dias atrás, valor, descrição)], [(dias atrás, valor)]
    ("Ana Souza", "11912345678", [(3, "18.50", "pão e leite"), (1, "32.00", "frios")], []),
    ("Carlos Lima", None, [(42, "55.00", "compras do mês"), (20, "12.00", "pão")], [(15, "30.00")]),
    ("Dona Cida", "11998765432", [(10, "27.90", "arroz e óleo")], [(2, "27.90")]),
    ("João Pereira", None, [(35, "40.00", "bebidas"), (5, "15.50", None)], []),
    ("Marcos Silva", "11955554444", [(6, "22.00", "pão e mortadela")], [(1, "10.00")]),
]


def main():
    app = create_app()
    with app.app_context():
        if Cliente.query.count():
            print("Já existem clientes no banco. Nada foi alterado.")
            return
        hoje = agora()
        for nome, telefone, compras, pagamentos in EXEMPLOS:
            cliente = Cliente(nome=nome, telefone=telefone, data_cadastro=hoje - timedelta(days=60))
            db.session.add(cliente)
            for dias, valor, descricao in compras:
                db.session.add(Compra(cliente=cliente, valor=Decimal(valor), descricao=descricao,
                                      data=hoje - timedelta(days=dias, hours=2)))
            for dias, valor in pagamentos:
                db.session.add(Pagamento(cliente=cliente, valor=Decimal(valor),
                                         data=hoje - timedelta(days=dias)))
        db.session.commit()
        print(f"{len(EXEMPLOS)} clientes fictícios criados.")


if __name__ == "__main__":
    main()
