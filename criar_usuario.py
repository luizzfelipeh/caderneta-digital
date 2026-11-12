"""
Cria (ou troca a senha de) a conta de acesso da proprietária.

Uso, no terminal, dentro da pasta do projeto:
    python criar_usuario.py
"""
from getpass import getpass

from app import create_app
from models import Usuario, db

TAMANHO_MINIMO_SENHA = 8


def main():
    app = create_app()
    with app.app_context():
        print("=== Caderneta Digital: conta de acesso ===")
        nome = input("Nome da proprietária: ").strip()
        email = input("E-mail (usado no login): ").strip().lower()
        if not nome or "@" not in email:
            print("Nome e e-mail válidos são obrigatórios.")
            return

        while True:
            senha = getpass(f"Senha (mínimo {TAMANHO_MINIMO_SENHA} caracteres, não aparece ao digitar): ")
            if len(senha) < TAMANHO_MINIMO_SENHA:
                print("Senha muito curta. Tente novamente.")
                continue
            if getpass("Repita a senha: ") != senha:
                print("As senhas não conferem. Tente novamente.")
                continue
            break

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            usuario.nome = nome
            usuario.definir_senha(senha)
            print("Senha atualizada.")
        else:
            usuario = Usuario(nome=nome, email=email)
            usuario.definir_senha(senha)
            db.session.add(usuario)
            print("Conta criada.")
        db.session.commit()
        print("Pronto! Agora rode:  python app.py")


if __name__ == "__main__":
    main()
