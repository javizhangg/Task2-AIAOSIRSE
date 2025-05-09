from SPARQLWrapper import SPARQLWrapper, JSON
import json
import time
import math

# Configurar SPARQL con User-Agent
sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.addCustomHttpHeader('User-Agent', 'MyKnowledgeGraphBot/1.0 (contact@example.com)')

def batch_query_wikidata(names, instance_type):
    """
    Consulta Wikidata para una lista de nombres y devuelve diccionario {name: enriched_data}.
    """
    if instance_type == "project":
        instance_of_q = "Q4915012"  # research project
    elif instance_type == "organization":
        instance_of_q = "Q43229"  # organization
    else:
        return {}

    # Construir VALUES
    values_clause = " ".join(f'"{name}"' for name in names)
    query = f"""
    SELECT ?entity ?entityLabel ?searchName ?countryLabel ?website ?startDate ?endDate ?funderLabel ?founderLabel ?createdDate WHERE {{
      VALUES ?searchName {{ {values_clause} }}
      ?entity wdt:P31 wd:{instance_of_q} ;
              rdfs:label ?entityLabel .
      FILTER(CONTAINS(LCASE(?entityLabel), LCASE(?searchName)))
      OPTIONAL {{ ?entity wdt:P17 ?country . }}
      OPTIONAL {{ ?entity wdt:P856 ?website . }}
      OPTIONAL {{ ?entity wdt:P580 ?startDate . }}
      OPTIONAL {{ ?entity wdt:P582 ?endDate . }}
      OPTIONAL {{ ?entity wdt:P859 ?funder . }}
      OPTIONAL {{ ?entity wdt:P112 ?founder . }}
      OPTIONAL {{ ?entity wdt:P571 ?createdDate . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
        enriched_data = {}
        for res in results["results"]["bindings"]:
            key = res["searchName"]["value"]
            enriched_data[key] = {
                "wikidata_uri": res["entity"]["value"],
                "label": res.get("entityLabel", {}).get("value"),
                "country": res.get("countryLabel", {}).get("value"),
                "website": res.get("website", {}).get("value"),
                "start_date": res.get("startDate", {}).get("value"),
                "end_date": res.get("endDate", {}).get("value"),
                "funder": res.get("funderLabel", {}).get("value"),
                "founder": res.get("founderLabel", {}).get("value"),
                "created_date": res.get("createdDate", {}).get("value"),
            }
        return enriched_data
    except Exception as e:
        print(f"Error en batch query: {e}")
        return {}

# Cargar JSON original
with open("outputs/papers_metadata_ner.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

# Recolectar todas las organizaciones y proyectos únicas
all_orgs = set()
all_projects = set()

for paper in papers:
    all_orgs.update(paper.get("organizations", []))
    all_projects.update(paper.get("projects", []))

print(f"\nTotal organizaciones únicas: {len(all_orgs)}")
print(f"Total proyectos únicos: {len(all_projects)}")

# Procesar en lotes (ejemplo: 10 entidades por lote)
BATCH_SIZE = 10

def process_in_batches(all_names, instance_type):
    all_enriched = {}
    name_list = list(all_names)
    num_batches = math.ceil(len(name_list) / BATCH_SIZE)

    for i in range(num_batches):
        batch = name_list[i*BATCH_SIZE : (i+1)*BATCH_SIZE]
        print(f"Consultando batch {i+1}/{num_batches}: {batch}")
        enriched = batch_query_wikidata(batch, instance_type)
        all_enriched.update(enriched)
        time.sleep(1)  # evitar bloqueo

    return all_enriched

# Consultar organizaciones y proyectos
enriched_orgs_dict = process_in_batches(all_orgs, "organization")
enriched_projects_dict = process_in_batches(all_projects, "project")

# Mapear resultados al JSON original
for idx, paper in enumerate(papers):
    enriched_orgs = []
    enriched_projects = []

    for org in paper.get("organizations", []):
        if org in enriched_orgs_dict:
            enriched_orgs.append(enriched_orgs_dict[org])
        else:
            enriched_orgs.append({"name": org, "wikidata_uri": None})

    for proj in paper.get("projects", []):
        if proj in enriched_projects_dict:
            enriched_projects.append(enriched_projects_dict[proj])
        else:
            enriched_projects.append({"name": proj, "wikidata_uri": None})

    paper["enriched_organizations"] = enriched_orgs
    paper["enriched_projects"] = enriched_projects

# Guardar JSON enriquecido
with open("outputs/papers_metadata_wikidata.json", "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)

print("\nJSON enriquecido guardado en outputs/papers_metadata_wikidata.json")
