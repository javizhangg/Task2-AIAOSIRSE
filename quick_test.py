from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF

# Cargar grafo RDF
g = Graph()
g.parse("outputs/knowledge_graph.ttl", format="turtle")

# Namespace
BASE = Namespace("https://example.org/")

# 1. Buscar papers similares a un paper con título específico
def get_similar_papers(title):
    query = f"""
    PREFIX base: <https://example.org/>

    SELECT ?similar_title WHERE {{
        ?paper a base:Paper ;
               base:has_title "{title}" ;
               base:similar_to ?other_paper .

        ?other_paper base:has_title ?similar_title .
    }}
    """
    results = g.query(query)
    print(f"Papers similares a: {title}")
    for row in results:
        print(" -", row.similar_title)

# 2. Ver todos los papers que pertenecen al topic llamado "1", con un mínimo de 0.3 de percentage
def get_papers_for_topic(topic_name="1", min_percentage=0.3):
    query = f"""
    PREFIX base: <https://example.org/>

    SELECT ?title WHERE {{
        ?topic a base:Topic ;
               base:has_name_topic "{topic_name}" .

        ?tb a base:TopicBelonging ;
            base:has_topic ?topic ;
            base:has_paper ?paper ;
            base:has_percentage ?percentage .

        FILTER (?percentage >= {min_percentage})

        ?paper base:has_title ?title .
    }}
    """
    results = g.query(query)
    print(f"Papers que pertenecen al topic {topic_name} con similitud >= {min_percentage}:")
    for row in results:
        print(" -", row.title)

# ---------- Ejemplos de uso ----------
get_similar_papers("Benchmarking machine learning models for predicting aerofoil performance")  # Reemplaza con un título real
print("=========================================================================================0")
get_papers_for_topic("1", min_percentage=0.3)  # Busca por nombre "1" con un mínimo de 0.3 en similitud
