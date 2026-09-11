# Oráculo — RAG para PDFs

O Oráculo extrai PDFs com PaddleOCR, normaliza o texto, cria chunks limitados por
tokens e permite consultá-los com recuperação lexical BM25 e uma LLM opcional.

A documentação completa está em [docs/README.md](docs/README.md).

## Estrutura principal

```text
pdfs/                              # PDFs de entrada
configs/ingestion.yml              # Configuração da ingestão
data/bases/documentos/
├── manifest.json
├── documents.jsonl
├── chunks.jsonl                   # Fonte de dados do BM25 e do RAG
├── failures.jsonl
└── documents/                     # Markdown extraído por documento
src/ingestion/                     # OCR, normalização, chunking e persistência
src/retrievers/bm25.py             # Recuperação BM25 sobre chunks.jsonl
src/pipelines/qa.py                # Recuperação + geração da resposta
run_bm25.py                        # Teste local, sem API
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

Variáveis aceitas: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`,
`LLM_PROVIDER` e `LLM_MODEL`.

## Testes automatizados

```bash
python -m pytest -q
```
