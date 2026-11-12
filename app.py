"""
Caderneta Digital - controle de fiado para o mercadinho.

Arquivo principal: cria a aplicação Flask, configura segurança, banco de dados
e login. Para rodar no computador:  python app.py
"""
import os
import secrets
import warnings
from datetime import timedelta

from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

from models import Usuario, db
from routes import _brl, bp

# O SQLite guarda decimais como texto/número; o aviso abaixo é esperado e inofensivo.
warnings.filterwarnings("ignore", message=".*does \\*not\\* support Decimal objects natively.*")

csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "main.login"
login_manager.login_message = "Faça login para acessar a Caderneta Digital."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"


@login_manager.user_loader
def carregar_usuario(usuario_id):
    return db.session.get(Usuario, int(usuario_id))


@event.listens_for(Engine, "connect")
def _ativar_chaves_estrangeiras(conexao, _registro):
    """Faz o SQLite respeitar as chaves estrangeiras (cliente_id)."""
    if conexao.__class__.__module__.startswith("sqlite3"):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _carregar_chave_secreta(pasta):
    """Usa a variável SECRET_KEY se existir; senão cria uma chave aleatória
    e guarda no arquivo instance/secret_key (fora do código-fonte)."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    arquivo = os.path.join(pasta, "secret_key")
    if not os.path.exists(arquivo):
        with open(arquivo, "w", encoding="utf-8") as f:
            f.write(secrets.token_hex(32))
    with open(arquivo, encoding="utf-8") as f:
        return f.read().strip()


def create_app(config_extra=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    caminho_banco = os.path.join(app.instance_path, "caderneta.db")
    app.config.update(
        SECRET_KEY=_carregar_chave_secreta(app.instance_path),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{caminho_banco}",
        CAMINHO_BANCO=caminho_banco,
        # Sessão: cookie protegido e com tempo de expiração
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SEGURO", "0") == "1",  # use 1 em produção (HTTPS)
        REMEMBER_COOKIE_HTTPONLY=True,
        WTF_CSRF_TIME_LIMIT=None,
    )
    if config_extra:
        app.config.update(config_extra)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    app.register_blueprint(bp)

    # Filtros usados nas telas
    app.jinja_env.filters["brl"] = _brl
    app.jinja_env.filters["data"] = lambda d: d.strftime("%d/%m/%Y") if d else ""
    app.jinja_env.filters["data_hora"] = lambda d: d.strftime("%d/%m/%Y %H:%M") if d else ""

    @app.after_request
    def cabecalhos_de_seguranca(resposta):
        # Política de conteúdo: só carrega scripts e estilos do próprio site
        resposta.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; "
            "script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'"
        )
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "same-origin"
        return resposta

    @app.errorhandler(404)
    def nao_encontrado(_erro):
        from flask import render_template
        return render_template("erro.html", mensagem="Página ou registro não encontrado."), 404

    @app.errorhandler(400)
    def requisicao_invalida(_erro):
        from flask import render_template
        return render_template(
            "erro.html",
            mensagem="Não foi possível concluir a ação. Volte e tente novamente.",
        ), 400

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    # debug=False por segurança; para ver erros detalhados use: set FLASK_DEBUG=1
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")
