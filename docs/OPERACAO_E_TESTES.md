# Operação, testes e solução de problemas

## Rotina recomendada

```bash
source venv/bin/activate
python -m src.cli.ingest --config configs/ingestion.yml
python run_bm25.py "Pergunta representativa"
python run_qa.py "Pergunta representativa"
```

Teste primeiro o BM25. Se o trecho correto não for recuperado, trocar o modelo de
LLM não resolverá a causa.

## Verificações de saúde

### Ambiente

```bash
python --version
python -m pip check
python -m pip show paddlepaddle paddlepaddle-gpu paddleocr rank-bm25 tiktoken
```

### Base

```bash
test -f data/bases/documentos/manifest.json
test -f data/bases/documentos/documents.jsonl
test -f data/bases/documentos/chunks.jsonl
wc -l data/bases/documentos/documents.jsonl
wc -l data/bases/documentos/chunks.jsonl
wc -l data/bases/documentos/failures.jsonl
```

### Recuperação

```bash
python run_bm25.py "Como executar o aplicativo?" --top-k 3
```

## Testes automatizados

Toda a suíte:

```bash
python -m pytest -q
```

Por camada:

```bash
python -m pytest tests/ingestion -q
python -m pytest tests/retrievers -q
python -m pytest tests/pipelines -q
python -m pytest tests/test_read_pdf.py -q
```

Cobertura atual dos testes:

- descoberta recursiva e extensão PDF sem diferenciação de caixa;
- validação da configuração;
- extração e filtragem por confiança com motores falsos;
- chunking por seção, página, overlap e tabela;
- ingestão incremental;
- substituição de documento modificado;
- preservação da versão anterior após falha;
- leitura do JSONL atual pelo BM25;
- ausência de resultados para termos inexistentes;
- montagem do contexto RAG;
- bloqueio da chamada à LLM quando a busca não retorna chunks;
- extração isolada por `read_pdf.py`.

Os testes usam extratores e provedores falsos. Eles não dependem de download de
modelos nem consomem APIs de LLM.

## Teste manual do OCR

```bash
python read_pdf.py ./pdfs/manual.pdf --output /tmp/manual-ocr.txt
sed -n "1,80p" /tmp/manual-ocr.txt
```

Use um PDF escaneado para validar OCR real. Um PDF que já contém texto também é
processado pelo PaddleOCR no fluxo atual.

## Teste manual da ingestão

```bash
python -m src.cli.ingest --config configs/ingestion.yml --force
python -m json.tool data/bases/documentos/manifest.json
```

Confirme no resumo:

- `failed` igual a zero;
- `active_documents` igual ao número esperado;
- `active_chunks` maior que zero.

## Teste manual do BM25

Escolha perguntas que contenham termos presentes nos documentos:

```bash
python run_bm25.py "Quais são os pré-requisitos?"
python run_bm25.py "Como funciona a sincronização offline?"
```

Avalie:

- se a primeira fonte é correta;
- se o intervalo de páginas é plausível;
- se o trecho contém a resposta;
- se mudanças em `top_k` melhoram ou pioram o contexto.

## Teste manual do RAG

```bash
python run_qa.py "Como funciona a sincronização offline?" --provider openrouter
```

Verifique se a resposta:

- está sustentada pelos chunks mostrados;
- cita a fonte;
- não adiciona informações externas;
- informa ausência de dados quando apropriado.

## Problemas comuns

### Diretório de entrada não encontrado

Sintoma:

```text
Input directory not found
```

Correção:

```bash
mkdir -p pdfs
```

Confirme também `source.input_dir` no YAML e execute o comando na raiz do projeto.

### Nenhum PDF descoberto

Confirme os arquivos:

```bash
find pdfs -type f -iname "*.pdf"
```

Se os PDFs estiverem em subpastas, use `recursive: true`.

### Erro `ConvertPirAttribute2RuntimeAttribute`

Esse erro está associado ao executor oneDNN do Paddle em CPU. O extrator define
`enable_mkldnn=False`. Confirme que está executando o código e o ambiente atuais:

```bash
source venv/bin/activate
python -c "import paddle, paddleocr; print(paddle.__version__); print(paddleocr.__version__)"
```

Não execute uma cópia antiga de `read_pdf.py` ou do pacote `src` em outro
diretório.

### `gpu:0` não funciona

Verifique:

```bash
nvidia-smi
python -c "import paddle; print(paddle.device.is_compiled_with_cuda())"
```

Se o segundo comando imprimir `False`, está instalado o runtime CPU. Instale o
wheel `paddlepaddle-gpu` compatível com a plataforma. O driver visível por
`nvidia-smi` não é suficiente.

### OCR não reconhece texto

Possíveis ações:

- confirme que o PDF abre e possui páginas;
- reduza `minimum_confidence`, por exemplo para `0.3`;
- selecione o idioma correto;
- habilite classificação de orientação para páginas rotacionadas;
- habilite unwarping para fotos deformadas;
- examine os avisos em `documents.jsonl` e as falhas em `failures.jsonl`.

Reduzir a confiança recupera mais texto, mas também aumenta erros.

### Primeira execução demorada

PaddleOCR pode baixar e inicializar modelos. Execuções posteriores reutilizam o
cache local. O processamento em CPU de PDFs longos pode levar vários minutos.

### Documento sempre aparece como `skipped`

O checksum não mudou. Para reprocessar:

```bash
python -m src.cli.ingest --config configs/ingestion.yml --force
```

### PDF removido ainda aparece na busca

Esse é o comportamento atual: remoção da origem não elimina registros antigos.
Para reconstruir a base apenas com os PDFs existentes, mova a base para backup e
execute novamente:

```bash
mv data/bases/documentos data/bases/documentos.backup
python -m src.cli.ingest --config configs/ingestion.yml
```

### JSONL inválido

Sintoma:

```text
Invalid JSONL ... at line ...
```

Restaure a base de um backup ou reconstrua pela ingestão. Evite corrigir apenas
uma linha sem verificar as relações entre documentos e chunks.

### BM25 não encontra resultados

O BM25 exige pelo menos um termo lexical em comum. Tente:

- usar palavras que aparecem no documento;
- remover formulações muito abstratas;
- conferir o conteúdo extraído com `rg`;
- confirmar que o script aponta para a base correta com `--chunks`.

Exemplo:

```bash
rg -n "sincronização" data/bases/documentos/chunks.jsonl
python run_bm25.py "sincronização offline"
```

### Resultado BM25 pouco relevante

- aumente ou reduza `top_k` para observar o ranking;
- verifique ruído introduzido pelo OCR;
- ajuste `chunk_size` e `chunk_overlap` e reingira a base;
- formule uma consulta com termos distintivos;
- lembre que scores são relativos ao corpus e não porcentagens.

### Arquivo de chunks não encontrado

Execute a ingestão ou informe outra base:

```bash
python -m src.cli.ingest --config configs/ingestion.yml
python run_bm25.py "Minha pergunta" --chunks data/bases/documentos/chunks.jsonl
```

### Chave de API ausente

Sintomas incluem mensagens como:

```text
OPENROUTER_API_KEY environment variable is not set
```

Crie `.env`, preencha a chave e escolha o provedor correspondente. O BM25 local
continua funcionando sem chaves.

### LLM responde algo não sustentado

Use `run_bm25.py --full` para inspecionar exatamente o contexto recuperado. Se o
contexto estiver errado, ajuste busca ou chunking. Se estiver correto, avalie o
modelo e as instruções do prompt.

## Dependências presentes, mas fora do fluxo

`chromadb`, `sentence-transformers` e `langchain-text-splitters` estão listados em
`requirements.txt`, porém não são importados pelo pipeline atual. O MinIO também
não está conectado. Não conte com armazenamento vetorial ou ingestão S3 sem uma
implementação adicional.

O SDK `google-generativeai` utilizado pelo provedor Gemini emite aviso de
descontinuação. O aviso não interfere no BM25, mas a migração para o SDK atual do
Google deve ser planejada antes de depender desse provedor em produção.

## Segurança operacional

- não versione `.env`;
- trate PDFs como entradas não confiáveis;
- revise dados sensíveis antes de enviar chunks a uma LLM externa;
- proteja backups da base, pois eles contêm o texto extraído;
- não exponha o MinIO com credenciais padrão fora de ambiente local;
- use permissões restritas para `data/bases`.
