from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import json
import uuid

# Cargar JSON enriquecido
with open("outputs/papers_metadata_enriched.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

# Crear grafo
g = Graph()

# Namespace de tu ontología
BASE = Namespace("http://www.owl-ontologies.com/base#")
g.bind("base", BASE)


for idx, paper in enumerate(papers):
    paper_id = f"Paper_{idx+1}"
    paper_uri = URIRef(BASE + paper_id)

    # Añadir clase Paper
    g.add((paper_uri, RDF.type, BASE.Paper))

    # Añadir título y fecha
    g.add((paper_uri, BASE.has_title, Literal(paper["title"])))
    g.add((paper_uri, BASE.has_date, Literal(paper["publication_date"])))

    # Autores
    for author_name in paper.get("authors", []):
        person_id = f"Person_{uuid.uuid4().hex[:8]}"
        person_uri = URIRef(BASE + person_id)

        g.add((person_uri, RDF.type, BASE.Person))
        g.add((person_uri, BASE.has_name, Literal(author_name)))

        # Relacionar paper -> has_author -> person
        g.add((paper_uri, BASE.has_author, person_uri))

    # Referencias
    for ref_idx, ref in enumerate(paper.get("references", [])):
        ref_paper_id = f"Reference_{idx+1}_{ref_idx+1}"
        ref_uri = URIRef(BASE + ref_paper_id)

        g.add((ref_uri, RDF.type, BASE.Paper))
        if ref.get("title"):
            g.add((ref_uri, BASE.has_title, Literal(ref["title"])))
        if ref.get("identifier"):
            g.add((ref_uri, BASE.references, Literal(ref["identifier"])))

        # Relación paper -> similar_to
        g.add((paper_uri, BASE.similar_to, ref_uri))

    # Organizaciones extraídas por NER desde el JSON enriquecido
    for org_name in paper.get("organizations", []):
        org_id = f"Org_{uuid.uuid4().hex[:8]}"
        org_uri = URIRef(BASE + org_id)
        g.add((org_uri, RDF.type, BASE.Organization))
        g.add((org_uri, BASE.has_name_organization, Literal(org_name)))
        g.add((paper_uri, BASE.acknowledges, org_uri))

# Guardar como Turtle
g.serialize("outputs/knowledge_graph.ttl", format="turtle")
print("Knowledge graph guardado en outputs/knowledge_graph_enriched.ttl")
