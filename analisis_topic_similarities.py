import json
import gensim
from gensim import corpora
from gensim.models import CoherenceModel
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
import os
import matplotlib.pyplot as plt

# Descargar recursos NLTK (solo la primera vez que ejecutes)
nltk.download("punkt", quiet=True)
nltk.download("stopwords", quiet=True)


def find_best_lda_coherence(dictionary, corpus, texts, start=2, end=15, step=1):
    """
    Proceso de selección automática del número óptimo de tópicos usando coherencia UMass.
    Entrena modelos LDA variando K desde 'start' hasta 'end' y devuelve el modelo con
    mayor coherencia (u_mass).
    """
    best_model = None
    best_num_topics = start
    best_coherence = float("-inf")
    coherence_values = []

    for num_topics in range(start, end + 1, step):
        print(f"Entrenando modelo con {num_topics} tópicos...")
        model = gensim.models.LdaModel(
            corpus=corpus,
            id2word=dictionary,
            num_topics=num_topics,
            passes=5,
            random_state=42,
            per_word_topics=False,
            eval_every=None,
        )
        cm = CoherenceModel(
            model=model, corpus=corpus, dictionary=dictionary, coherence="u_mass"
        )
        coherence = cm.get_coherence()
        coherence_values.append((num_topics, coherence))
        print(f" → Coherencia u_mass: {coherence:.4f}")

        if coherence > best_coherence:
            best_coherence = coherence
            best_model = model
            best_num_topics = num_topics

    # Gráfica de coherencia vs num_topics
    x, y = zip(*coherence_values)
    plt.figure(figsize=(8, 4))
    plt.plot(x, y, marker="o")
    plt.xlabel("Número de tópicos")
    plt.ylabel("Coherencia UMass")
    plt.title("Selección del número óptimo de tópicos (UMass)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    print(
        f"\n✅ Mejor número de tópicos: {best_num_topics} con coherencia UMass {best_coherence:.4f}"
    )
    return best_model


def main():
    # Rutas de entrada y salida
    input_path = "outputs/papers_metadata.json"
    output_topics_path = "outputs/papers_with_topics.json"
    output_similarity_path = "outputs/abstract_similarities.json"

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"No se encontró: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    # Preprocesamiento de abstracts
    stop_words = set(stopwords.words("english"))
    texts = []
    raw_texts = []
    for paper in papers:
        abs_text = paper.get("abstract", "")
        raw_texts.append(abs_text)
        tokens = word_tokenize(abs_text.lower())
        tokens = [t for t in tokens if t.isalpha() and t not in stop_words]
        texts.append(tokens)

    # Crear diccionario y corpus para LDA
    dictionary = corpora.Dictionary(texts)
    corpus = [dictionary.doc2bow(t) for t in texts]

    # Selección de tópicos usando coherencia UMass
    lda_model = find_best_lda_coherence(dictionary, corpus, texts, start=2, end=15)

    # Asignar tópico principal a cada paper
    papers_with_topics = []
    for paper, bow in zip(papers, corpus):
        topic_probs = lda_model.get_document_topics(bow)
        main = max(topic_probs, key=lambda x: x[1])
        papers_with_topics.append(
            {
                "filename": paper.get("filename", ""),
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", ""),
                "main_topic": main[0],
                "topic_score": float(round(main[1], 3)),
            }
        )

    # Guardar resultados de topic modeling
    with open(output_topics_path, "w", encoding="utf-8") as f:
        json.dump(papers_with_topics, f, indent=2, ensure_ascii=False)
    print(f"Temas guardados en: {output_topics_path}")

    # Similitud TF-IDF + Coseno
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(raw_texts)
    cosine_sim_matrix = cosine_similarity(tfidf_matrix)

    # Guardar similitudes en JSON
    similarities = []
    n = len(papers)
    for i in range(n):
        for j in range(i + 1, n):
            similarities.append(
                {
                    "paper1": papers[i].get("filename", ""),
                    "paper2": papers[j].get("filename", ""),
                    "similarity": round(float(cosine_sim_matrix[i, j]), 3),
                }
            )
    with open(output_similarity_path, "w", encoding="utf-8") as f:
        json.dump(similarities, f, indent=2, ensure_ascii=False)
    print(f"Similitudes guardadas en: {output_similarity_path}")


if __name__ == "__main__":
    main()
