import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Cargar datos
with open("outputs/papers_with_topics.json", "r", encoding="utf-8") as f:
    papers = json.load(f)

# Agrupar abstracts por tema
topic_groups = {}
for paper in papers:
    topic = paper["main_topic"]
    topic_groups.setdefault(topic, []).append(paper)

# Crear carpeta de salida
output_dir = "outputs/similarities_by_topic"
os.makedirs(output_dir, exist_ok=True)

# Calcular similitudes dentro de cada grupo
for topic, group in topic_groups.items():
    abstracts = [p["abstract"] for p in group]
    filenames = [p["filename"] for p in group]

    if len(group) < 2:
        print(f"⚠️ Tema {topic} tiene menos de 2 papers, se omite.")
        continue

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(abstracts)
    sim_matrix = cosine_similarity(tfidf_matrix)

    # Guardar pares únicos
    similarities = []
    for i in range(len(group)):
        for j in range(i + 1, len(group)):
            similarities.append(
                {
                    "paper1": filenames[i],
                    "paper2": filenames[j],
                    "similarity": round(float(sim_matrix[i][j]), 3),
                }
            )

    # Guardar JSON por grupo
    output_path = os.path.join(output_dir, f"topic_{topic}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(similarities, f, indent=2, ensure_ascii=False)

print("✅ Similaridades por tema guardadas en outputs/similarities_by_topic/")
