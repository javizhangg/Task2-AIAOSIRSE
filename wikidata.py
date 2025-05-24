#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enrich_wikidata_v1.1.py
• Lee  outputs/papers_metadata_ner.json
• Añade enriched_organizations  / enriched_projects
  con TODOS los campos del modelo (null si no hay dato)
• Guarda outputs/papers_metadata_wikidata.json
"""

from __future__ import annotations
import json, requests, time
from pathlib import Path
from typing import Dict, Any
from tqdm import tqdm

# -------------------------------------------------------------------------
ROOT      = Path(__file__).resolve().parent
IN_FILE   = ROOT / "outputs/papers_metadata_ner.json"
OUT_FILE  = ROOT / "outputs/papers_metadata_wikidata.json"

SEARCH    = "https://www.wikidata.org/w/api.php"
ENTITY    = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
HEADERS   = {"User-Agent": "KG-Enricher/1.1 (contact@example.com)"}

ORG_QIDS  = {"Q43229","Q3918","Q783794","Q79913","Q31855"}
PROJ_QIDS = {"Q23044590","Q3402703","Q722377"}

# -------------------------------------------------------------------------
_cache_search: dict[str,str|None] = {}
_cache_entity: dict[str,dict]|None = {}

def search_exact(label:str)->str|None:
    if label in _cache_search:            # caché
        return _cache_search[label]
    params={"action":"wbsearchentities","search":label,"language":"en",
            "type":"item","format":"json","limit":5}
    try:
        hits=[h for h in requests.get(SEARCH,params=params,headers=HEADERS,
                                       timeout=8).json().get("search",[])
              if h["label"].casefold()==label.casefold()]
        qid = hits[0]["id"] if len(hits)==1 else None
    except Exception: qid=None
    _cache_search[label]=qid
    return qid

def fetch_entity(qid:str)->dict|None:
    if qid in _cache_entity:              # caché
        return _cache_entity[qid]
    try:
        data=requests.get(ENTITY.format(qid),headers=HEADERS,timeout=8).json()
        _cache_entity[qid]=data["entities"][qid]
    except Exception: _cache_entity[qid]=None
    return _cache_entity[qid]

def first(claims,pid):                    # helper
    v=claims.get(pid)
    if not v: return None
    sn=v[0]["mainsnak"]
    dt=sn["datatype"]
    if dt in {"string","url","external-id"}:
        return sn.get("datavalue",{}).get("value")
    if dt=="wikibase-item":
        return sn["datavalue"]["value"]["id"]
    if dt=="time":
        return sn["datavalue"]["value"]["time"]
    return None

# ----------   plantillas vacías  -----------------------------------------
ORG_TEMPLATE = {
    "has_name_organization": None,
    "has_wikidata_uri": None,
    "has_wikidata_label": None,
    "has_located_country": None,
    "has_website": None,
    "has_start_date": None,
    "has_end_date": None,
    "has_funder": None,
    "has_founder": None,
}
PROJ_TEMPLATE = {
    "has_id_project": None,
    "has_wikidata_uri": None,
    "has_wikidata_label": None,
    "has_located_country": None,
    "has_website": None,
    "has_start_date": None,
    "has_end_date": None,
    "has_funder": None,
}

def enrich(name:str,kind:str)->Dict[str,Any]:
    """kind=='org'|'proj'  → devuelve dict completo (nulls si vacío)"""
    base=ORG_TEMPLATE.copy() if kind=="org" else PROJ_TEMPLATE.copy()
    key  ="has_name_organization" if kind=="org" else "has_id_project"
    base[key]=name                         # siempre guardamos el nombre

    qid = search_exact(name)
    if not qid:                            # sin coincidencia → todos null
        return base

    ent = fetch_entity(qid)
    if not ent:                            # error al descargar
        return base

    # verificar instancia
    types={c["mainsnak"]["datavalue"]["value"]["id"]
           for c in ent.get("claims",{}).get("P31",[])
           if "datavalue" in c["mainsnak"]}
    if (kind=="org" and not (types & ORG_QIDS)) or \
       (kind=="proj" and not (types & PROJ_QIDS)):
        return base

    claims = ent["claims"]
    base.update({
        "has_wikidata_uri"  : f"https://www.wikidata.org/entity/{qid}",
        "has_wikidata_label": ent.get("labels",{}).get("en",{}).get("value"),
        "has_located_country": first(claims,"P17"),
        "has_website"       : first(claims,"P856"),
        "has_start_date"    : first(claims,"P580") or first(claims,"P571"),
        "has_end_date"      : first(claims,"P582"),
        "has_funder"        : first(claims,"P859"),
    })
    if kind=="org":
        base["has_founder"]= first(claims,"P112")
    return base

# -------------------------------------------------------------------------
print("📑 Leyendo papers_metadata_ner.json …")
papers=json.loads(IN_FILE.read_text("utf-8"))

org_names={o for p in papers for o in p.get("organizations",[])}
proj_names={g for p in papers for g in p.get("projects",[])}

print(f"· Organizaciones únicas: {len(org_names)}")
print(f"· Proyectos únicos     : {len(proj_names)}\n")

enriched_orgs  ={n:enrich(n,"org")  for n in tqdm(org_names, desc="orgs     ")}
enriched_projs ={n:enrich(n,"proj") for n in tqdm(proj_names,desc="projects")}

for p in papers:
    p["enriched_organizations"]=[enriched_orgs[n]  for n in p.get("organizations",[])]
    p["enriched_projects"]     =[enriched_projs[n] for n in p.get("projects",[])]

OUT_FILE.parent.mkdir(exist_ok=True)
OUT_FILE.write_text(json.dumps(papers,indent=2,ensure_ascii=False),"utf-8")
print(f"\n✅  Guardado → {OUT_FILE.relative_to(ROOT)}")
