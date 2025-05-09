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
si quieres  probar se puede hacer con 
```bash 
python wikidata.py
```

https://drive.google.com/file/d/1heVXqSL_hGMyUH_ERv-NbrnHFA24A0xB/view?usp=sharing
enlace draw.io de los diagramas

te deborveria paper_metadata_wikidata.json
la ontology.ttl muesta el kg de los metadatos sin estender y el ontology_enhanced.ttl muestra el kg extendido con orgs y project faltaria lo de las personas


conda install pytorch torchvision torchaudio cpuonly -c pytorch
