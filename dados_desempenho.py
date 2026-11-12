"""
Gera um volume FICTÍCIO fixo para o teste de desempenho (RNF03):
50 clientes e 500 compras (10 por cliente), sempre com os mesmos valores.

Uso (em um banco de testes, sem dados reais):  python dados_desempenho.py
"""
import random
from datetime import timedelta
from decimal import Decimal

from app import create_app
from models import Cliente, Compra, Pagamento, agora, db


def main():
    app = create_app()
    with app.app_context():
        if Cliente.query.count():
            print("Já existem clientes no banco. Use um banco vazio para o teste de desempenho.")
            return
        random.seed(2026)  # mesma semente = mesmos dados em todas as medições
        hoje = agora()
        for i in range(1, 51):
            cliente = Cliente(nome=f"Cliente Teste {i:02d}")
            db.session.add(cliente)
            for _ in range(10):
                db.session.add(Compra(
                    cliente=cliente,
                    valor=Decimal(random.randint(500, 6000)) / 100,
                    data=hoje - timedelta(days=random.randint(0, 60)),
                ))
            db.session.add(Pagamento(cliente=cliente, valor=Decimal("20.00"),
                                     data=hoje - timedelta(days=5)))
        db.session.commit()
        print("50 clientes e 500 compras fictícias criados.")


if __name__ == "__main__":
    main()
