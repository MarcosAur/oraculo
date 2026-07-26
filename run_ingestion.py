import sys
sys.path.append("src")
from pipelines import IngestionPipeline

# Edict base text
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
    print(" INICIANDO PIPELINE DE INGESTÃO DE DADOS ")
    print("=" * 60)
    
    pipeline = IngestionPipeline()
    pipeline.run(BASE_TEXT)
    
    print("=" * 60)
    print(" PIPELINE DE INGESTÃO CONCLUÍDO ")
    print("=" * 60)

if __name__ == "__main__":
    main()
