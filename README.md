# Oráculo — RAG para PDFs

O Oráculo extrai PDFs com PaddleOCR, normaliza o texto, cria chunks limitados por
tokens, armazena os embeddings em um banco vetorial (ChromaDB) e permite
consultá-los com busca lexical (BM25), semântica ou híbrida e uma LLM opcional.

A documentação completa está em [docs/README.md](docs/README.md).

## Estrutura principal

```text
pdfs/                              # PDFs de entrada
configs/ingestion.yml              # Configuração da ingestão
data/bases/documentos/
├── manifest.json
├── documents.jsonl
├── chunks.jsonl                   # Fonte de dados do BM25 e do RAG
├── chroma/                        # Banco vetorial (embeddings dos chunks)
├── failures.jsonl
└── documents/                     # Markdown extraído por documento
src/ingestion/                     # OCR, normalização, chunking e persistência
src/retrievers/bm25.py             # Recuperação BM25 sobre chunks.jsonl
src/retrievers/vector.py           # ChromaDB: indexação e busca semântica
src/retrievers/hybrid.py           # BM25 + vetores (Reciprocal Rank Fusion)
src/pipelines/qa.py                # Recuperação + geração da resposta
run_bm25.py                        # Teste local, sem API
run_search.py                      # Teste BM25/vetorial/híbrido, sem API
run_qa.py                          # RAG completo, com LLM
```

## Instalação

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp configs/ingestion.example.yml configs/ingestion.yml
mkdir -p pdfs
```

## Ingestão dos PDFs

Coloque os arquivos em `pdfs/`. Subpastas também são processadas quando
`source.recursive` está habilitado.

```bash
python -m src.cli.ingest --config configs/ingestion.yml
```

Para reprocessar inclusive os PDFs que não mudaram:

```bash
python -m src.cli.ingest --config configs/ingestion.yml --force
```

## Teste do BM25

O teste lê diretamente `data/bases/documentos/chunks.jsonl` e não chama APIs:

```bash
python run_bm25.py "Como executar o aplicativo?"
```

Para ver o texto integral dos resultados ou usar outra base:

```bash
python run_bm25.py "Como executar o aplicativo?" --top-k 5 --full
python run_bm25.py "Minha pergunta" --chunks data/bases/outra-base/chunks.jsonl
```

## Banco vetorial

A ingestão já vetoriza os chunks ao final (`vector_store` em
`configs/ingestion.yml`). Para vetorizar uma base existente ou refazer o índice:

```bash
python -m src.cli.index_vectors
python -m src.cli.index_vectors --rebuild
```

Teste a busca semântica ou híbrida sem LLM:

```bash
python run_search.py "Quem são os usuários do sistema?" --retriever vector
python run_search.py "Como executar o aplicativo?"      # hybrid (padrão)
```

Detalhes em [docs/BUSCA_VETORIAL.md](docs/BUSCA_VETORIAL.md).

## RAG completo

Configure no `.env` a chave do provedor desejado e execute:

```bash
python run_qa.py "Como executar o aplicativo?"
```

O padrão usa OpenRouter. Outros exemplos:

```bash
python run_qa.py "Minha pergunta" --provider openai --model gpt-4.1-mini
python run_qa.py "Minha pergunta" --provider gemini --model gemini-2.0-flash
```

Por padrão a recuperação é híbrida; use `--retriever bm25|vector|hybrid` para
escolher.

Variáveis aceitas: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`,
`LLM_PROVIDER`, `LLM_MODEL`, `RETRIEVER_MODE` e `EMBEDDING_MODEL`.

## Testes automatizados

```bash
python -m pytest -q
```
