# Comandos para execução do Oráculo

Execute os comandos na raiz do repositório.

## Preparar o ambiente

```bash
source venv/bin/activate
python -m pip install -r requirements.txt
cp configs/ingestion.example.yml configs/ingestion.yml
mkdir -p pdfs
```

## Ingerir todos os PDFs

Coloque os PDFs em `pdfs/` e execute:

```bash
python -m src.cli.ingest --config configs/ingestion.yml
```

Para reprocessar arquivos inalterados:

```bash
python -m src.cli.ingest --config configs/ingestion.yml --force
```

## Testar somente o BM25

```bash
python run_bm25.py "Como executar o aplicativo?"
```

Esse comando lê `data/bases/documentos/chunks.jsonl` e não usa uma LLM.

## Executar o RAG completo

```bash
python run_qa.py "Como executar o aplicativo?"
```

O RAG recupera os trechos do mesmo `chunks.jsonl` com BM25 e envia somente os
resultados relevantes à LLM configurada.

## Ler um único PDF sem ingestão

```bash
python read_pdf.py ./pdfs/documento.pdf --output ./resultado.txt
```

## Executar os testes

```bash
python -m pytest -q
```

## MinIO opcional

O MinIO ainda não participa da pipeline de ingestão.

```bash
docker compose up -d minio
docker compose ps
docker compose down
```
