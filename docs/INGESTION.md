# Ingestão genérica de PDFs

O pipeline processa recursivamente todos os PDFs de uma pasta. O extrator padrão usa PaddleOCR, filtra resultados pela confiança configurada e produz um Markdown paginado. Também é possível injetar qualquer implementação de `DocumentExtractor`.

## Instalação

Use o ambiente virtual do projeto e instale as dependências da ingestão:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Configuração

Copie a configuração de exemplo:

```bash
cp configs/ingestion.example.yml configs/ingestion.yml
```

Os caminhos relativos do YAML são resolvidos a partir do diretório em que o comando é executado.

Configuração mínima:

```yaml
source:
  input_dir: ./pdfs

output:
  root_dir: ./data/bases
  base_name: documentos
```

Configuração do PaddleOCR:

```yaml
paddle_ocr:
  language: pt
  device: cpu
  minimum_confidence: 0.5
  use_doc_orientation_classify: false
  use_doc_unwarping: false
  use_textline_orientation: false
```

## Execução

Com YAML:

```bash
python -m src.cli.ingest --config configs/ingestion.yml
```

Sem YAML:

```bash
python -m src.cli.ingest --input ./pdfs --base documentos
```

Na primeira execução, o PaddleOCR pode baixar os modelos necessários. Use `--force` para reprocessar documentos cujo checksum não mudou.

## Saída

```text
data/bases/documentos/
├── manifest.json
├── documents.jsonl
├── chunks.jsonl
├── failures.jsonl
└── documents/
    └── <document_id>/
        ├── document.md
        ├── document.raw.md
        └── assets/
```

- `document.raw.md` preserva o texto reconhecido antes da normalização.
- `document.md` contém o Markdown normalizado usado no chunking.
- `assets/` contém imagens extraídas e referenciadas pelo Markdown.
- `documents.jsonl` registra documentos ativos e checksums.
- `chunks.jsonl` é a fonte de dados usada pelo BM25 e pelo RAG.
- `failures.jsonl` registra falhas da execução mais recente.
- `manifest.json` registra configuração, versão e estatísticas.

## Atualização incremental

O checksum SHA-256 identifica alterações. PDFs inalterados são ignorados. Um PDF modificado substitui sua versão anterior somente depois de extração, normalização e chunking bem-sucedidos. Uma falha mantém a última versão válida na base.

PDFs removidos da pasta de entrada permanecem na base. A exclusão será implementada futuramente como uma operação explícita.

## Testes

```bash
python -m pytest tests/ingestion -q
```
