# Pipeline de ingestão

## Finalidade

A pipeline converte todos os PDFs de um diretório em uma base persistida de
documentos e chunks. A saída padrão é consumida diretamente pelo BM25 e pelo RAG.

## Preparação

```bash
source venv/bin/activate
cp configs/ingestion.example.yml configs/ingestion.yml
mkdir -p pdfs
```

Coloque os documentos em `pdfs/`. Com `recursive: true`, subpastas são incluídas:

```text
pdfs/
├── manual.pdf
├── arquitetura.pdf
└── normas/
    └── seguranca.PDF
```

A extensão é comparada sem diferenciar maiúsculas de minúsculas. Outros tipos de
arquivo são ignorados.

## Execução

Com YAML:

```bash
python -m src.cli.ingest --config configs/ingestion.yml
```

Com argumentos:

```bash
python -m src.cli.ingest --input ./pdfs --base documentos --output ./data/bases
```

Reprocessamento forçado:

```bash
python -m src.cli.ingest --config configs/ingestion.yml --force
```

Ao final, a CLI imprime um resumo em JSON. O código de saída é zero quando não há
falhas, 2 quando pelo menos um documento falha e 130 quando há interrupção por
teclado.

## Etapas detalhadas

### 1. Descoberta

`DirectoryPdfSource` valida se `input_dir` existe e é um diretório. Em seguida,
lista e ordena os PDFs pelo caminho relativo, de forma estável e sem diferenciar
maiúsculas de minúsculas.

Para cada arquivo são coletados:

- caminho absoluto;
- caminho relativo à pasta de entrada;
- nome do arquivo;
- tamanho em bytes.

### 2. Detecção incremental

A pipeline calcula SHA-256 em blocos de 1 MiB. O documento é ignorado quando:

- já existe um registro com o mesmo caminho relativo;
- o checksum não mudou;
- o Markdown processado ainda existe;
- `force` está desativado.

O caminho relativo faz parte da identidade. Mover o mesmo PDF para outra
subpasta faz com que ele seja tratado como outro documento.

### 3. OCR

`PaddleOcrPdfExtractor` cria o motor somente quando ele é necessário. Isso evita
carregar modelos durante operações que usam extratores injetados em testes.

Para cada página, o extrator lê `rec_texts` e `rec_scores`. Linhas vazias são
ignoradas. Linhas abaixo de `minimum_confidence` são descartadas e registradas
como avisos no documento.

As páginas reconhecidas são separadas por:

```html
<!-- page-break -->
```

O resultado inicial é salvo como `document.raw.md`.

Se o OCR não retornar páginas ou não reconhecer texto, o documento falha.

### 4. Normalização

`MarkdownNormalizer` faz uma limpeza conservadora:

- normaliza Unicode para NFC;
- converte CRLF e CR para LF;
- remove espaços no final das linhas;
- padroniza linhas em branco ao redor do marcador de página;
- reduz três ou mais quebras consecutivas para duas;
- preserva Markdown, tabelas e estrutura textual.

O resultado é salvo em `document.md`.

### 5. Chunking

`MarkdownChunker` usa `tiktoken` para respeitar `chunk_size`.

O algoritmo:

1. separa o Markdown em páginas pelo marcador;
2. separa blocos por linhas em branco;
3. reconhece títulos de nível 1 a 6;
4. mantém o caminho hierárquico da seção;
5. reconhece tabelas Markdown;
6. divide blocos maiores que o limite;
7. reaproveita até `chunk_overlap` tokens;
8. tenta unir um último chunk pequeno ao anterior quando o resultado ainda cabe
   em `chunk_size`.

Tabelas grandes são divididas por linhas e repetem o cabeçalho em cada parte.
Blocos comuns muito grandes são cortados por tokens.

Cada chunk registra:

- texto;
- número sequencial no documento;
- quantidade de tokens;
- páginas inicial e final;
- seção atual;
- quantidade de tokens de overlap;
- caminho do PDF de origem.

### 6. Commit e snapshot

O documento é processado dentro de `data/bases/<base>/.staging`. Apenas após
todas as etapas terem sucesso ele é movido para o diretório definitivo.

Depois de processar os documentos, a pipeline grava:

- `documents.jsonl`;
- `chunks.jsonl`;
- `failures.jsonl`;
- `manifest.json`.

Esses arquivos são escritos por substituição atômica.

## Estrutura de saída

```text
data/bases/documentos/
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

`assets/` é criado para cada documento. O extrator atual não popula imagens,
mas o diretório faz parte do contrato para extratores futuros.

## Atualizações, falhas e remoções

### PDF inalterado

É ignorado e contado em `skipped`. Use `--force` para processá-lo novamente.

### PDF modificado

Recebe um novo `document_id`. A versão anterior e seus chunks só são removidos
depois que a nova versão é concluída com sucesso.

### Falha em um PDF novo

A falha é escrita em `failures.jsonl`; nenhum documento incompleto é publicado.

### Falha ao atualizar um PDF existente

A última versão válida permanece em `documents.jsonl`, `chunks.jsonl` e no
diretório de documentos.

### PDF removido de `pdfs/`

Permanece na base. A exclusão automática ainda não foi implementada.

## Recomeçar uma base

Não esvazie somente `chunks.jsonl`, porque os arquivos da base formam um
snapshot coerente. Para preservar uma cópia antes de reiniciar:

```bash
mv data/bases/documentos data/bases/documentos.backup
python -m src.cli.ingest --config configs/ingestion.yml
```

Escolha outro nome para o backup se `documentos.backup` já existir.

## Inspeção rápida

```bash
wc -l data/bases/documentos/documents.jsonl
wc -l data/bases/documentos/chunks.jsonl
wc -l data/bases/documentos/failures.jsonl
python -m json.tool data/bases/documentos/manifest.json
```

Para localizar uma expressão nos chunks:

```bash
rg -n "flutter run" data/bases/documentos/chunks.jsonl
```

## Extração isolada

`read_pdf.py` permite testar o OCR sem atualizar a base:

```bash
python read_pdf.py ./pdfs/manual.pdf
python read_pdf.py ./pdfs/manual.pdf --output ./resultado.txt
python read_pdf.py ./pdfs/manual.pdf --language pt --device cpu --minimum-confidence 0.5
```

Essa execução usa um diretório temporário e copia somente o Markdown bruto para
o TXT de destino.
