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


# ---------------- Fluxos complementares (cobertura das demais telas) ----------------

def test_editar_cliente(logado, app, novo_cliente):
    with app.app_context():
        cid = novo_cliente("Ana").id
    logado.post(f"/clientes/{cid}/editar", data={"nome": "Ana Paula", "telefone": "11 98888-7777"})
    with app.app_context():
        c = db.session.get(Cliente, cid)
        assert c.nome == "Ana Paula" and c.telefone == "11988887777"


def test_inativar_cliente_bloqueia_novas_compras(logado, app, novo_cliente):
    with app.app_context():
        cid = novo_cliente().id
    logado.post(f"/clientes/{cid}/ativo")
    with app.app_context():
        assert db.session.get(Cliente, cid).ativo is False
    r = logado.post(f"/clientes/{cid}/compra", data={"valor": "10"}, follow_redirects=True)
    assert "Este cliente está inativo" in r.get_data(as_text=True)
    assert "Ana" not in logado.get("/").get_data(as_text=True)  # inativo some da lista padrão
    assert "Ana" in logado.get("/?inativos=1").get_data(as_text=True)


def test_excluir_pagamento_recalcula_saldo(logado, app, novo_cliente):
    with app.app_context():
        c = novo_cliente()
        db.session.add(Compra(cliente=c, valor=Decimal("30.00")))
        pagamento = Pagamento(cliente=c, valor=Decimal("10.00"))
        db.session.add(pagamento)
        db.session.commit()
        cid, pid = c.id, pagamento.id
    logado.post(f"/pagamentos/{pid}/excluir")
    with app.app_context():
        assert db.session.get(Cliente, cid).saldo == Decimal("30.00")


def test_painel_mostra_taxa_e_navega_entre_meses(logado, app, novo_cliente):
    with app.app_context():
        c = novo_cliente()
        db.session.add_all([Compra(cliente=c, valor=Decimal("100.00")),
                            Pagamento(cliente=c, valor=Decimal("50.00"))])
        db.session.commit()
    html = logado.get("/painel").get_data(as_text=True)
    assert "50,0%" in html and "Taxa de recebimento" in html
    assert logado.get("/painel?mes=2020-01").status_code == 200
    assert logado.get("/painel?mes=invalido").status_code == 200


def test_backup_baixa_arquivo_do_banco(logado):
    r = logado.get("/backup")
    assert r.status_code == 200
    assert "attachment" in r.headers["Content-Disposition"]


def test_sair_encerra_a_sessao(logado):
    logado.post("/sair")
    r = logado.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_icone_e_manifesto_disponiveis(cliente_http):
    html = cliente_http.get("/login").get_data(as_text=True)
    assert 'rel="icon"' in html and 'rel="apple-touch-icon"' in html and 'rel="manifest"' in html
    for arquivo in ["icone.svg", "icone-192.png", "icone-512.png", "apple-touch-icon.png",
                    "manifest.webmanifest"]:
        assert cliente_http.get(f"/static/{arquivo}").status_code == 200


def test_pagamento_bloqueado_para_cliente_sem_divida(logado, app, novo_cliente):
    with app.app_context():
        cid = novo_cliente().id
    # Acesso direto pelo endereço (GET) volta para a ficha com aviso
    r = logado.get(f"/clientes/{cid}/pagamento", follow_redirects=True)
    assert "não tem dívida em aberto" in r.get_data(as_text=True)
    # Envio forçado (POST) também é recusado no servidor
    logado.post(f"/clientes/{cid}/pagamento", data={"valor": "10"})
    with app.app_context():
        assert Pagamento.query.count() == 0
