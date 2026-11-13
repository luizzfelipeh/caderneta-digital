# Publicação no PythonAnywhere (plano gratuito)

Guia para colocar a Caderneta Digital na internet, acessível pelo celular da proprietária,
em `https://SEU-USUARIO.pythonanywhere.com`.

> Plano gratuito: 1 aplicação web, 512 MiB de disco e expiração em 1 mês
> (é preciso clicar em **"Run until 1 month from today"** na aba **Web** para renovar).

## 1. Criar a conta
1. Acesse **pythonanywhere.com** → **Pricing & signup** → **Create a Beginner account**.
2. Confirme o e-mail.

## 2. Baixar o código do GitHub
Na aba **Consoles**, abra um **Bash** e rode:

```bash
git clone https://github.com/luizzfelipeh/Caderneta-digital.git
cd Caderneta-digital
mkvirtualenv --python=/usr/bin/python3.12 caderneta
pip install -r requirements.txt
python -m pytest
```

(Os testes devem passar também no servidor: isso comprova a portabilidade.)

## 3. Criar o usuário da proprietária
Ainda no console Bash:

```bash
python criar_usuario.py
```

Use o e-mail e uma senha **escolhida pela própria proprietária** (no mínimo 8 caracteres).
Para demonstração/validação com dados fictícios, rode também `python dados_exemplo.py`.

## 4. Criar a aplicação web
1. Aba **Web** → **Add a new web app** → **Next**.
2. Escolha **Manual configuration** (não escolha "Flask") → **Python 3.12** → **Next**.
3. Na mesma aba **Web**, preencha:
   - **Source code:** `/home/SEU-USUARIO/Caderneta-digital`
   - **Working directory:** `/home/SEU-USUARIO/Caderneta-digital`
   - **Virtualenv:** `/home/SEU-USUARIO/.virtualenvs/caderneta`
4. Em **Static files**, adicione:
   - **URL:** `/static/`
   - **Directory:** `/home/SEU-USUARIO/Caderneta-digital/static`
5. Em **Security**, ative **Force HTTPS**.

## 5. Configurar o arquivo WSGI
Na aba **Web**, clique no link do **WSGI configuration file**, apague todo o conteúdo e cole:

```python
import os
import sys

caminho = "/home/SEU-USUARIO/Caderneta-digital"
if caminho not in sys.path:
    sys.path.insert(0, caminho)

os.environ["COOKIE_SEGURO"] = "1"  # cookie de sessão só por HTTPS

from wsgi import application  # noqa: E402,F401
```

Salve (**Save**).

## 6. Iniciar
Na aba **Web**, clique em **Reload**. Acesse `https://SEU-USUARIO.pythonanywhere.com`.

## 7. Atalho na tela inicial do celular
- **Android (Chrome):** menu ⋮ → **Adicionar à tela inicial**.
- **iPhone (Safari):** botão Compartilhar → **Adicionar à Tela de Início**.

O ícone da Caderneta Digital aparecerá como um aplicativo.

## Atualizar o sistema depois de um novo merge
```bash
cd ~/Caderneta-digital
git pull
workon caderneta
pip install -r requirements.txt
```
Depois clique em **Reload** na aba **Web**. O banco (`instance/caderneta.db`) não é afetado.

## Backup
No sistema, **Painel → Baixar cópia de segurança (backup)**, ou na aba **Files** do
PythonAnywhere, baixe `Caderneta-digital/instance/caderneta.db`.
