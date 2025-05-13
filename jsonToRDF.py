from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
import json
import uuid
import glob
import os

# Cargar datos de entrada
with open("outputs/papers_metadata.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

with open("outputs/enriched_authors.json", "r", encoding="utf-8") as f:
    enriched_authors_data = json.load(f)

# Crear grafo y namespace
g = Graph()
BASE = Namespace("https://example.org/")
g.bind("base", BASE)

paper_uri_map = {}

def get_enriched_author_info(author_name):
    return next((item for item in enriched_authors_data if item["full_name"] == author_name), None)

for idx, paper in enumerate(papers):
    paper_id = f"Paper_{idx+1}"
    paper_uri = URIRef(BASE + paper_id)
    paper_uri_map[paper["filename"]] = paper_uri  # map título para uso en similar_to
    g.add((paper_uri, RDF.type, BASE.Paper))
    g.add((paper_uri, BASE.has_title, Literal(paper["title"])))
    g.add((paper_uri, BASE.has_date, Literal(paper["publication_date"])))

    for author in paper.get("authors", []):
        person_id = f"Person_{uuid.uuid4().hex[:8]}"
        person_uri = URIRef(BASE + person_id)
        g.add((person_uri, RDF.type, BASE.Person))
        g.add((person_uri, BASE.has_name, Literal(author["name"])))

        enriched_info = get_enriched_author_info(author["name"])
        if enriched_info:
            if enriched_info.get("work_count"):
                g.add((person_uri, BASE.has_work_count, Literal(enriched_info["work_count"])))
            if enriched_info.get("other_names"):
                for other_name in enriched_info["other_names"]:
                    g.add((person_uri, BASE.has_other_name, Literal(other_name)))
            if enriched_info.get("external_ids"):
                for ext_id in enriched_info["external_ids"]:
                    if ext_id.get("type") == "ORCID":
                        g.add((person_uri, BASE.has_orcid, Literal(ext_id.get("value"))))
            if enriched_info.get("researcher_urls"):
                for url in enriched_info["researcher_urls"]:
                    g.add((person_uri, BASE.has_researcher_url, Literal(url.get("url"))))
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
        g.add((paper_uri, BASE.references, ref_uri))

    # Organizaciones enriquecidas
    for org in paper.get("enriched_organizations", []):
        org_id = f"Org_{uuid.uuid4().hex[:8]}"
        org_uri = URIRef(BASE + org_id)
        g.add((org_uri, RDF.type, BASE.Organization))
        if org.get("label"):
            g.add((org_uri, BASE.has_name_organization, Literal(org["label"])))
        elif org.get("name"):
            g.add((org_uri, BASE.has_name_organization, Literal(org["name"])))
        if org.get("wikidata_uri"):
            g.add((org_uri, BASE.has_wikidata_uri, Literal(org["wikidata_uri"])))
        if org.get("country"):
            g.add((org_uri, BASE.has_located_country, Literal(org["country"])))
        if org.get("website"):
            g.add((org_uri, BASE.has_website, Literal(org["website"])))
        if org.get("start_date"):
            g.add((org_uri, BASE.has_start_date, Literal(org["start_date"])))
        if org.get("end_date"):
            g.add((org_uri, BASE.has_end_date, Literal(org["end_date"])))
        if org.get("funder"):
            g.add((org_uri, BASE.has_funder, Literal(org["funder"])))
        g.add((paper_uri, BASE.acknowledges, org_uri))

    # Proyectos enriquecidos
    for proj in paper.get("enriched_projects", []):
        proj_id = f"Project_{uuid.uuid4().hex[:8]}"
        proj_uri = URIRef(BASE + proj_id)
        g.add((proj_uri, RDF.type, BASE.Project))
        if proj.get("label"):
            g.add((proj_uri, BASE.has_id_project, Literal(proj["label"])))
        if proj.get("wikidata_uri"):
            g.add((proj_uri, BASE.has_wikidata_uri, Literal(proj["wikidata_uri"])))
        if proj.get("country"):
            g.add((proj_uri, BASE.has_located_country, Literal(proj["country"])))
        if proj.get("website"):
            g.add((proj_uri, BASE.has_website, Literal(proj["website"])))
        if proj.get("start_date"):
            g.add((proj_uri, BASE.has_start_date, Literal(proj["start_date"])))
        if proj.get("end_date"):
            g.add((proj_uri, BASE.has_end_date, Literal(proj["end_date"])))
        if proj.get("funder"):
            g.add((proj_uri, BASE.has_funder, Literal(proj["funder"])))

# ------------------------
# Añadir Topics y Similitud
# ------------------------
similarity_folder = "outputs/similarities_semantic_by_topic/"
if os.path.exists(similarity_folder):
    for file_path in glob.glob(os.path.join(similarity_folder, "topic_*.json")):
        topic_name = os.path.splitext(os.path.basename(file_path))[0].replace("topic_", "")
        topic_uri = URIRef(BASE + f"Topic_{topic_name}")
        g.add((topic_uri, RDF.type, BASE.Topic))
        g.add((topic_uri, BASE.has_name_topic, Literal(topic_name)))

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for relation in data:
                paper1_title = relation["paper1"]
                paper2_title = relation["paper2"]
                similarity = relation.get("similarity", None)

                uri1 = paper_uri_map.get(paper1_title)
                uri2 = paper_uri_map.get(paper2_title)

                if uri1 and uri2:
                    print(uri1)
                    # Similaridad entre papers
                    g.add((uri1, BASE.similar_to, uri2))

                    # TopicBelonging paper1
                    tb1_id = f"TB_{uuid.uuid4().hex[:8]}"
                    tb1_uri = URIRef(BASE + tb1_id)
                    g.add((tb1_uri, RDF.type, BASE.TopicBelonging))
                    g.add((tb1_uri, BASE.has_paper, uri1))
                    g.add((tb1_uri, BASE.has_topic, topic_uri))
                    if similarity:
                        g.add((tb1_uri, BASE.has_percentage, Literal(float(similarity))))

                    # TopicBelonging paper2
                    tb2_id = f"TB_{uuid.uuid4().hex[:8]}"
                    tb2_uri = URIRef(BASE + tb2_id)
                    g.add((tb2_uri, RDF.type, BASE.TopicBelonging))
                    g.add((tb2_uri, BASE.has_paper, uri2))
                    g.add((tb2_uri, BASE.has_topic, topic_uri))
                    if similarity:
                        g.add((tb2_uri, BASE.has_percentage, Literal(float(similarity))))

# Guardar como Turtle
g.serialize("outputs/knowledge_graph.ttl", format="turtle")
print("Knowledge graph guardado en outputs/knowledge_graph.ttl")
