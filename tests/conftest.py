"""
Configuração compartilhada dos testes (fixtures do pytest).
Cada teste usa um banco SQLite temporário e isolado.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import routes  # noqa: E402
from app import create_app  # noqa: E402
from models import Cliente, Usuario, db  # noqa: E402

EMAIL = "dona@mercadinho.com"
SENHA = "senhaSegura123"


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'teste.db'}",
        "CAMINHO_BANCO": str(tmp_path / "teste.db"),
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        usuario = Usuario(nome="Proprietária", email=EMAIL)
        usuario.definir_senha(SENHA)
        db.session.add(usuario)
        db.session.commit()
    routes._tentativas.clear()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def cliente_http(app):
    return app.test_client()


@pytest.fixture
def logado(cliente_http):
    cliente_http.post("/login", data={"email": EMAIL, "senha": SENHA})
    return cliente_http


@pytest.fixture
def novo_cliente():
    """Retorna uma função que cria e grava um cliente (usar dentro de app_context)."""
    def _criar(nome="Ana"):
        cliente = Cliente(nome=nome)
        db.session.add(cliente)
        db.session.commit()
        return cliente
    return _criar
