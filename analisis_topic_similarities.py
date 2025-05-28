import json
import gensim
from gensim import corpora
from gensim.models import CoherenceModel
from gensim.parsing.preprocessing import STOPWORDS as gensim_stopwords
from nltk.tokenize import wordpunct_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import matplotlib.pyplot as plt

# Definición de selección automática del número óptimo de tópicos


def find_best_lda_coherence(dictionary, corpus, texts, start=2, end=15, step=1):
    """
    Entrena modelos LDA variando K desde 'start' hasta 'end', calcula coherencia UMass y devuelve
    el modelo con la mejor coherencia.
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
        print(f" → Coherencia UMass: {coherence:.4f}")

        if coherence > best_coherence:
            best_coherence = coherence
            best_model = model
            best_num_topics = num_topics

    print(
        f"\n Mejor número de tópicos: {best_num_topics} con coherencia UMass {best_coherence:.4f}"
    )
    return best_model


def main():
    # Rutas de entrada y salida
    input_path = "outputs/papers_metadata.json"
    output_topics_path = "outputs/papers_with_topics.json"
    output_similarity_path = "outputs/abstract_similarities.json"

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"No se encontró: {input_path}")

    # Carga de datos
    with open(input_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    # Preprocesamiento de abstracts sin recursos externos de NLTK
    stop_words = set(gensim_stopwords)
    texts = []
    raw_texts = []
    for paper in papers:
        abs_text = paper.get("abstract", "")
        raw_texts.append(abs_text)
        # Tokenización con wordpunct_tokenize (regex)
        tokens = wordpunct_tokenize(abs_text.lower())
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

    # Similitud TF-IDF + coseno
    vectorizer = TfidfVectorizer()
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
