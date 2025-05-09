from transformers import pipeline
from SPARQLWrapper import SPARQLWrapper, JSON
import json
import re

print("Cargando modelo NER...")
ner_pipeline = pipeline("ner", model="Jean-Baptiste/roberta-large-ner-english", aggregation_strategy="simple")

# Configurar SPARQL
sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
sparql.addCustomHttpHeader('User-Agent', 'MyKnowledgeGraphBot/1.0 (contact@example.com)')

# SPARQL mejorada (label + altLabel)
def is_project_in_wikidata(entity_name):
    query = f"""
    SELECT ?project WHERE {{
      {{
        ?project wdt:P31 wd:Q4915012;
                 rdfs:label ?label.
        FILTER(CONTAINS(LCASE(?label), LCASE("{entity_name}")))
      }}
      UNION
      {{
        ?project wdt:P31 wd:Q4915012;
                 skos:altLabel ?altLabel.
        FILTER(CONTAINS(LCASE(?altLabel), LCASE("{entity_name}")))
      }}
    }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return len(results["results"]["bindings"]) > 0
    except Exception as e:
        print(f"Error consultando Wikidata para '{entity_name}': {e}")
        return False

# Extraer candidatos adicionales por regex
def extract_project_candidates(text):
    patterns = [
        r"Horizon 2020",
        r"FP7",
        r"ERC",
        r"Marie Curie",
        r"grant agreement No\.?\s*\d+",
        r"award\s+[A-Za-z0-9\-]+",
        r"project number\s*\d+",
        r"funding from the [A-Z][A-Za-z\s]+",
        r"supported by the [A-Z][A-Za-z\s]+",
        r"funded by the [A-Z][A-Za-z\s]+"
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(re.findall(pattern, text, re.IGNORECASE))
    return candidates

# Cargar JSON
with open("outputs/papers_metadata.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

for idx, paper in enumerate(papers):
    ack_text = paper.get("acknowledgements", "")
    print(f"\nProcesando acknowledgements del paper {idx+1}...")

    # Extraer nombres de NER
    ner_entities = ner_pipeline(ack_text)
    ner_orgs = [ent['word'] for ent in ner_entities if ent['entity_group'] == 'ORG']

    # Extraer por regex
    regex_candidates = extract_project_candidates(ack_text)

    # Combinar todos los nombres únicos
    all_candidates = set(ner_orgs + regex_candidates)

    projects = []
    organizations = []

    for name in all_candidates:
        print(f"Consultando Wikidata para: {name}")
        if is_project_in_wikidata(name):
            print(f"✅ '{name}' identificado como PROJECT")
            projects.append(name)
        else:
            print(f"⚠️ '{name}' no es proyecto (añadiendo como ORGANIZATION)")
            organizations.append(name)

    paper["organizations"] = organizations
    paper["projects"] = projects

# Guardar JSON enriquecido
with open("outputs/papers_metadata_ner.json", "w", encoding="utf-8") as f:
    json.dump(papers, f, indent=2, ensure_ascii=False)

print("\nJSON enriquecido guardado como papers_metadata_ner.json")
