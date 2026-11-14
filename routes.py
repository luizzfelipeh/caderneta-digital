"""
Camada CONTROLLER da Caderneta Digital (rotas do Flask).

Cada rota recebe a ação da usuária, confere o login, valida o formulário,
chama as regras do Model e escolhe qual tela (View) mostrar.
"""
import time
from datetime import datetime

from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, send_file, session, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func

from forms import ClienteForm, LancamentoForm, LoginForm
from models import (Cliente, Compra, Pagamento, Usuario, agora, db, resumo_geral,
                    taxa_recebimento)

bp = Blueprint("main", __name__)

# ---------------- Proteção contra tentativas de senha (força bruta) ----------------
MAX_TENTATIVAS = 5
BLOQUEIO_SEGUNDOS = 5 * 60
_tentativas = {}  # email -> [quantidade, momento_da_primeira_falha]


def _login_bloqueado(email):
    registro = _tentativas.get(email)
    if not registro:
        return False
    quantidade, inicio = registro
    if time.time() - inicio > BLOQUEIO_SEGUNDOS:
        _tentativas.pop(email, None)
        return False
    return quantidade >= MAX_TENTATIVAS


def _registrar_falha(email):
    quantidade, inicio = _tentativas.get(email, [0, time.time()])
    _tentativas[email] = [quantidade + 1, inicio]


def _buscar_cliente(cliente_id):
    cliente = db.session.get(Cliente, cliente_id)
    if cliente is None:
        abort(404)
    return cliente


def _nome_duplicado(nome, ignorar_id=None):
    consulta = Cliente.query.filter(func.lower(Cliente.nome) == nome.lower())
    if ignorar_id:
        consulta = consulta.filter(Cliente.id != ignorar_id)
    return consulta.first() is not None


# ---------------- Login / logout ----------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if _login_bloqueado(email):
            flash("Muitas tentativas erradas. Aguarde 5 minutos e tente de novo.", "danger")
            return render_template("login.html", form=form), 429
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.verificar_senha(form.senha.data):
            _tentativas.pop(email, None)
            session.clear()  # nova sessão a cada login
            login_user(usuario)
            session.permanent = True
            return redirect(url_for("main.inicio"))
        _registrar_falha(email)
        # Mensagem genérica: não revela se o e-mail existe
        flash("E-mail ou senha incorretos.", "danger")
    return render_template("login.html", form=form)


@bp.route("/sair", methods=["POST"])
@login_required
def sair():
    logout_user()
    session.clear()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("main.login"))


# ---------------- Tela inicial: lista de clientes ----------------

@bp.route("/")
@login_required
def inicio():
    busca = request.args.get("q", "").strip()[:100]
    mostrar_inativos = request.args.get("inativos") == "1"

    consulta = Cliente.query
    if not mostrar_inativos:
        consulta = consulta.filter_by(ativo=True)
    if busca:
        # Consulta parametrizada pelo SQLAlchemy (protege contra SQL Injection)
        consulta = consulta.filter(Cliente.nome.ilike(f"%{busca}%"))
    clientes = consulta.order_by(Cliente.nome).all()

    resumo = resumo_geral(Cliente.query.all())
    return render_template(
        "inicio.html", clientes=clientes, busca=busca,
        mostrar_inativos=mostrar_inativos, resumo=resumo, referencia=agora(),
    )


# ---------------- Clientes ----------------

@bp.route("/clientes/novo", methods=["GET", "POST"])
@login_required
def novo_cliente():
    form = ClienteForm()
    duplicado = False
    if form.validate_on_submit():
        duplicado = _nome_duplicado(form.nome.data)
        if duplicado and not form.confirmar_duplicado.data:
            flash("Já existe um cliente com esse nome. Use sobrenome/apelido ou confirme abaixo.", "warning")
        else:
            cliente = Cliente(nome=form.nome.data, telefone=form.telefone.data)
            db.session.add(cliente)
            db.session.commit()
            flash(f"Cliente {cliente.nome} cadastrado.", "success")
            return redirect(url_for("main.ficha_cliente", cliente_id=cliente.id))
    return render_template("cliente_form.html", form=form, titulo="Novo cliente", duplicado=duplicado)


@bp.route("/clientes/<int:cliente_id>")
@login_required
def ficha_cliente(cliente_id):
    cliente = _buscar_cliente(cliente_id)
    return render_template("cliente.html", cliente=cliente, referencia=agora())


@bp.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_required
def editar_cliente(cliente_id):
    cliente = _buscar_cliente(cliente_id)
    form = ClienteForm(obj=cliente)
    duplicado = False
    if form.validate_on_submit():
        duplicado = _nome_duplicado(form.nome.data, ignorar_id=cliente.id)
        if duplicado and not form.confirmar_duplicado.data:
            flash("Já existe outro cliente com esse nome. Confirme abaixo para salvar.", "warning")
        else:
            cliente.nome = form.nome.data
            cliente.telefone = form.telefone.data
            db.session.commit()
            flash("Dados do cliente atualizados.", "success")
            return redirect(url_for("main.ficha_cliente", cliente_id=cliente.id))
    return render_template("cliente_form.html", form=form, titulo="Editar cliente",
                           duplicado=duplicado, cliente=cliente)


@bp.route("/clientes/<int:cliente_id>/ativo", methods=["POST"])
@login_required
def alternar_ativo(cliente_id):
    cliente = _buscar_cliente(cliente_id)
    cliente.ativo = not cliente.ativo
    db.session.commit()
    flash("Cliente reativado." if cliente.ativo else "Cliente inativado (o histórico foi mantido).", "info")
    return redirect(url_for("main.ficha_cliente", cliente_id=cliente.id))


# ---------------- Lançamentos: compra e pagamento ----------------

@bp.route("/clientes/<int:cliente_id>/compra", methods=["GET", "POST"])
@login_required
def nova_compra(cliente_id):
    cliente = _buscar_cliente(cliente_id)
    if not cliente.ativo:
        flash("Este cliente está inativo. Reative-o para lançar compras.", "warning")
        return redirect(url_for("main.ficha_cliente", cliente_id=cliente.id))
    form = LancamentoForm()
    if form.validate_on_submit():
        compra = Compra(cliente=cliente, valor=form.valor_convertido,
                        descricao=(form.descricao.data or "").strip() or None, data=agora())
        db.session.add(compra)
        db.session.commit()
        flash(f"Compra de R$ {_brl(compra.valor)} registrada.", "success")
        return redirect(url_for("main.ficha_cliente", cliente_id=cliente.id))
    return render_template("lancamento_form.html", form=form, cliente=cliente, tipo="compra")


@bp.route("/clientes/<int:cliente_id>/pagamento", methods=["GET", "POST"])
@login_required
def novo_pagamento(cliente_id):
    cliente = _buscar_cliente(cliente_id)
    # Bloqueio no servidor: mesmo acessando o endereço direto, não é possível
    # registrar pagamento para cliente sem dívida (o botão já fica desativado na tela).
    if cliente.saldo <= 0:
        flash("Este cliente não tem dívida em aberto.", "info")
        return redirect(url_for("main.ficha_cliente", cliente_id=cliente.id))
    form = LancamentoForm()
    if form.validate_on_submit():
        erro = cliente.validar_pagamento(form.valor_convertido)
        if erro:
            form.valor.errors.append(f"{erro} (Saldo atual: R$ {_brl(cliente.saldo)})")
        else:
            pagamento = Pagamento(cliente=cliente, valor=form.valor_convertido, data=agora())
            db.session.add(pagamento)
            db.session.commit()
            flash(f"Pagamento de R$ {_brl(pagamento.valor)} registrado.", "success")
            return redirect(url_for("main.ficha_cliente", cliente_id=cliente.id))
    return render_template("lancamento_form.html", form=form, cliente=cliente, tipo="pagamento")


@bp.route("/compras/<int:compra_id>/excluir", methods=["POST"])
@login_required
def excluir_compra(compra_id):
    compra = db.session.get(Compra, compra_id) or abort(404)
    cliente_id = compra.cliente_id
    db.session.delete(compra)
    db.session.commit()
    flash("Compra excluída. O saldo foi recalculado.", "info")
    return redirect(url_for("main.ficha_cliente", cliente_id=cliente_id))


@bp.route("/pagamentos/<int:pagamento_id>/excluir", methods=["POST"])
@login_required
def excluir_pagamento(pagamento_id):
    pagamento = db.session.get(Pagamento, pagamento_id) or abort(404)
    cliente_id = pagamento.cliente_id
    db.session.delete(pagamento)
    db.session.commit()
    flash("Pagamento excluído. O saldo foi recalculado.", "info")
    return redirect(url_for("main.ficha_cliente", cliente_id=cliente_id))


# ---------------- Painel (indicadores) ----------------

def _mes_de_referencia(texto):
    """Lê '2026-11' da URL; se inválido, usa o mês atual."""
    try:
        return datetime.strptime(texto, "%Y-%m")
    except (TypeError, ValueError):
        hoje = agora()
        return datetime(hoje.year, hoje.month, 1)


def _somar_meses(data, meses):
    ano = data.year + (data.month - 1 + meses) // 12
    mes = (data.month - 1 + meses) % 12 + 1
    return datetime(ano, mes, 1)


@bp.route("/painel")
@login_required
def painel():
    inicio_mes = _mes_de_referencia(request.args.get("mes"))
    fim_mes = _somar_meses(inicio_mes, 1)
    resumo = resumo_geral(Cliente.query.all())
    indicador = taxa_recebimento(inicio_mes, fim_mes)
    return render_template(
        "painel.html", resumo=resumo, indicador=indicador, inicio_mes=inicio_mes,
        mes_anterior=_somar_meses(inicio_mes, -1), mes_seguinte=fim_mes,
        referencia=agora(),
    )


@bp.route("/backup")
@login_required
def backup():
    """Baixa uma cópia do arquivo do banco de dados (cópia de segurança)."""
    caminho = current_app.config["CAMINHO_BANCO"]
    nome = f"caderneta_backup_{agora():%Y-%m-%d_%H%M}.db"
    return send_file(caminho, as_attachment=True, download_name=nome)


def _brl(valor):
    """Formata 1234.5 como '1.234,50'."""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
