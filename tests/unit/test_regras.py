"""
TESTES UNITÁRIOS: verificam regras isoladas do Model e dos formulários,
sem passar pelas rotas HTTP (cálculo do saldo, débito antigo, taxa,
conversão de valores, formatação e hash de senha).
"""
from datetime import timedelta
from decimal import Decimal

from conftest import EMAIL, SENHA
from forms import converter_valor
from models import Compra, Pagamento, Usuario, agora, db, taxa_recebimento
from routes import _brl

# ---------------- Regras de negócio (Model) ----------------

def test_saldo_e_compras_menos_pagamentos(app, novo_cliente):
    with app.app_context():
        c = novo_cliente()
        db.session.add_all([
            Compra(cliente=c, valor=Decimal("18.50")),
            Compra(cliente=c, valor=Decimal("32.00")),
            Pagamento(cliente=c, valor=Decimal("20.00")),
        ])
        db.session.commit()
        assert c.saldo == Decimal("30.50")


def test_debito_antigo_mais_de_30_dias(app, novo_cliente):
    with app.app_context():
        c = novo_cliente()
        hoje = agora()
        db.session.add_all([
            Compra(cliente=c, valor=Decimal("50.00"), data=hoje - timedelta(days=40)),
            Compra(cliente=c, valor=Decimal("10.00"), data=hoje - timedelta(days=2)),
        ])
        db.session.commit()
        assert c.tem_debito_antigo()
        # Pagando a compra antiga, sobra só a recente: não é mais débito antigo
        db.session.add(Pagamento(cliente=c, valor=Decimal("50.00")))
        db.session.commit()
        assert not c.tem_debito_antigo()
        assert c.devendo_desde().date() == (hoje - timedelta(days=2)).date()


def test_taxa_de_recebimento(app, novo_cliente):
    with app.app_context():
        c = novo_cliente()
        hoje = agora()
        db.session.add_all([
            Compra(cliente=c, valor=Decimal("400.00"), data=hoje),
            Pagamento(cliente=c, valor=Decimal("300.00"), data=hoje),
        ])
        db.session.commit()
        resultado = taxa_recebimento(hoje - timedelta(days=1), hoje + timedelta(days=1))
        assert resultado["taxa"] == Decimal("75.0")


def test_converter_valor_aceita_virgula():
    assert converter_valor("23,50") == Decimal("23.50")
    assert converter_valor("1.234,56") == Decimal("1234.56")
    assert converter_valor("abc") is None


def test_senha_guardada_com_hash(app):
    with app.app_context():
        usuario = Usuario.query.filter_by(email=EMAIL).first()
        assert SENHA not in usuario.senha_hash
        assert usuario.senha_hash.startswith("scrypt:")


def test_cliente_quitado_nao_tem_devendo_desde(app, novo_cliente):
    with app.app_context():
        c = novo_cliente()
        db.session.add_all([
            Compra(cliente=c, valor=Decimal("40.00"), data=agora() - timedelta(days=50)),
            Pagamento(cliente=c, valor=Decimal("40.00")),
        ])
        db.session.commit()
        assert c.saldo == Decimal("0.00")
        assert c.devendo_desde() is None
        assert not c.tem_debito_antigo()


def test_converter_valor_rejeita_entradas_invalidas():
    assert converter_valor("") is None
    assert converter_valor("NaN") is None
    assert converter_valor("R$ 10,00") == Decimal("10.00")


def test_formatacao_em_reais():
    assert _brl(Decimal("1234.5")) == "1.234,50"
    assert _brl(Decimal("0")) == "0,00"
