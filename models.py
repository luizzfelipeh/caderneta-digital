"""
Camada MODEL da Caderneta Digital.

Aqui ficam as entidades do banco de dados (Usuario, Cliente, Compra, Pagamento)
e as REGRAS DE NEGÓCIO do fiado: cálculo do saldo, débitos antigos e taxa de
recebimento. Todas as telas usam estas mesmas regras, então o valor exibido
é sempre o mesmo em qualquer lugar do sistema.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")
DIAS_DEBITO_ANTIGO = 30
ZERO = Decimal("0.00")


def agora():
    """Data e hora atual no horário de Brasília (sem fuso, para gravar no SQLite)."""
    return datetime.now(FUSO_HORARIO).replace(tzinfo=None, microsecond=0)


def _dinheiro(valor):
    """Garante que o valor seja Decimal com 2 casas (evita erro de arredondamento)."""
    return Decimal(str(valor or 0)).quantize(Decimal("0.01"))


class Usuario(UserMixin, db.Model):
    """Conta de acesso da proprietária. A senha NUNCA é gravada em texto puro."""

    __tablename__ = "usuario"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    data_criacao = db.Column(db.DateTime, nullable=False, default=agora)

    def definir_senha(self, senha):
        # Hash robusto com o algoritmo scrypt (Werkzeug)
        self.senha_hash = generate_password_hash(senha, method="scrypt")

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class Cliente(db.Model):
    """Pessoa que compra fiado no mercadinho."""

    __tablename__ = "cliente"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, index=True)
    telefone = db.Column(db.String(20), nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    data_cadastro = db.Column(db.DateTime, nullable=False, default=agora)

    # 1 cliente -> N compras / N pagamentos
    compras = db.relationship(
        "Compra", back_populates="cliente", lazy="selectin",
        order_by="Compra.data", cascade="all, delete-orphan",
    )
    pagamentos = db.relationship(
        "Pagamento", back_populates="cliente", lazy="selectin",
        order_by="Pagamento.data", cascade="all, delete-orphan",
    )

    # ---------------- Regras de negócio ----------------

    @property
    def total_compras(self):
        return sum((_dinheiro(c.valor) for c in self.compras), ZERO)

    @property
    def total_pagamentos(self):
        return sum((_dinheiro(p.valor) for p in self.pagamentos), ZERO)

    @property
    def saldo(self):
        """Saldo devedor = soma das compras - soma dos pagamentos.
        É sempre CALCULADO, nunca digitado, para não ficar diferente do histórico."""
        return self.total_compras - self.total_pagamentos

    def devendo_desde(self):
        """Data da compra mais antiga que ainda não foi paga.

        Os pagamentos abatem as compras da mais antiga para a mais nova
        (como acontece na prática). Retorna None se o cliente está em dia.
        """
        if self.saldo <= ZERO:
            return None
        restante_pago = self.total_pagamentos
        for compra in sorted(self.compras, key=lambda c: c.data):
            valor = _dinheiro(compra.valor)
            if restante_pago >= valor:
                restante_pago -= valor
            else:
                return compra.data
        return None

    def tem_debito_antigo(self, referencia=None):
        """True se existe dívida em aberto há mais de 30 dias."""
        desde = self.devendo_desde()
        if desde is None:
            return False
        referencia = referencia or agora()
        return (referencia - desde) > timedelta(days=DIAS_DEBITO_ANTIGO)

    def historico(self):
        """Compras e pagamentos juntos, do mais recente para o mais antigo."""
        itens = [
            {"tipo": "compra", "id": c.id, "valor": _dinheiro(c.valor),
             "data": c.data, "descricao": c.descricao}
            for c in self.compras
        ] + [
            {"tipo": "pagamento", "id": p.id, "valor": _dinheiro(p.valor),
             "data": p.data, "descricao": None}
            for p in self.pagamentos
        ]
        return sorted(itens, key=lambda i: (i["data"], i["tipo"]), reverse=True)


class Compra(db.Model):
    """Uma compra fiada (substitui cada anotação do caderno)."""

    __tablename__ = "compra"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False, index=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data = db.Column(db.DateTime, nullable=False, default=agora)
    descricao = db.Column(db.String(200), nullable=True)

    cliente = db.relationship("Cliente", back_populates="compras")


class Pagamento(db.Model):
    """Um pagamento (total ou parcial) feito pelo cliente."""

    __tablename__ = "pagamento"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False, index=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data = db.Column(db.DateTime, nullable=False, default=agora)

    cliente = db.relationship("Cliente", back_populates="pagamentos")


# ---------------- Indicadores do painel ----------------

def resumo_geral(clientes, referencia=None):
    """Total a receber, devedores e clientes com débito antigo."""
    referencia = referencia or agora()
    devedores = [c for c in clientes if c.saldo > ZERO]
    antigos = [c for c in devedores if c.tem_debito_antigo(referencia)]
    return {
        "total_a_receber": sum((c.saldo for c in devedores), ZERO),
        "devedores": sorted(devedores, key=lambda c: c.saldo, reverse=True),
        "debitos_antigos": sorted(antigos, key=lambda c: c.devendo_desde()),
    }


def taxa_recebimento(inicio, fim):
    """Indicador 1 do projeto: (valor recebido / valor vendido fiado) x 100 no período."""
    vendido = sum(
        (_dinheiro(c.valor) for c in Compra.query.filter(Compra.data >= inicio, Compra.data < fim)),
        ZERO,
    )
    recebido = sum(
        (_dinheiro(p.valor) for p in Pagamento.query.filter(Pagamento.data >= inicio, Pagamento.data < fim)),
        ZERO,
    )
    taxa = None
    if vendido > ZERO:
        taxa = (recebido / vendido * 100).quantize(Decimal("0.1"))
    return {"vendido": vendido, "recebido": recebido, "taxa": taxa}
