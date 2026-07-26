# Oráculo — Sistema RAG para Consultas de Editais

O **Oráculo** é um sistema de **RAG (Retrieval-Augmented Generation)** projetado para responder a perguntas de forma precisa e direta sobre documentos textuais estruturados (como editais de concursos públicos). 

Ele adota uma abordagem local para a busca de documentos com o algoritmo **BM25**, gerando chunks inteligentes baseados em parágrafos com overlap de tokens via `tiktoken`. A síntese de respostas é terceirizada para provedores de LLM configuráveis (Google Gemini, OpenAI ou OpenRouter) através de uma interface abstrata.

---

## 🏗️ Estrutura do Projeto

Abaixo está o mapeamento dos principais diretórios e arquivos que compõem o Oráculo:

```text
Oraculo/
├── data/
│   └── chunks_cache.json       # Cache gerado pelo pipeline de ingestão contendo os chunks processados
├── src/
│   ├── llm/                    # Camada de abstração e provedores de LLMs
│   │   ├── __init__.py
│   │   ├── base.py             # Classe abstrata base LLMProvider
│   │   ├── gemini_prov.py      # Integração com modelos Google Gemini
│   │   ├── openai_prov.py      # Integração com modelos OpenAI
│   │   └── openrouter_prov.py  # Integração com a API do OpenRouter
│   ├── pipelines/              # Pipelines que orquestram os fluxos do sistema
│   │   ├── __init__.py
│   │   ├── ingestion.py        # IngestionPipeline: processamento inicial do texto base
│   │   └── qa.py               # QAPipeline: fluxo completo de pergunta, busca e resposta RAG
│   ├── retrievers/             # Algoritmos de busca e recuperação de contexto
│   │   ├── __init__.py
│   │   ├── base.py             # Interface abstrata BaseRetriever
│   │   └── bm25.py             # BM25Retriever usando tokenização tiktoken e biblioteca rank-bm25
│   └── chunker.py              # ParagraphChunker para segmentação inteligente de textos
├── .env.exemplo                # Modelo de variáveis de ambiente do projeto
├── .gitignore
├── requirements.txt            # Dependências Python necessárias
├── run_ingestion.py            # Script executável para processar o texto base
└── run_qa.py                   # Script interativo de Perguntas & Respostas
```

---

## 🛠️ Tecnologias e Dependências

O projeto é desenvolvido em **Python 3** e utiliza as seguintes bibliotecas principais:

*   **Processamento de Texto & Tokenização**:
    *   `tiktoken`: Usado para contar tokens de forma precisa e alinhar com o vocabulário das LLMs.
*   **Recuperação de Informação (Retriever)**:
    *   `rank-bm25` (`BM25Okapi`): Algoritmo de busca léxica por relevância.
*   **Provedores de LLM**:
    *   `google-generativeai`: Acesso às APIs do Google Gemini.
    *   `openai`: Acesso às APIs da OpenAI e integradores compatíveis (como OpenRouter).
*   **Gestão de Ambiente**:
    *   `python-dotenv`: Carregamento automático de chaves de API a partir de arquivos `.env`.

---

## ⚙️ Configuração e Instalação

### 1. Clonar e Acessar o Diretório
```bash
git clone <url-do-repositorio>
cd Oraculo
```

### 2. Configurar o Ambiente Virtual (Recomendado)
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar as Chaves de API
Crie um arquivo `.env` na raiz do projeto contendo as chaves que você deseja utilizar. Você pode se basear no arquivo `.env.exemplo`:
```bash
cp .env.exemplo .env
```
Abra o `.env` e preencha as variáveis de ambiente necessárias:
```env
GEMINI_API_KEY="sua-chave-gemini"
OPENAI_API_KEY="sua-chave-openai"
OPENROUTER_API_KEY="sua-chave-openrouter"
```

---

## 🚀 Como Executar

O fluxo de funcionamento do projeto possui duas etapas obrigatórias: **Ingestão** e **Consulta**.

### Etapa 1: Ingestão de Dados
O script `run_ingestion.py` pega um texto base estático (definido na variável `BASE_TEXT` dentro do arquivo) e realiza o split por parágrafos duplos (`\n\n`), calculando uma sobreposição (overlap) de 20% de tokens de forma a preservar o contexto entre os blocos. Os resultados são salvos em `data/chunks_cache.json`.

Execute o script de ingestão:
```bash
python run_ingestion.py
```

### Etapa 2: Executar Consultas (Q&A)
O script `run_qa.py` é interativo. Ele carrega os chunks persistidos no passo anterior, inicializa o retriever e solicita a pergunta do usuário.

1. Abra o arquivo `run_qa.py` e escolha qual provedor e modelo deseja usar (descomentando as linhas apropriadas em `main()`):
   ```python
   # Exemplo: Utilizando OpenRouter
   provider = OpenRouterProvider()
   model_name = "openai/gpt-4.1-mini"
   ```
2. Execute o script:
   ```bash
   python run_qa.py
   ```
3. Digite sua pergunta quando solicitado no terminal (exemplo: *"Qual o prazo de validade do concurso?"*).
4. O Oráculo irá buscar os parágrafos mais relevantes no cache local usando BM25, formatará o prompt e gerará a resposta final fundamentada nos dados recuperados.
