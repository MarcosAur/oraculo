# Documentação do Oráculo

Esta pasta contém a documentação técnica e operacional do sistema Oráculo.

## Índice

1. [Visão geral e arquitetura](ARQUITETURA.md)
2. [Instalação e configuração](CONFIGURACAO.md)
3. [Pipeline de ingestão](INGESTION.md)
4. [Busca BM25 e RAG](BM25_E_RAG.md)
5. [Banco vetorial e busca semântica](BUSCA_VETORIAL.md)
6. [Formatos e persistência](FORMATOS_DE_DADOS.md)
7. [Operação, testes e solução de problemas](OPERACAO_E_TESTES.md)
8. [Referência rápida de comandos](COMANDOS_EXECUCAO.md)

## Fluxo rápido

```bash
source venv/bin/activate
cp configs/ingestion.example.yml configs/ingestion.yml
mkdir -p pdfs
python -m src.cli.ingest --config configs/ingestion.yml
python run_bm25.py "Como executar o aplicativo?"
python run_search.py "Como executar o aplicativo?"
python run_qa.py "Como executar o aplicativo?"
```

O teste BM25 é totalmente local. O RAG completo requer uma chave de API para o
provedor de LLM selecionado.

## Estado atual

O sistema implementa:

- descoberta local e recursiva de PDFs;
- OCR com PaddleOCR;
- normalização conservadora de Markdown;
- chunking estrutural limitado por tokens;
- persistência incremental em JSON e JSONL;
- recuperação lexical BM25+;
- banco vetorial ChromaDB com embeddings `multilingual-e5-small`;
- busca semântica e híbrida (BM25 + vetores via RRF);
- geração de respostas com OpenRouter, OpenAI ou Gemini;
- testes automatizados dos componentes principais.

Ainda não fazem parte do fluxo ativo:

- MinIO como fonte de documentos;
- interface web;
- remoção automática da base quando um PDF desaparece da pasta de entrada.
