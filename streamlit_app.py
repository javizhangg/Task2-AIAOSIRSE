"""
# My first app
Here's our first attempt at using data to create a table:
"""

import streamlit as st
from rdflib import Graph
import pandas as pd
import json

from rdflib.term import URIRef

if 'expander_open' not in st.session_state:
    st.session_state.expander_open = False

if 'datos' not in st.session_state:
    st.session_state.datos = []

def limpiar_uri(valor):
    if isinstance(valor, URIRef):
        return valor.split("/")[-1].split("#")[-1]
    return str(valor)

# Cargar el KG (esto puede venir de archivo .ttl)
@st.cache_data
def cargar_kg(path):
    g = Graph()
    with open(path, "r", encoding="utf-8") as file:
      ttl_data=file.read()
    g.parse(data=ttl_data, format="turtle")  # O usar file_uploader
    return g

@st.cache_data
def cargar_topics(_g):
    query = """
    SELECT ?paper ?topic ?percentage
    WHERE {
        ?tb a <https://example.org/TopicBelonging> ;
            <https://example.org/has_paper> ?paper ;
            <https://example.org/has_topic> ?topic ;
            <https://example.org/has_percentage> ?percentage .
    }
    """
    results = _g.query(query)
    return {
        str(paper): {"topic": limpiar_uri(topic), "percentage": float(percentage)}
        for paper, topic, percentage in results
    }

@st.cache_data
def cargar_similitudes(path):
    with open(path, "r", encoding="utf-8") as f:
        similitudes = json.load(f)
    return pd.DataFrame(similitudes)

kg_path = "outputs/knowledge_graph.ttl"

g = cargar_kg(kg_path)
topic_query = cargar_topics(g)

st.title("Buscador SPARQL sobre Knowledge Graph")

# Barra de búsqueda
col1, col2 = st.columns([4,1], vertical_alignment="bottom")
with col1:
  termino = st.text_input("Buscar por nombre, título u otro término:",placeholder="Michael, Short-term window, University ...")
with col2:
    filter_search = st.button("Buscar", use_container_width=True)


# Filtros en pestaña colapsable
with st.expander("Filtros", expanded=st.session_state.expander_open):
    filtro_categoria = st.selectbox(
        "Tipo de entidad",
        options=["Todas", "Persona", "Organización", "Paper"]
    )
    filtro_resultados = st.number_input("Número límite de resultados", min_value=1, value=20)
    filtro_topics = st.selectbox("Pertenece al tópico", options=["Todos", 0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    
    filtro_topic_threshold = st.slider("Umbral de pertenencia al tópico", 0.0, 1.0, 0.3, 0.05)

    consulta_usuario = st.text_area("Busqueda avanzada:", height=100)
    precise_search = st.button("Realizar búsqueda avanzada")
 

# Mapear filtro a clases del KG (ajústalo según tu ontología)
tipo_uri = {
    "Persona": "<https://example.org/Person>",
    "Organización": "<https://example.org/Organization>",
    "Paper": "<https://example.org/Paper>",
}

# Ejecutar consulta al pulsar Enter o botón
if filter_search:
    st.session_state.expander_open = False

    # Construcción dinámica de la consulta SPARQL
    filtro_tipo = ""
    if filtro_categoria != "Todas":
        filtro_tipo = f"?s a {tipo_uri[filtro_categoria]} ."
    elif filtro_categoria == "Paper" or filtro_categoria == "Todas":
      if filtro_topics != "Todos":
        filtro_tipo = f"""
          ?topic a <https://example.org/Topic> ;
                 <https://example.org/has_name_topic> "{filtro_topics}" .
    
          ?tb a <https://example.org/TopicBelonging> ;
               <https://example.org/has_topic> ?topic ;
               <https://example.org/has_paper> ?s ;
               <https://example.org/has_percentage> ?percentage .
    
          FILTER (?percentage >= {filtro_topic_threshold})
    
          ?s a <https://example.org/Paper> .
        """


    if termino.strip() == "":
      query = f"""
        SELECT DISTINCT ?s ?p ?o
        WHERE {{
            {filtro_tipo}
            ?s <https://example.org/has_title> ?o .
        }}
        ORDER BY ?s
        LIMIT {filtro_resultados}
        """

    else:
      query = f"""
        SELECT DISTINCT ?s ?p ?o
        WHERE {{
            {filtro_tipo}
            ?s ?p ?o .
            OPTIONAL {{ ?s a <https://example.org/Paper> . BIND(1 AS ?tipo) }}
            OPTIONAL {{ ?s a <https://example.org/Person> . BIND(2 AS ?tipo) }}
            OPTIONAL {{ ?s a <https://example.org/Organization> . BIND(3 AS ?tipo) }}
            FILTER(CONTAINS(LCASE(STR(?s)), LCASE("{termino}")) || CONTAINS(LCASE(STR(?p)), LCASE("{termino}")) || CONTAINS(LCASE(STR(?o)), LCASE("{termino}")))
        }}
        ORDER BY ?s ?tipo
        LIMIT {filtro_resultados}
        """
      
    resultados = g.query(query)

    # Formatear resultados
    st.session_state.datos = [{"Sujeto": limpiar_uri(r.s), "Propiedad": limpiar_uri(r.p) if limpiar_uri(r.p)!="None" else "has_title", "Nombre": limpiar_uri(r.o), "Topic": topic_query.get(str(r.s), "") if limpiar_uri(r.s).startswith("Paper_") else ""} for r in resultados]

if precise_search:
  st.session_state.expander_open = False
  try:
    resultados_avanzados = g.query(consulta_usuario)
    st.session_state.datos = [{"Sujeto": limpiar_uri(r.s), "Propiedad": limpiar_uri(r.p), "Nombre": limpiar_uri(r.o), "Topic": topic_query.get(str(r.s), "") if limpiar_uri(r.s).startswith("Paper_") else ""} for r in resultados_avanzados]
  except Exception as e:
    st.error(f"Error en la consulta SPARQL: {e}")

if st.session_state.datos:
  st.subheader("Resultados")
  df = pd.DataFrame(st.session_state.datos)
  st.dataframe(df, use_container_width=True)
  papers = df[df['Sujeto'].str.contains("Paper")]['Sujeto'].unique()
  if len(papers) > 0:
      selected_paper = st.selectbox("Selecciona un paper para buscar similares", papers)
      if st.button("Buscar papers similares"):
          paper_title_query = g.value(subject=URIRef(f"https://example.org/{selected_paper}"),
                                      predicate=URIRef("https://example.org/has_title"))
          
          if paper_title_query:
              query_similares = f"""
              PREFIX base: <https://example.org/>
      
              SELECT DISTINCT ?similar_title ?other_paper WHERE {{
                  ?paper a base:Paper ;
                         base:has_title "{paper_title_query}" ;
                         base:similar_to ?other_paper .
      
                  ?other_paper base:has_title ?similar_title .
              }}
              """
      
              resultados_similares = g.query(query_similares)
      
              datos_similares = []
              for r in resultados_similares:
                  paper_uri = str(r.other_paper)
                  paper_id = limpiar_uri(paper_uri)
                  topic_data = topic_query.get(paper_uri, {})
                  datos_similares.append({
                      "Paper similar": paper_id,
                      "Título": r.similar_title,
                      "Topic": topic_data.get("topic", "") if isinstance(topic_data, dict) else topic_data
                  })
      
              if datos_similares:
                  df_similares = pd.DataFrame(datos_similares)
                  st.write(f"Papers similares a **{selected_paper}**:")
                  st.dataframe(df_similares, use_container_width=True)
              else:
                  st.warning("No se encontraron papers similares.")
          else:
              st.warning("No se pudo recuperar el título del paper seleccionado.")
      
  else:
      st.info("No hay papers en los resultados para seleccionar.")


else:
  st.write("No se encontraron resultados")

