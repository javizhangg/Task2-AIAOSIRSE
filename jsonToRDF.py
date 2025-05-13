from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import json
import uuid
import glob
import os

# Cargar JSON enriquecido
with open("outputs/papers_metadata.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

# Cargar información adicional extraída de person.py (por ejemplo, nombres alternativos, identificadores externos, etc.)
with open("outputs/enriched_authors.json", "r", encoding="utf-8") as f:
    enriched_authors_data = json.load(f)

# Crear grafo
g = Graph()

# Namespace de tu ontología
BASE = Namespace("http://www.owl-ontologies.com/base#")
g.bind("base", BASE)

# Paper index -> URI mapping para reutilizar URIs entre relaciones
paper_uri_map = {}

# Función para obtener datos enriquecidos del autor
def get_enriched_author_info(author_name):
    for paper in papers:
        for author in paper.get("authors", []):
            if author["name"] == author_name:
                # Match author, extract corresponding enriched data
                return next((item for item in enriched_authors_data if item["full_name"] == author_name), None)
    return None

for idx, paper in enumerate(papers):
    paper_id = f"Paper_{idx+1}"
    paper_uri = URIRef(BASE + paper_id)

    # Añadir clase Paper
    g.add((paper_uri, RDF.type, BASE.Paper))

    # Añadir título y fecha
    g.add((paper_uri, BASE.has_title, Literal(paper["title"])))
    g.add((paper_uri, BASE.has_date, Literal(paper["publication_date"])))

    # Autores
    for author in paper.get("authors", []):
        person_id = f"Person_{uuid.uuid4().hex[:8]}"
        person_uri = URIRef(BASE + person_id)

        # Añadir la clase Person
        g.add((person_uri, RDF.type, BASE.Person))
        g.add((person_uri, BASE.has_name, Literal(author["name"])))

        # Obtener información enriquecida para el autor
        enriched_info = get_enriched_author_info(author["name"])
        if enriched_info:
            # Añadir otras propiedades enriquecidas del autor
            if enriched_info.get("work_count"):
                g.add((person_uri, BASE.has_work_count, Literal(enriched_info["work_count"])))
            if enriched_info.get("other_names"):
                for other_name in enriched_info["other_names"]:
                    g.add((person_uri, BASE.has_other_name, Literal(other_name)))
            if enriched_info.get("external_ids"):
                for ext_id in enriched_info["external_ids"]:
                    if ext_id.get("type") == "ORCID":
                        g.add((person_uri, BASE.has_orcid, Literal(ext_id.get("value"))))

            # Añadir las URLs del investigador
            if enriched_info.get("researcher_urls"):
                for url in enriched_info["researcher_urls"]:
                    g.add((person_uri, BASE.has_researcher_url, Literal(url.get("url"))))

            # Añadir educación y empleos (si los hay)
            for edu in enriched_info.get("education", []):
                if edu.get("institution"):
                    g.add((person_uri, BASE.has_education_institution, Literal(edu["institution"])))
                if edu.get("city"):
                    g.add((person_uri, BASE.has_education_city, Literal(edu["city"])))
                if edu.get("country"):
                    g.add((person_uri, BASE.has_education_country, Literal(edu["country"])))

            for emp in enriched_info.get("employment", []):
                if emp.get("institution"):
                    g.add((person_uri, BASE.has_employment_institution, Literal(emp["institution"])))
                if emp.get("city"):
                    g.add((person_uri, BASE.has_employment_city, Literal(emp["city"])))
                if emp.get("country"):
                    g.add((person_uri, BASE.has_employment_country, Literal(emp["country"])))

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
            g.add((ref_uri, BASE.has_identifier, Literal(ref["identifier"])))

        # Relación paper -> references
        g.add((paper_uri, BASE.references, ref_uri))

    # Organizaciones extraídas por NER desde el JSON enriquecido
    for org_name in paper.get("organizations", []):
        org_id = f"Org_{uuid.uuid4().hex[:8]}"
        org_uri = URIRef(BASE + org_id)
        g.add((org_uri, RDF.type, BASE.Organization))
        g.add((org_uri, BASE.has_name_organization, Literal(org_name)))
        g.add((paper_uri, BASE.acknowledges, org_uri))

#  Añadir relaciones de similitud semántica entre papers
similarity_folder = "outputs/similarities_semantic_by_topic/"
if os.path.exists(similarity_folder):
    for file_path in glob.glob(os.path.join(similarity_folder, "topic_*.json")):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for relation in data:
                paper1 = relation["paper1"]
                paper2 = relation["paper2"]
                uri1 = paper_uri_map.get(paper1)
                uri2 = paper_uri_map.get(paper2)
                if uri1 and uri2:
                    g.add((uri1, BASE.similar_to, uri2))

# Guardar como Turtle
g.serialize("outputs/knowledge_graph.ttl", format="turtle")
print("Knowledge graph guardado en outputs/knowledge_graph_enriched.ttl")
