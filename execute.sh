#!/bin/bash
set -e

echo " Ejecutando pipeline completo..."

echo "1. Extracción GROBID"
python grobid.py

echo "2. NER (organizaciones/proyectos)"
python ner.py

echo "3. Enriquecimiento de autores (ORCID)"
python person.py

echo "4. Enriquecimiento Wikidata"
python wikidata.py

echo "5. Topic Modeling + similitud TF-IDF"
python analisis_topic_similarities.py

echo "6. Similitud semántica por tópico"
python similarities_by_topic_semantic.py

echo "7. Exportando a RDF"
python jsonToRDF.py

echo "8. Lanzando app Streamlit"
exec streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.address=0.0.0.0