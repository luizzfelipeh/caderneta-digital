# 📒 Caderneta Digital

[![CI](https://github.com/luizzfelipeh/Caderneta-digital/actions/workflows/ci.yml/badge.svg)](https://github.com/luizzfelipeh/Caderneta-digital/actions/workflows/ci.yml)

Sistema web para controle de vendas fiadas de um mercadinho de bairro.
Projeto de Software – ADS (Experiências Práticas – DreamShaper).

**Tecnologias:** Python 3.12 · Flask · Flask-SQLAlchemy · Flask-Login · Flask-WTF · Bootstrap 5.3 · SQLite · pytest
**Arquitetura:** monolito em camadas, padrão MVC

---

## Como rodar no seu computador (Windows + VS Code)

1. **Extraia** o arquivo `caderneta_digital.zip` (por exemplo em `Documentos`).
2. No **VS Code**: `Arquivo > Abrir Pasta...` e escolha a pasta `caderneta_digital`.
3. Abra o terminal: `Terminal > Novo Terminal`.
4. Crie e ative o ambiente virtual (só na primeira vez):

   ```
   python -m venv venv
   venv\Scripts\activate
   ```

   Vai aparecer `(venv)` no começo da linha do terminal.

   > Se aparecer erro de "execução de scripts desabilitada", rode antes:
   > `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e confirme com `S`.

5. Instale as bibliotecas (só na primeira vez):

   ```
   pip install -r requirements.txt
   ```

6. Crie o login da proprietária (só na primeira vez):

   ```
   python criar_usuario.py
   ```

7. *(Opcional)* Crie clientes **fictícios** para testar e tirar prints:

   ```
   python dados_exemplo.py
   ```

8. Rode o sistema:

   ```
   python app.py
   ```

9. Abra no navegador: **http://127.0.0.1:5000**
   Para parar o sistema, volte ao terminal e aperte `Ctrl + C`.

Nas próximas vezes, basta: abrir a pasta no VS Code → `venv\Scripts\activate` → `python app.py`.

### Ver como fica no celular (pelo computador)
No Chrome, aperte `F12` e depois `Ctrl + Shift + M` para simular a tela de um celular.

### Rodar os testes automáticos

```
python -m pytest                    # todos os testes
python -m pytest tests/unit         # só os unitários (regras do Model)
python -m pytest tests/integration  # só os de integração (telas + banco)
python -m pytest --cov --cov-report=term-missing   # com análise de cobertura
```

Os mesmos testes rodam automaticamente no GitHub a cada envio (Integração Contínua,
arquivo `.github/workflows/ci.yml`).

---

## Publicação na internet

O passo a passo para publicar no PythonAnywhere (plano gratuito) está em
[DEPLOY_PYTHONANYWHERE.md](DEPLOY_PYTHONANYWHERE.md).

## Estrutura do projeto (MVC)

| Arquivo / pasta | Camada | O que faz |
|---|---|---|
| `models.py` | Model | Entidades (Usuario, Cliente, Compra, Pagamento) e regras: saldo, débitos +30 dias, taxa de recebimento |
| `routes.py` | Controller | Rotas: login, clientes, compras, pagamentos, painel, backup |
| `forms.py` | Controller | Formulários e validações (valor > 0, telefone, CSRF) |
| `templates/` | View | Telas HTML |
| `static/` | View | Estilos (Bootstrap + style.css) e app.js |
| `app.py` | — | Cria a aplicação e configura segurança |
| `criar_usuario.py` | — | Cria ou troca a senha da proprietária |
| `dados_exemplo.py` | — | Dados fictícios para demonstração |
| `tests/unit/` | — | Testes unitários (regras de negócio) |
| `tests/integration/` | — | Testes de integração (rotas + banco) |
| `.github/workflows/ci.yml` | — | Integração Contínua no GitHub Actions |
| `instance/` | — | Criada automaticamente: banco `caderneta.db` e chave secreta (**não compartilhe**) |

## Segurança implementada (OWASP Top 10)

- Senha com **hash scrypt** (nunca em texto puro) e bloqueio de 5 minutos após 5 tentativas erradas
- Todas as telas exigem **login**; sessão expira em 12 horas; cookie `HttpOnly` e `SameSite`
- **SQL Injection:** consultas parametrizadas pelo SQLAlchemy
- **XSS:** escape automático do Jinja2 + Content-Security-Policy
- **CSRF:** token em todos os formulários (Flask-WTF)
- Validação de todas as entradas no servidor; mensagens de erro sem detalhes técnicos

## Acessibilidade

Fonte base de 18 px · botões com no mínimo 48 px de altura · contraste mínimo de 4,5:1 (WCAG 2.1 AA) ·
rótulos em todos os campos · foco visível · mensagens anunciadas para leitores de tela · valores com texto ("Deve", "Em dia").
