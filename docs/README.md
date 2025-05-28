# Task2-AIAOSIRSE: Knowledge Graph of Scientific Papers Enhanced with ORCID and Wikidata Metadata

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15525833.svg)](https://doi.org/10.5281/zenodo.15525833)

Clonar repositorio antes de hacer nada.

```bash
git clone https://github.com/javizhangg/Task2-AIAOSIRSE.git
```

## Diagrama del proceso

https://drive.google.com/file/d/12_EM-y5ptJhGotsEJ1NyPQciONYfK82P/view?usp=sharing

```bash
conda env create -f environment.yml
conda activate mi_entorno
python grobid.py
```

También puedes ejecutar todo el proceso directamente con Docker:

```bash
docker-compose up --build
```

## Extracción de Metadatos (`grobid.py`)

El script `grobid.py` utiliza la herramienta GROBID para procesar artículos científicos en formato PDF y extraer metadatos estructurados.

- **Título del paper**
- **Fecha de publicación**
- **Autores**:
  - Nombre completo
  - Afiliación asociada (si está disponible y correctamente vinculada)
- **Resumen (abstract)**, si está presente
- **Referencias**:
  - Título del paper citado
  - Autores (si están disponibles)
  - Año de publicación

El resultado se guarda en el archivo:

```
outputs/papers_metadata.json
```

Este archivo es la base para los procesos posteriores de enriquecimiento (NER, ORCID, Wikidata, RDF...).

---

Devuelve `papers_metadata.json` 

```bash
python ner.py
```

Devuelve `papers_metadata_ner.json` 

```bash
python wikidata.py
```
Devuelve `paper_metadata_wikidata.json`
`ontology.ttl` muesta el kg de los metadatos sin extender y el 
`ontology_enhanced.ttl` muestra el kg extendido con orgs y project

## Enriquecimiento de Autores desde ORCID (`person.py`)

Este script utiliza la API pública de **ORCID** para buscar información adicional sobre los autores identificados en los metadatos del paper (en `papers_metadata.json`).

---

### Requisitos

1. Credenciales 1de acceso a la API de ORCID:
   - https://orcid.org/developer-tools
   - Registro como desarrollador
   - Creación de API Pública
   - Generación de:
     - `Client ID`
     - `Client Secret`

---

### Uso de las credenciales

- Estas credenciales se usan para obtener un token temporal (`access_token`) que permite acceder a datos públicos de autores.
- Se solicita automáticamente desde el script con:

  ```python
  def fetch_access_token(client_id, client_secret):
      ...
  ```

---

### Script `person.py`

```bash
python person.py
```

1. Lee los autores del archivo `outputs/papers_metadata.json`.
2. Por cada autor:
   - Busca su **ORCID ID** mediante:
     - Fuzzy matching por **afiliación**
     - Coincidencia de **palabras clave** del título del paper en sus trabajos
   - Si se encuentra un ORCID válido se obtienen:
     - Afiliaciones (educación y empleo)
     - Nombres alternativos
     - URLs públicas
     - IDs externos
     - Número total de trabajos

---

### Salida generada

El resultado se guarda como JSON enriquecido en:

```
outputs/enriched_authors.json
```

Este archivo luego es integrado al grafo RDF final mediante el script `jsonToRDF.py`.

---

### Ejemplo de entrada (`papers_metadata.json`)

```json
{
  "title": "...",
  "authors": [
    {
      "name": "...",
      "affiliation": "..."
    }
  ]
}
```

### Ejemplo de salida (`enriched_authors.json`)

```json
{
  "full_name": "...",
  "orcid_id": "0000-0000-0000-0000",
  "employment": [...],
  "education": [...],
  "external_ids": [...],
  "other_names": [...],
  "researcher_urls": [...],
  "work_count": 0
}
```

### Parte del Topic Modeling y la Similitud entre Papers

---

Durante esta parte de la práctica se exploraron dos enfoques distintos para analizar un conjunto de papers científicos: el agrupamiento por temas (_topic modeling_ con LDA) y el cálculo de similitud entre abstracts.

Inicialmente para calcular la similitud entre papers, se usó TF-IDF, pero los valores obtenidos eran demasiado bajos y no representaban bien la relación entre documentos. Esto se debía a que TF-IDF solo compara palabras exactas y no es capaz de interpretar el significado de las frases.

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

### Scripts utilizados

#### `analisis_topic_similarities.py`

Luego para ejecutarlo hay que usar este comando:

```bash
python analisis_topic_similarities.py
```

Este script fue el punto de partida y realiza:

- **Topic modeling con LDA**: distinguimos los diferentes papers a través de un proceso de selección automática del número de tópicos mediante la coherencia UMass, dandonos el número óptimo de tópicos.
- **Similaridad general (TF-IDF + cosine)**: mide la similitud entre todos los pares de abstracts usando vectorización clásica.

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

- Agrupa los papers por su tema principal (`main_topic`), calculado anteriormente por el modelo LDA.
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

## Generación del Grafo de Conocimiento RDF (`jsonToRDF.py`)

Este script construye un grafo semántico en formato RDF/Turtle combinando los metadatos de artículos científicos, información enriquecida de autores, organizaciones y proyectos, y análisis temático y de similitud semántica.

---

### Entrada

Utiliza los archivos generados en las secciones anteriores, almacenados en `outputs/`:

- `papers_metadata.json`: Metadatos de los artículos.
- `enriched_authors.json`: Información extendida de los autores.
- `papers_with_topics.json`: Topic de cada paper.
- `similarities_semantic_by_topic/*.json`: Relación de similitud semántica entre artículos por topic.

---

### Script `jsonToRDF.py`

Por último hay que ejecutar este script para que nos de el grafo enriquecido en `outputs/knowledge_graph.ttl`.
```bash
python jsonToRDF.py
```

1. Carga los datos de entrada.
2. Crea instancias RDF para:
   - Artículos (`Paper`)
   - Autores (`Person`)
   - Organizaciones (`Organization`)
   - Proyectos (`Project`)
   - Topics (`Topic`)
3. Define relaciones entre ellas.
4. Guarda el grafo en `outputs/knowledge_graph.ttl`.

---

### Propiedades RDF (`base:`)

- `has_title`: título del paper o referencia (**artículo original / referencias**).
- `has_date`: fecha de publicación (**artículo original**).
- `has_author`: relación entre un artículo y su(s) autor(es) (**artículo original**).
- `has_orcid`: ID ORCID de un autor (**ORCID**).
- `has_work_count`: cantidad de trabajos del autor (**ORCID**).
- `has_other_name`: otros nombres del autor en ORCID (**ORCID**).
- `has_researcher_url`: URLs públicas asociadas al autor (**ORCID**).
- `has_education_institution`, `has_education_city`, `has_education_country`: educación del autor (**ORCID**).
- `has_employment_institution`, `has_employment_city`, `has_employment_country`: empleo del autor (**ORCID**).
- `references`: relación entre artículos referenciados (**artículo original**).
- `acknowledges`: reconocimiento a una organización o proyecto (**Wikidata**).
- `has_name_organization`: nombre de una organización (**Wikidata**).
- `has_wikidata_uri`: enlace a Wikidata si existe (**Wikidata**).
- `has_funder`: entidad financiadora (**Wikidata**).
- `has_start_date`, `has_end_date`: fechas de existencia de la organización o proyecto (**Wikidata**).
- `has_website`: URL oficial de la entidad (**Wikidata**).
- `has_topic`: relación con el topic principal del artículo (**Topic Modeling**).
- `has_name_topic`: nombre o identificador del topic (**Topic Modeling**).
- `has_percentage`: nivel de pertenencia a un topic (**Topic Modeling**).
- `similar_to`: relación de similitud semántica entre artículos (**Semantic Similarity**).

---

### Flujo de trabajo para Topics y Similarities

1. Carga de asignaciones de tópicos (`outputs/papers_with_topics.json`)

2. Creación de instancias `TopicBelonging`:  
   Para cada paper, se crea una instancia `base:TopicBelonging` que relaciona el paper con el tópico asignado, usando las propiedades:

   - `base:has_paper` → URI del paper
   - `base:has_topic` → URI del tópico
   - `base:has_percentage` → grado de pertenencia (topic_score)

   Esto permite modelar la relación de un paper con un topic y establecer un grado de pertenencia.

3. Carga de asignaciones de similitud (`outputs/similarities_semantic_by_topic/`)

4. Creación de la relación `similar_to`:  
   Si la similitud es mayor a un umbral, se añade la propiedad de manera bidireccional.

---

### Resultado

El grafo de conocimiento se guarda en:

```
outputs/knowledge_graph.ttl
```

## Prueba (`quicktest.py`)

Este script realiza un par de consultas sobre el grafo RDF generado.

### Consultas

- `get_similar_papers(title)`  
  Busca y lista papers similares a un paper dado por su título.  
  **Consulta:** tripletas con la propiedad `similar_to` entre papers.  
  **Origen de datos:** relaciones de similitud semántica.

- `get_papers_for_topic(topic_name, min_percentage)`  
  Lista papers asociados a un topic específico, filtrando por un nivel mínimo de pertenencia.  
  **Consulta:** tripletas que vinculan `TopicBelonging` con `Topic` y `Paper`, usando propiedades `has_topic`, `has_paper` y `has_percentage`.  
  **Origen de datos:** asignación de topics a papers.

## Interfaz Interactiva (`streamlit_app.py`)

Este script genera en una aplicación web con la librería Streamlit donde el usuario puede interactuar con el Knowledge Graph mediante un motor de búsqueda.

Para activarlo, simplemente ejecutar el comando

```bash
streamlit run streamlit_app.py
```

La aplicación presenta filtros que poder aplicar a la búsqueda (por categoría, por tópico, umbral de pertenencia al tópico...) además de un modo de búsqueda avanzada para realizar consultas personalizadas al KG mediante SparSQL.

## 📖 Documentación

La documentación completa del proyecto está disponible en:

👉 [https://task2-aiaosirse.readthedocs.io/es/latest/](https://task2-aiaosirse.readthedocs.io/es/latest/)


## LICENCE

Este proyecto se publica bajo la Licencia Apache 2.0 — consulta el archivo `LICENSE`.

## CITATION

Si reutilizas este codigo, datos o idea citanos siguiendo `CITATION.cff`
