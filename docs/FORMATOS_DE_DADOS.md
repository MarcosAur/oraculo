# Formatos de dados e persistência

## Organização da base

Cada base ocupa um diretório próprio:

```text
data/bases/<base_name>/
├── .staging/
├── manifest.json
├── documents.jsonl
├── chunks.jsonl
├── failures.jsonl
└── documents/
    └── <document_id>/
        ├── document.raw.md
        ├── document.md
        └── assets/
```

Com a configuração padrão, `<base_name>` é `documentos`.

## JSON e JSONL

`manifest.json` é um único objeto JSON formatado. Os demais arquivos de
metadados usam JSON Lines: cada linha não vazia é um objeto JSON independente.

Vantagens do JSONL neste sistema:

- leitura sequencial simples;
- um registro por documento, chunk ou falha;
- inspeção com ferramentas de terminal;
- reconstrução direta do índice BM25.

Não transforme `chunks.jsonl` em uma lista JSON com colchetes. O carregador BM25
espera um objeto por linha.

## `manifest.json`

Registra a configuração efetiva e o resumo da última execução.

Exemplo simplificado:

```json
{
  "base_name": "documentos",
  "generated_at": "2026-09-11T22:00:00+00:00",
  "input_directory": "/caminho/Oraculo/pdfs",
  "schema_version": "1.0",
  "configuration": {
    "source": {
      "input_dir": "/caminho/Oraculo/pdfs",
      "recursive": true
    },
    "output": {
      "root_dir": "/caminho/Oraculo/data/bases",
      "base_name": "documentos"
    }
  },
  "statistics": {
    "discovered": 2,
    "processed": 2,
    "skipped": 0,
    "failed": 0,
    "active_documents": 2,
    "active_chunks": 2,
    "duration_seconds": 42.5
  }
}
```

Campos estatísticos:

| Campo | Significado |
| --- | --- |
| `discovered` | PDFs encontrados na execução |
| `processed` | PDFs processados com sucesso |
| `skipped` | PDFs inalterados ignorados |
| `failed` | PDFs que falharam nesta execução |
| `active_documents` | Documentos válidos presentes na base |
| `active_chunks` | Chunks válidos presentes na base |
| `duration_seconds` | Duração total da execução |

## `documents.jsonl`

Contém um registro para cada documento ativo.

```json
{
  "assets_dir": "documents/417c4ce6595374a2682494aa/assets",
  "checksum": "sha256-completo",
  "created_at": "2026-09-11T22:00:00+00:00",
  "document_id": "417c4ce6595374a2682494aa",
  "extraction_method": "paddleocr",
  "file_name": "manual.pdf",
  "languages": ["pt"],
  "markdown_path": "documents/417c4ce6595374a2682494aa/document.md",
  "metadata": {
    "warnings": []
  },
  "page_count": 2,
  "raw_markdown_path": "documents/417c4ce6595374a2682494aa/document.raw.md",
  "relative_path": "manual.pdf",
  "schema_version": "1.0",
  "size_bytes": 123456,
  "source_path": "/caminho/Oraculo/pdfs/manual.pdf",
  "status": "success"
}
```

`source_path` é absoluto. Os caminhos de artefatos são relativos à raiz da base.

## `chunks.jsonl`

É a fonte de dados do BM25 e do RAG.

```json
{
  "chunk_id": "421610485894e9ee7f0880b1d0e9615d",
  "chunk_index": 1,
  "document_id": "417c4ce6595374a2682494aa",
  "metadata": {
    "overlap_token_count": 0,
    "tokenizer_model": "gpt-4.1"
  },
  "page_end": 2,
  "page_start": 1,
  "schema_version": "1.0",
  "section_path": ["Manual", "Execução"],
  "source_path": "manual.pdf",
  "text": "Texto normalizado do trecho.",
  "token_count": 527
}
```

Campos relevantes para consulta:

| Campo | Uso |
| --- | --- |
| `text` | Corpus lexical e contexto enviado à LLM |
| `source_path` | Identificação da fonte exibida ao usuário |
| `page_start`, `page_end` | Localização aproximada no PDF |
| `section_path` | Hierarquia Markdown associada |
| `token_count` | Tamanho segundo o tokenizer da ingestão |
| `metadata.overlap_token_count` | Conteúdo reaproveitado do chunk anterior |

O BM25 cria sua própria tokenização lexical em memória. Portanto, não há campo
`tokens` persistido.

## `failures.jsonl`

Registra apenas falhas da execução mais recente:

```json
{
  "error_type": "RuntimeError",
  "message": "Descrição da falha",
  "occurred_at": "2026-09-11T22:00:00+00:00",
  "relative_path": "documentos/manual.pdf",
  "source_path": "/caminho/Oraculo/pdfs/documentos/manual.pdf",
  "stage": "ingestion"
}
```

Uma execução posterior sem falhas regrava esse arquivo vazio.

## Artefatos Markdown

### `document.raw.md`

Resultado direto do OCR após filtro de confiança. Preserva o marcador entre
páginas.

### `document.md`

Versão normalizada usada pelo chunker.

### `assets/`

Diretório reservado para imagens ou outros artefatos gerados por extratores. O
extrator PaddleOCR atual apenas reconhece texto e deixa o diretório vazio.

## Ordenação

Antes da gravação:

- documentos são ordenados por `relative_path`;
- chunks são ordenados por `document_id` e `chunk_index`;
- falhas são ordenadas por `relative_path`.

## Consistência e edição manual

Evite editar os arquivos da base manualmente. Os IDs, documentos, chunks e
caminhos são relacionados entre si. Para corrigir conteúdo, altere ou substitua
o PDF e execute a ingestão novamente.

Para validar sintaxe:

```bash
python -m json.tool data/bases/documentos/manifest.json
python -c "import json; [json.loads(line) for line in open(\"data/bases/documentos/chunks.jsonl\", encoding=\"utf-8\") if line.strip()]; print(\"JSONL válido\")"
```

## Backup

A unidade mínima recomendada de backup é toda a pasta da base:

```bash
cp -a data/bases/documentos data/bases/documentos.backup
```

Copiar somente `chunks.jsonl` não preserva os artefatos Markdown nem os registros
de documentos.
