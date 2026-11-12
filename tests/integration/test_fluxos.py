"""
TESTES DE INTEGRAÇÃO: verificam o sistema funcionando junto (rotas Flask +
formulários + regras + banco SQLite), simulando a proprietária usando as telas:
login, segurança, cadastro, compra, pagamento, exclusão e busca.
"""
from decimal import Decimal

from app import create_app
from conftest import EMAIL, SENHA
from models import Cliente, Compra, Pagamento, db


def test_rotas_exigem_login(cliente_http):
    for rota in ["/", "/painel", "/clientes/novo", "/backup"]:
        resposta = cliente_http.get(rota)
        assert resposta.status_code == 302
        assert "/login" in resposta.headers["Location"]


def test_login_errado_e_bloqueio(cliente_http):
    for _ in range(5):
        r = cliente_http.post("/login", data={"email": EMAIL, "senha": "errada"})
        assert "E-mail ou senha incorretos" in r.get_data(as_text=True)
    r = cliente_http.post("/login", data={"email": EMAIL, "senha": SENHA})
    assert r.status_code == 429  # bloqueado mesmo com a senha certa


def test_csrf_bloqueia_post_sem_token(tmp_path):
    app = create_app({"TESTING": True,
                      "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'csrf.db'}"})
    r = app.test_client().post("/login", data={"email": EMAIL, "senha": SENHA})
    assert r.status_code == 400


def test_xss_e_escapado(logado, app):
    logado.post("/clientes/novo", data={"nome": "<script>alert(1)</script>"})
    html = logado.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_cabecalhos_de_seguranca(logado):
    r = logado.get("/")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_pagina_inexistente_sem_detalhes_tecnicos(logado):
    r = logado.get("/clientes/99999")
    assert r.status_code == 404
    assert "Traceback" not in r.get_data(as_text=True)


# ---------------- Fluxos (Controller) ----------------

def test_fluxo_compra_e_pagamento(logado, app):
    logado.post("/clientes/novo", data={"nome": "Carlos", "telefone": "(11) 91234-5678"})
    with app.app_context():
        c = Cliente.query.filter_by(nome="Carlos").first()
        assert c.telefone == "11912345678"
        cid = c.id
    r = logado.post(f"/clientes/{cid}/compra", data={"valor": "23,50", "descricao": "pão"},
                    follow_redirects=True)
    assert "R$ 23,50" in r.get_data(as_text=True)
    logado.post(f"/clientes/{cid}/pagamento", data={"valor": "10"})
    with app.app_context():
        assert db.session.get(Cliente, cid).saldo == Decimal("13.50")


def test_pagamento_maior_que_saldo_e_recusado(logado, app, novo_cliente):
    with app.app_context():
        c = novo_cliente()
        db.session.add(Compra(cliente=c, valor=Decimal("20.00")))
        db.session.commit()
        cid = c.id
    r = logado.post(f"/clientes/{cid}/pagamento", data={"valor": "50"})
    assert "não pode ser maior que o saldo" in r.get_data(as_text=True)
    with app.app_context():
        assert Pagamento.query.count() == 0


def test_valor_zero_ou_negativo_e_recusado(logado, app, novo_cliente):
    with app.app_context():
        cid = novo_cliente().id
    for valor in ["0", "-5", "abc"]:
        logado.post(f"/clientes/{cid}/compra", data={"valor": valor})
    with app.app_context():
        assert Compra.query.count() == 0


def test_nome_duplicado_pede_confirmacao(logado, app):
    logado.post("/clientes/novo", data={"nome": "Maria"})
    r = logado.post("/clientes/novo", data={"nome": "maria"})
    assert "Já existe um cliente com esse nome" in r.get_data(as_text=True)
    with app.app_context():
        assert Cliente.query.count() == 1
    logado.post("/clientes/novo", data={"nome": "maria", "confirmar_duplicado": "y"})
    with app.app_context():
        assert Cliente.query.count() == 2


def test_excluir_compra_recalcula_saldo(logado, app, novo_cliente):
    with app.app_context():
        c = novo_cliente()
        compra = Compra(cliente=c, valor=Decimal("15.00"))
        db.session.add(compra)
        db.session.commit()
        cid, compra_id = c.id, compra.id
    logado.post(f"/compras/{compra_id}/excluir")
    with app.app_context():
        assert db.session.get(Cliente, cid).saldo == Decimal("0.00")


def test_busca_por_nome(logado, app, novo_cliente):
    with app.app_context():
        novo_cliente("Ana Souza")
        novo_cliente("Bruno Costa")
    html = logado.get("/?q=souza").get_data(as_text=True)
    assert "Ana Souza" in html and "Bruno Costa" not in html
