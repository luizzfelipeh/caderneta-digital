"""
Formulários e validações (Flask-WTF / WTForms).

Toda entrada da usuária passa por aqui antes de chegar ao banco:
campos obrigatórios, tamanhos máximos, valor maior que zero e proteção CSRF.
"""
import re
from decimal import Decimal, InvalidOperation

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp, ValidationError

VALOR_MAXIMO = Decimal("100000.00")


def converter_valor(texto):
    """Converte '23,50', '1.234,56' ou '23.50' em Decimal('23.50').
    Retorna None se o texto não for um número válido."""
    if texto is None:
        return None
    texto = texto.strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None
    if not valor.is_finite():
        return None
    return valor.quantize(Decimal("0.01"))


class LoginForm(FlaskForm):
    email = StringField(
        "E-mail",
        validators=[
            DataRequired(message="Informe o e-mail."),
            Length(max=120),
            Regexp(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", message="E-mail inválido."),
        ],
    )
    senha = PasswordField("Senha", validators=[DataRequired(message="Informe a senha."), Length(max=128)])
    entrar = SubmitField("Entrar")


class ClienteForm(FlaskForm):
    nome = StringField(
        "Nome do cliente",
        validators=[DataRequired(message="Informe o nome."), Length(max=100, message="Máximo de 100 caracteres.")],
    )
    telefone = StringField("Telefone (opcional)", validators=[Optional(), Length(max=20)])
    confirmar_duplicado = BooleanField("Já existe um cliente com esse nome. Cadastrar mesmo assim?")
    salvar = SubmitField("Salvar")

    def validate_nome(self, campo):
        campo.data = " ".join(campo.data.split())  # remove espaços extras
        if not campo.data:
            raise ValidationError("Informe o nome.")

    def validate_telefone(self, campo):
        if not campo.data:
            campo.data = None
            return
        numeros = re.sub(r"\D", "", campo.data)
        if not 10 <= len(numeros) <= 11:
            raise ValidationError("Informe o telefone com DDD (10 ou 11 números).")
        campo.data = numeros


class LancamentoForm(FlaskForm):
    """Usado tanto para COMPRA quanto para PAGAMENTO."""

    valor = StringField("Valor (R$)", validators=[DataRequired(message="Informe o valor.")])
    descricao = StringField("Descrição (opcional)", validators=[Optional(), Length(max=200)])
    salvar = SubmitField("Salvar")

    def validate_valor(self, campo):
        valor = converter_valor(campo.data)
        if valor is None:
            raise ValidationError("Digite um valor válido, por exemplo 23,50.")
        if valor <= 0:
            raise ValidationError("O valor deve ser maior que zero.")
        if valor > VALOR_MAXIMO:
            raise ValidationError("Valor muito alto. Confira o número digitado.")
        self.valor_convertido = valor

