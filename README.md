# Task2-AIAOSIRSE

//lo que tiene que instalar el conda para que funcione bien el json to rdf

Funcionalidades hasta ahora, para poder extraer los metadatos con grobid necesitas activar grobid
depues importa mi_entorno con el comando

```bash
conda env create -f environment.yml
conda activate mi_entorno
python grobid.py
python jsonToRDF.py
```

con eso tienes ya lo de los papers_metadatos con grobid.py y el kg principal el mas sencillo con jsonToRDF.py, si quieres sacarle las organizaciones y los projectoso de acknowledges es haciendo

```bash
python ner.py
```

se genera los papaer metadata ner.json despues de eso esta en prueba lo de la alimentacion de con wikidata(wikidata.pyt).
si quieres probar se puede hacer con

```bash
python wikidata.py
```

https://drive.google.com/file/d/1heVXqSL_hGMyUH_ERv-NbrnHFA24A0xB/view?usp=sharing
enlace draw.io de los diagramas

te deborveria paper_metadata_wikidata.json
la ontology.ttl muesta el kg de los metadatos sin estender y el ontology_enhanced.ttl muestra el kg extendido con orgs y project faltaria lo de las personas

conda install pytorch torchvision torchaudio cpuonly -c pytorch

### Parte del Topic Modeling y la Similitud entre Papers

---

## Reflexión final

Durante esta parte de la práctica se exploraron dos enfoques distintos para analizar un conjunto de papers científicos: el agrupamiento por temas (_topic modeling_ con LDA) y el cálculo de similitud entre abstracts.

Inicialmente, se usó TF-IDF para medir similitud textual, pero los valores obtenidos eran demasiado bajos y no representaban bien la relación entre documentos. Esto se debía a que TF-IDF solo compara palabras exactas y no es capaz de interpretar el significado de las frases.

Posteriormente, se utilizó el modelo `sentence-transformers` (`all-MiniLM-L6-v2`, obtenido de HuggingFace) para calcular **similaridad semántica** entre abstracts. Este modelo permitió obtener valores mucho más realistas, ya que interpreta el contenido a nivel conceptual y no únicamente lexical.

Finalmente, se optó por:

- **Usar LDA para identificar temas generales entre los papers.**
- **Usar embeddings semánticos para medir similitud real entre papers dentro de cada tema.**

Esta combinación proporciona una visión estructurada (por temas) y precisa (por contenido), permitiendo construir representaciones más útiles y coherentes para analizar el corpus científico.

---

## Análisis de Temas y Similitud Semántica entre Papers

Esta parte de la práctica se centra en **analizar automáticamente un conjunto de artículos científicos** para:

1. **Agruparlos por temas comunes** mediante _topic modeling_ (LDA).
2. **Medir qué tan similares son entre sí** los abstracts usando embeddings semánticos.

---

## ▶️ Cómo ejecutar los scripts

A continuación se indican los pasos para ejecutar los análisis de temas y similitud semántica entre papers.

---

### 1. ✅ Requisitos (Habiendo usado lo del conda de antes)

```bash
pip install gensim nltk sentence-transformers
```

### Scripts utilizados

#### `analisis_topic_similarities.py`

Luego para ejecutarlo hay que usar este comando:

```bash
python analisis_topic_similarities.py
```

Este script fue el punto de partida y realiza:

- **Topic modeling con LDA**: descubre temas ocultos en los abstracts.
- **Similaridad general (TF-IDF + cosine)**: mide la similitud entre todos los pares de abstracts usando vectorización clásica.

> Este script se considera **obsoleto** como versión final, ya que la similitud TF-IDF no capturaba bien el contenido real de los textos.

**Salidas generadas**:

- `papers_with_topics.json`
- `abstract_similarities.json`

---

#### `similarities_by_topic_semantic.py`

Luego para ejecutarlo hay que usar este comando:

```bash
python similarities_by_topic_semantic.py
```

Este es el **script final y recomendado**. Realiza lo siguiente:

- Agrupa los papers por su tema principal (`main_topic`), calculado por el modelo LDA.
- Calcula **la similitud semántica** entre los abstracts de cada grupo temático utilizando `sentence-transformers`.

**Salida generada**:

- Archivos `.json` por tema, con pares de papers y su similitud semántica real, en:
  `outputs/similarities_semantic_by_topic/topic_X.json`

---

#### `similarities_by_topic_TF-IDF.py` (versión alternativa)

Luego para ejecutarlo hay que usar este comando:

```bash
python similarities_by_topic_TF.py
```

Este script replica el enfoque anterior pero usando **TF-IDF** en lugar de embeddings.
Se conserva únicamente como referencia para mostrar en la presentación por qué se decidió **migrar a un modelo semántico**.

**Salida generada**:

- Archivos `.json` por tema con similitud TF-IDF, en:
  `outputs/similarities_by_topic/topic_X.json`

---

### Justificación del enfoque final

- **LDA** es ideal para **descubrir temas comunes** y dar estructura al conjunto de documentos.
- **TF-IDF** resultó poco útil al aplicar similitud, ya que muchos abstracts hablaban de _machine learning_ pero aplicado a campos muy distintos y con vocabulario técnico diferente.
- **Embeddings semánticos** (`sentence-transformers`) ofrecieron una mejor medición del contenido real, permitiendo identificar relaciones reales entre papers más allá del vocabulario exacto.

Este enfoque mixto permite obtener agrupaciones temáticas coherentes y relaciones relevantes dentro de cada tema.

```

```
