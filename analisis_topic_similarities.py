import json
import gensim
from gensim import corpora, models
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
import os

# Descargar recursos NLTK (solo la primera vez que ejecutes)
nltk.download("punkt")
nltk.download("stopwords")

# Rutas
input_path = "outputs/papers_metadata.json"
output_topics_path = "outputs/papers_with_topics.json"
output_similarity_path = "outputs/abstract_similarities.json"

# Cargar JSON
if not os.path.exists(input_path):
    raise FileNotFoundError(f"No se encontró el archivo: {input_path}")

with open(input_path, "r", encoding="utf-8") as f:
    papers = json.load(f)

# Preprocesamiento básico
stop_words = set(stopwords.words("english"))
processed_texts = []
raw_texts = []

for paper in papers:
    abstract = paper.get("abstract", "")
    raw_texts.append(abstract)
    tokens = word_tokenize(abstract.lower())
    filtered_tokens = [w for w in tokens if w.isalpha() and w not in stop_words]
    processed_texts.append(filtered_tokens)

# --- TOPIC MODELING (LDA) ---
dictionary = corpora.Dictionary(processed_texts)
corpus = [dictionary.doc2bow(text) for text in processed_texts]

lda_model = gensim.models.LdaModel(corpus, num_topics=5, id2word=dictionary, passes=15)

papers_with_topics = []
for paper, bow in zip(papers, corpus):
    topic_probs = lda_model.get_document_topics(bow)
    main_topic = max(topic_probs, key=lambda x: x[1])
    papers_with_topics.append(
        {
            "filename": paper.get("filename", ""),
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", ""),
            "main_topic": main_topic[0],
            "topic_score": float(round(main_topic[1], 3)),
        }
    )

# Guardar resultados del topic modeling
with open(output_topics_path, "w", encoding="utf-8") as f:
    json.dump(papers_with_topics, f, indent=2, ensure_ascii=False)

# --- SIMILARIDAD ENTRE ABSTRACTS (TF-IDF + Cosine Similarity) ---
vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = vectorizer.fit_transform(raw_texts)

cosine_sim_matrix = cosine_similarity(tfidf_matrix)

# Convertir a lista de pares únicos
similarities = []
num_papers = len(papers)
for i in range(num_papers):
    for j in range(i + 1, num_papers):
        sim_score = float(cosine_sim_matrix[i][j])
        similarities.append(
            {
                "paper1": papers[i].get("filename", f"paper_{i+1}"),
                "paper2": papers[j].get("filename", f"paper_{j+1}"),
                "similarity": round(sim_score, 3),
            }
        )

# Guardar resultados de similitud
with open(output_similarity_path, "w", encoding="utf-8") as f:
    json.dump(similarities, f, indent=2, ensure_ascii=False)

print("✅ Análisis completado")
print(f"📁 Temas por paper guardados en: {output_topics_path}")
print(f"📁 Similitudes entre abstracts guardadas en: {output_similarity_path}")
