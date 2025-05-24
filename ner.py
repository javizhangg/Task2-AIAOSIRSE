# -*- coding: utf-8 -*-
"""NER extractor (v 3.2 – *simple*)
───────────────────────────────────────────────────────────────────────────────
• Hugging Face (`dslim/bert‑base‑NER`) → candidatos ORG/MISC.
• Heurística muy ligera para *grant‑id*   → siempre **project**.
• Consulta compacta a Wikidata (API `wbsearchentities` + `P31`).
  - Si la etiqueta coincide exactamente, determina si es **organization**
    o **project** (listados QIDs mínimos).
  - Si no se puede clasificar ⇒ se descarta.
• Actualiza `outputs/papers_metadata_ner.json`.

Dependencias
~~~~~~~~~~~~
```bash
pip install transformers torch requests tqdm
```
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import List, Dict

import requests
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

###############################################################################
# 1 · MODELO HUGGING FACE                                                    #
###############################################################################
print("🔎  Cargando modelo Hugging Face …")
_tok  = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
_model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")
ner    = pipeline("ner", model=_model, tokenizer=_tok, aggregation_strategy="simple")

###############################################################################
# 2 · CONSTANTES / REGEX                                                     #
###############################################################################
ORG_QIDS  = {
    "Q43229",   # organisation
    "Q3918",    # university
    "Q783794",  # research institute
    "Q79913",   # company
    "Q31855",   # government agency
}
PROJECT_QIDS = {
    "Q23044590",  # research project
    "Q722377",    # framework programme
    "Q3402703",   # research programme
}
WIKIDATA_SEARCH = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"

GRANT_RE = re.compile(r"(?:grant|contract|award)[^A-Za-z0-9]{0,6}([A-Z0-9\-]{6,})", re.I)

###############################################################################
# 3 · UTILIDADES                                                             #
###############################################################################
_cache: dict[str,str] = {}

def clean(txt: str) -> str:
    txt = unicodedata.normalize("NFKC", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip(" ,;.:")

def classify_wikidata(label: str) -> str | None:
    """Devuelve 'org' / 'proj' / None si no se puede clasificar."""
    if label in _cache:
        return _cache[label]

    params = {
        "action": "wbsearchentities",
        "search": label,
        "language": "en",
        "format": "json",
        "type": "item",
        "limit": 5,
    }
    try:
        r = requests.get(WIKIDATA_SEARCH, params=params, timeout=6)
        r.raise_for_status()
        hits = r.json().get("search", [])
        hit = next((h for h in hits if h.get("label", "").casefold() == label.casefold()), None)
        if not hit:
            _cache[label] = None
            return None
        qid = hit["id"]
        ent = requests.get(WIKIDATA_ENTITY.format(qid), timeout=6).json()
        p31 = {
            c["mainsnak"]["datavalue"]["value"]["id"]
            for c in ent["entities"][qid].get("claims", {}).get("P31", [])
            if "datavalue" in c["mainsnak"]
        }
        if p31 & ORG_QIDS:
            _cache[label] = "org"
            return "org"
        if p31 & PROJECT_QIDS:
            _cache[label] = "proj"
            return "proj"
    except Exception:
        pass
    _cache[label] = None
    return None

###############################################################################
# 4 · EXTRACCIÓN                                                             #
###############################################################################

def extract_from_ack(text: str) -> Dict[str, List[str]]:
    orgs, projs = set(), set()

    # a) candidates via NER
    for ent in ner(text):
        if ent["entity_group"] not in {"ORG", "MISC"}:
            continue
        cand = clean(ent["word"])
        if len(cand) < 3:
            continue
        # check wikidata type
        typ = classify_wikidata(cand)
        if typ == "org":
            orgs.add(cand)
        elif typ == "proj":
            projs.add(cand)

    # b) grant‑like ids → projects
    for m in GRANT_RE.finditer(text):
        projs.add(m.group(1))

    return {
        "organizations": sorted(orgs),
        "projects": sorted(projs),
    }

###############################################################################
# 5 · I/O                                                                    #
###############################################################################
ROOT = Path(__file__).resolve().parent
IN_FILE  = ROOT / "outputs/papers_metadata.json"
OUT_FILE = ROOT / "outputs/papers_metadata_ner.json"

papers = json.loads(IN_FILE.read_text("utf-8"))
print(f"\n▶ Procesando {len(papers)} artículos …\n")
for p in tqdm(papers):
    ack = p.get("acknowledgements", "")
    res = extract_from_ack(ack)
    p.update(res)

OUT_FILE.parent.mkdir(exist_ok=True)
OUT_FILE.write_text(json.dumps(papers, indent=2, ensure_ascii=False), "utf-8")
print(f"\n✓ Resultado guardado en → {OUT_FILE.relative_to(ROOT)}\n")
