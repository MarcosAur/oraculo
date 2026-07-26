from chunker import ParagraphChunker
from retriever import BM25OkapiRetriever

# Base raw text
BASE_TEXT = """
1.1 O Concurso Público regido por este Edital, pelos diplomas legais e regulamentares, seus anexos e posteriores retificações, caso existam, destina-se ao provimento de 212 (duzentos e doze) vagas, bem como à formação de cadastro de reserva, distribuídas na forma do subitem 3.1 deste Edital, observado o prazo de validade do certame.

1.2 O prazo de validade do Concurso será de 2 (dois) anos, contados a partir da data de homologação do resultado final, podendo ser prorrogado pelo mesmo período, a critério da Dataprev, nos termos do Art. 37, inciso III, da Constituição Federal de 1988.

1.3 Serão reservadas às pessoas com deficiência, no mínimo, 5% (cinco por cento), das vagas ofertadas e das que vierem a ser criadas durante o prazo de validade do concurso, providas na forma da Lei nº 13.146/2015, do Decreto nº 3.298/1999 e do Decreto nº 9.508/2018, e suas alterações, na forma do subitem 3.1. e do Anexo VI deste Edital.

1.4 Serão reservadas aos candidatos pretos, pardos, indígenas e quilombolas, 30% (trinta por cento) das vagas ofertadas e das que vierem a ser criadas durante o prazo de validade do concurso, com fundamento na Lei nº 15.142/2025.

1.5 A inscrição do candidato implicará a concordância plena e integral com os termos deste Edital, seus anexos, eventuais alterações e a legislação vigente.

1.6 O concurso será executado sob a responsabilidade da Fundação Getulio Vargas - FGV.
"""

def main():
    print("=" * 60)
    print(" [DEBUG] PROCESSAMENTO DE CHUNKING E TOKENIZAÇÃO ")
    print("=" * 60)
    
    # Initialize the chunker
    chunker = ParagraphChunker(model_name="gpt-4")
    
    # 1. Split text into paragraphs
    paragraphs = chunker.split_paragraphs(BASE_TEXT)
    print(f"\nTotal de parágrafos identificados: {len(paragraphs)}\n")
    
    # 2. Create chunks with 20% overlap
    overlap_percentage = 0.20
    chunks = chunker.create_chunks(paragraphs, overlap_percentage=overlap_percentage)
    
    # Print the chunks details for debugging
    for chunk in chunks:
        idx = chunk["chunk_index"]
        print("-" * 50)
        print(f"CHUNK {idx}")
        print("-" * 50)
        if chunk["overlap_text"]:
            print(f"[Overlap de 20% do Parágrafo {idx-1} (tokens: {chunk['overlap_token_count']})]:")
            print(f"\033[33m{chunk['overlap_text']}\033[0m\n")
        print(f"[Texto Principal do Parágrafo {idx} (tokens: {chunk['original_token_count']})]:")
        print(f"\033[32m{chunk['paragraph_text']}\033[0m\n")
        print(f"[Total de Tokens no Chunk: {chunk['token_count']}]")
        print(f"Tokens (IDs): {chunk['tokens']}\n")

    print("=" * 60)
    print(" [DEBUG] RECUPERAÇÃO DE INFORMAÇÕES VIA BM25OKAPI ")
    print("=" * 60)
    
    # 3. Get user question
    default_question = "Qual o prazo de validade do concurso?"
    print(f"Digite sua pergunta ou aperte ENTER para usar a pergunta padrão:")
    print(f"Padrão: \"{default_question}\"")
    
    try:
        user_question = input("\nPergunta: ").strip()
        if not user_question:
            user_question = default_question
    except (EOFError, KeyboardInterrupt):
        user_question = default_question
        print(f"\nUsando pergunta padrão (ambiente não interativo): \"{default_question}\"")
        
    print(f"\nPergunta processada: \"\033[36m{user_question}\033[0m\"")
    
    # 4. Tokenize the question using the same encoder
    question_tokens = chunker.encoding.encode(user_question)
    print(f"Tokens da pergunta ({len(question_tokens)} tokens): {question_tokens}\n")
    
    # 5. Initialize BM25OkapiRetriever
    corpus_tokens = [chunk["tokens"] for chunk in chunks]
    retriever = BM25OkapiRetriever(corpus_tokens)
    
    # 6. Retrieve and score chunks
    scored_chunks = retriever.retrieve(question_tokens, chunks)
    
    # 7. Show similarity results
    print("Resultados de Similaridade BM25Okapi (ordenados por score descendente):")
    print("-" * 70)
    for scored in scored_chunks:
        print(f"Chunk {scored['chunk_index']} | Score BM25: \033[35m{scored['bm25_score']:.4f}\033[0m")
        print(f"Texto do Chunk:\n{scored['text'].strip()}")
        print("-" * 70)

if __name__ == "__main__":
    main()
