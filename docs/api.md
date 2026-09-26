# Documentação da API do Oráculo RAG

A API do Oráculo expõe o pipeline RAG (Retrieval-Augmented Generation) através de endpoints HTTP utilizando FastAPI. Ela possui autenticação baseada em JWT (Bearer Token) e utiliza um banco de dados SQLite por padrão (via SQLAlchemy) para gerenciar os usuários.

## 🚀 Tecnologias Utilizadas

- **FastAPI**: Framework web rápido e moderno.
- **SQLAlchemy + Alembic**: ORM e controle de migrações de banco de dados.
- **JWT (python-jose)**: Geração e validação de tokens Bearer.
- **Bcrypt (passlib)**: Hashing seguro de senhas.
- **Pydantic**: Validação de dados (Schemas).

---

## 🛠️ Configuração e Execução

### 1. Variáveis de Ambiente

Copie o arquivo `.env.exemplo` para `.env` e ajuste as variáveis. Para a API, as configurações mais importantes são:

```env
SECRET_KEY=sua_chave_secreta_aqui
DATABASE_URL=sqlite:///./oraculo.db
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 2. Configurar o Banco de Dados

Antes de rodar a API pela primeira vez, execute as migrações do banco de dados (Alembic) para criar as tabelas necessárias:

```bash
# Com o ambiente virtual ativado:
alembic upgrade head
```

### 3. Popular o Banco de Dados (Seeder)

Para testes e uso inicial, o projeto possui um script de seeder que cria um usuário administrador padrão (`admin@oraculo.com` / `admin123`). Após rodar as migrações, execute:

```bash
python seed.py
```

### 4. Rodar a API

Inicie o servidor de desenvolvimento utilizando o Uvicorn:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Acesse a documentação interativa da API (Swagger UI) em:
[http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📚 Endpoints

### Autenticação (`/auth`)

#### 1. Criar Usuário (Register)
- **Método:** `POST`
- **Rota:** `/auth/register`
- **Descrição:** Registra um novo usuário no sistema.
- **Corpo da Requisição (JSON):**
  ```json
  {
    "email": "usuario@exemplo.com",
    "password": "sua_senha_segura"
  }
  ```
- **Resposta de Sucesso (201):**
  ```json
  {
    "id": 1,
    "email": "usuario@exemplo.com",
    "is_active": true
  }
  ```

#### 2. Fazer Login
- **Método:** `POST`
- **Rota:** `/auth/login`
- **Descrição:** Autentica um usuário e retorna um token JWT. O FastAPI utiliza o padrão `OAuth2PasswordRequestForm`, portanto os dados devem ser enviados como `application/x-www-form-urlencoded`.
- **Corpo da Requisição (Form Data):**
  - `username`: usuario@exemplo.com
  - `password`: sua_senha_segura
- **Resposta de Sucesso (200):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "token_type": "bearer"
  }
  ```

---

### Perguntas e Respostas (`/qa`)

#### 1. Fazer uma Pergunta (Ask)
- **Método:** `POST`
- **Rota:** `/qa/ask`
- **Descrição:** Recebe uma pergunta, executa o fluxo RAG e retorna a resposta da LLM junto com as fontes recuperadas.
- **Autenticação Necessária:** Sim (Bearer Token no cabeçalho `Authorization: Bearer <token>`).
- **Corpo da Requisição (JSON):**
  ```json
  {
    "question": "O que é o Oráculo?",
    "provider": "openrouter",
    "model": "openai/gpt-4.1-mini",
    "top_k": 3,
    "retriever_mode": "hybrid"
  }
  ```
  *(Nota: `provider`, `model`, `top_k` e `retriever_mode` são opcionais. O modo pode ser `bm25`, `vector` ou `hybrid`; se omitido, será usado `RETRIEVER_MODE` do arquivo `.env`.)*
- **Resposta de Sucesso (200):**
  ```json
  {
    "question": "O que é o Oráculo?",
    "answer": "O Oráculo é um sistema RAG...",
    "retriever_mode": "hybrid",
    "sources": [
      {
        "source_path": "caminho/do/documento.pdf",
        "score": 14.53,
        "page_start": 1,
        "page_end": 2,
        "text": "Conteúdo extraído do documento..."
      }
    ]
  }
  ```

---

## 🏗️ Estrutura de Diretórios (`src/api/`)

- `main.py`: Ponto de entrada do FastAPI, onde as rotas e o CORS são configurados.
- `config.py`: Carrega as variáveis de ambiente utilizando Pydantic.
- `database.py`: Configuração do SQLAlchemy e Sessão do banco.
- `dependencies.py`: Injeção de dependências do FastAPI (ex: recuperar sessão do banco e usuário logado).
- `models/`: Modelos ORM (ex: `User`).
- `schemas/`: Schemas do Pydantic para validação de Input/Output (Request/Response).
- `routers/`: Definição dos endpoints (`auth.py`, `qa.py`).
- `services/`: Lógica de negócio, como hashing de senha, geração de JWT e inicialização do pipeline do Oráculo.

## 📝 Banco de Dados e Migrações (Alembic)

O controle do esquema do banco de dados é feito pelo **Alembic**.

- Para criar uma nova migração (após alterar os modelos em `models/`):
  ```bash
  alembic revision --autogenerate -m "descricao_da_mudanca"
  ```
- Para aplicar as alterações no banco:
  ```bash
  alembic upgrade head
  ```
