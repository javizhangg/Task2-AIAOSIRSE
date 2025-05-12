import json
import os
from sentence_transformers import SentenceTransformer, util

# Cargar los papers ya clasificados por tema
with open("outputs/papers_with_topics.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

# Agrupar por tema
topic_groups = {}
for paper in papers:
    topic = paper["main_topic"]
    topic_groups.setdefault(topic, []).append(paper)

# Crear carpeta de salida
output_dir = "outputs/similarities_semantic_by_topic"
os.makedirs(output_dir, exist_ok=True)

# Cargar modelo preentrenado
print("Cargando modelo de embeddings...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Calcular similitud semántica por grupo
for topic, group in topic_groups.items():
    if len(group) < 2:
        print(f"Tema {topic} tiene menos de 2 papers. Se omite.")
        continue

    abstracts = [p["abstract"] for p in group]
    filenames = [p["filename"] for p in group]

    # Codificar los abstracts como vectores
    embeddings = model.encode(abstracts, convert_to_tensor=True)

    # Calcular similitudes
    cosine_scores = util.pytorch_cos_sim(embeddings, embeddings).cpu().numpy()

    similarities = []
    for i in range(len(group)):
        for j in range(i + 1, len(group)):
            similarities.append(
                {
                    "paper1": filenames[i],
                    "paper2": filenames[j],
                    "similarity": round(float(cosine_scores[i][j]), 3),
                }
            )

    # Guardar resultados
    output_path = os.path.join(output_dir, f"topic_{topic}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(similarities, f, indent=2, ensure_ascii=False)

print("Similaridades semánticas guardadas en outputs/similarities_semantic_by_topic/")
