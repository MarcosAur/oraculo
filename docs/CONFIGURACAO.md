# Instalação e configuração

## Requisitos

- Python 3.12 recomendado para reproduzir o ambiente atual;
- espaço em disco para modelos do PaddleOCR e artefatos extraídos;
- acesso à internet na primeira carga dos modelos OCR;
- chave de API apenas para o RAG completo;
- GPU NVIDIA opcional, com driver e wheel CUDA compatíveis.

## Ambiente Python

Na raiz do repositório:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Confirme o interpretador:

```bash
python --version
python -m pip --version
```

## Configuração da ingestão

Crie o arquivo local a partir do modelo versionado:

```bash
cp configs/ingestion.example.yml configs/ingestion.yml
mkdir -p pdfs
```

Configuração completa padrão:

```yaml
source:
  input_dir: ./pdfs
  recursive: true

output:
  root_dir: ./data/bases
  base_name: documentos

paddle_ocr:
  language: pt
  device: cpu
  minimum_confidence: 0.5
  use_doc_orientation_classify: false
  use_doc_unwarping: false
  use_textline_orientation: false

chunking:
  tokenizer_model: gpt-4.1
  chunk_size: 800
  chunk_overlap: 120
  minimum_chunk_size: 80

runtime:
  force: false
  continue_on_error: true
```

### `source`

| Campo | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `input_dir` | caminho | obrigatório | Diretório local que contém os PDFs |
| `recursive` | booleano | `true` | Inclui PDFs de subdiretórios |

Caminhos relativos são resolvidos a partir do diretório no qual o comando é
executado. Execute os comandos na raiz do repositório para obter os caminhos
mostrados nesta documentação.

### `output`

| Campo | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `root_dir` | caminho | `data/bases` | Diretório que reúne todas as bases |
| `base_name` | texto | `default` | Nome da base dentro de `root_dir` |

`base_name` deve começar com letra ou número e só pode conter letras, números,
ponto, sublinhado e hífen.

### `paddle_ocr`

| Campo | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `language` | texto | `pt` | Idioma principal do reconhecimento |
| `device` | texto | `cpu` | Dispositivo, como `cpu` ou `gpu:0` |
| `minimum_confidence` | decimal | `0.5` | Score mínimo aceito, entre 0 e 1 |
| `use_doc_orientation_classify` | booleano | `false` | Detecta orientação geral do documento |
| `use_doc_unwarping` | booleano | `false` | Tenta corrigir deformação da página |
| `use_textline_orientation` | booleano | `false` | Detecta orientação das linhas |

O backend oneDNN está desativado no código para evitar uma incompatibilidade do
PaddlePaddle 3.3.x em CPU. Isso pode reduzir desempenho, mas torna a execução
mais estável no ambiente atual.

### `chunking`

| Campo | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `tokenizer_model` | texto | `gpt-4.1` | Modelo usado pelo `tiktoken` para contar tokens |
| `chunk_size` | inteiro | `800` | Máximo de tokens por chunk |
| `chunk_overlap` | inteiro | `120` | Máximo de tokens reaproveitados entre chunks |
| `minimum_chunk_size` | inteiro | `80` | Limite usado para tentar unir o último chunk pequeno |

Regras de validação:

- `chunk_size` deve ser maior que zero;
- `chunk_overlap` não pode ser negativo;
- `chunk_overlap` deve ser menor que `chunk_size`;
- `minimum_chunk_size` deve estar entre zero e `chunk_size`.

Se `tokenizer_model` não for conhecido pelo `tiktoken`, o sistema usa
`cl100k_base`.

### `runtime`

| Campo | Tipo | Padrão | Descrição |
| --- | --- | --- | --- |
| `force` | booleano | `false` | Reprocessa PDFs mesmo com checksum inalterado |
| `continue_on_error` | booleano | `true` | Continua após falha em um documento |

O argumento CLI `--force` sobrescreve o valor definido no YAML.

## Execução sem YAML

É possível configurar os caminhos pela linha de comando:

```bash
python -m src.cli.ingest \
  --input ./pdfs \
  --base documentos \
  --output ./data/bases
```

As opções `--input`, `--base` e `--output` também podem sobrescrever partes do
arquivo YAML quando usadas junto de `--config`.

## Variáveis de ambiente das LLMs

Copie o exemplo se ainda não houver `.env`:

```bash
cp .env.exemplo .env
```

Variáveis reconhecidas:

| Variável | Uso |
| --- | --- |
| `OPENROUTER_API_KEY` | Autenticação no OpenRouter |
| `OPENAI_API_KEY` | Autenticação na OpenAI |
| `GEMINI_API_KEY` | Autenticação no Gemini |
| `LLM_PROVIDER` | Provedor padrão de `run_qa.py` |
| `LLM_MODEL` | Modelo padrão de `run_qa.py` |

Valores válidos de `LLM_PROVIDER`: `openrouter`, `openai` e `gemini`.

Nunca versione o arquivo `.env`. Ele já está ignorado pelo Git.

## CPU e GPU

O pacote `paddlepaddle` comum é a distribuição para CPU. Informar `gpu:0` não
transforma essa instalação em CUDA. O script verifica
`paddle.device.is_compiled_with_cuda()` e encerra com uma mensagem clara quando
o runtime não possui CUDA.

Verificação:

```bash
python -c "import paddle; print(paddle.__version__); print(paddle.device.is_compiled_with_cuda())"
```

Para GPU, instale um wheel `paddlepaddle-gpu` compatível com o sistema, o Python,
o driver e a versão CUDA. Não mantenha simultaneamente os wheels CPU e GPU que
exportam o mesmo módulo `paddle`.

## MinIO

O serviço opcional pode ser iniciado com:

```bash
docker compose up -d minio
```

Endpoints padrão:

- API S3: `http://localhost:9000`;
- console: `http://localhost:9001`.

As variáveis `MINIO_*` existem no arquivo de exemplo, mas a pipeline atual ainda
não lê PDFs do MinIO.
