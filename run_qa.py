import sys
import os
from dotenv import load_dotenv

sys.path.append("src")
from pipelines import QAPipeline
from llm import GeminiProvider, OpenAIProvider, OpenRouterProvider

def main():
    print("=" * 60)
    print(" INICIANDO PIPELINE DE RESPOSTA AO CLIENTE ")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # 1. Initialize the LLM provider manually
    # Uncomment/configure the provider you wish to use:
    # provider = GeminiProvider()
    # model_name = "gemini-1.5-flash"
    
    # provider = OpenAIProvider()
    # model_name = "gpt-4o"
    
    provider = OpenRouterProvider()
    model_name = "openai/gpt-4.1-mini"
    
    # 2. Initialize QAPipeline
    try:
        pipeline = QAPipeline(llm_provider=provider)
    except FileNotFoundError as e:
        print(f"\033[31m{e}\033[0m")
        sys.exit(1)
        
    # 3. Get user question
    default_question = "Qual o prazo de validade do concurso?"
    print(f"Digite sua pergunta ou aperte ENTER para usar a padrão:")
    print(f"Padrão: \"{default_question}\"")
    
    try:
        user_question = input("\nPergunta: ").strip()
        if not user_question:
            user_question = default_question
    except (EOFError, KeyboardInterrupt):
        user_question = default_question
        print(f"\nUsando pergunta padrão (ambiente não interativo): \"{default_question}\"")
        
    print(f"\nBuscando resposta usando o modelo: {model_name}...")
    
    # 4. Generate answer
    result = pipeline.answer(user_question, llm_model=model_name, top_k=3)
    
    # 5. Display output
    print("\n" + "=" * 60)
    print(" RESPOSTA DO ORÁCULO ")
    print("=" * 60)
    print(f"\033[32m{result['answer']}\033[0m")
    print("=" * 60)
    
    print("\n[Fontes Consultadas]:")
    for doc in result["sources"]:
        print(f" - Chunk {doc['chunk_index']} (score: {doc['score']:.4f}):")
        text_preview = doc['text'].strip().replace('\n', ' ')
        if len(text_preview) > 120:
            text_preview = text_preview[:120] + "..."
        print(f"   \"{text_preview}\"")
    print("=" * 60)

if __name__ == "__main__":
    main()

