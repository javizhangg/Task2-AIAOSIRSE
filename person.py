import json
import os

from rapidfuzz import fuzz
import requests

def is_title_match(arxiv_title, orcid_title, threshold=70):
    """Return True if the titles are similar enough based on the threshold."""
    score = fuzz.token_set_ratio(arxiv_title.lower(), orcid_title.lower())
    return score >= threshold


def fetch_access_token(client_id, client_secret):
    resp = requests.post("https://orcid.org/oauth/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "/read-public"
    }, headers={"Accept": "application/json"})
    
    return resp.json().get("access_token")

CLIENT_ID = "APP-4SOBDMAL2P672JW5"
CLIENT_SECRET = "7b996b75-b456-4b1c-b4a9-54c53b142e12"
ACCESS_TOKEN = fetch_access_token(CLIENT_ID, CLIENT_SECRET)
HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

def extract_affiliations(orcid_id):
    base_url = f"https://pub.orcid.org/v3.0/{orcid_id}"
    
    def fetch(url):
        resp = requests.get(url, headers=HEADERS)
        return resp.json().get("employment-summary" if "employments" in url else "education-summary", [])
    
    def simplify(entry):
        org = entry.get("organization", {})
        return {
            "institution": org.get("name"),
            "city": org.get("address", {}).get("city"),
            "country": org.get("address", {}).get("country"),
            "role": entry.get("role-title"),
            "start_year": entry.get("start-date", {}).get("year", {}).get("value"),
            "end_year": entry.get("end-date", {}).get("year", {}).get("value"),
            "identifier": org.get("disambiguated-organization", {}).get("disambiguated-organization-identifier")
        }
    
    education = [simplify(e) for e in fetch(f"{base_url}/educations")]
    employment = [simplify(e) for e in fetch(f"{base_url}/employments")]

    return {"education": education, "employment": employment}


def extract_person_info(orcid_id):
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/person"
    resp = requests.get(url, headers=HEADERS).json()

    # External IDs
    ids = []
    for ext_id in resp.get("external-identifiers", {}).get("external-identifier", []):
        ids.append({
            "type": ext_id.get("external-id-type"),
            "value": ext_id.get("external-id-value"),
            "url": ext_id.get("external-id-url", {}).get("value")
        })

    # URLs
    urls = []
    for r_url in resp.get("researcher-urls", {}).get("researcher-url", []):
        urls.append({
            "label": r_url.get("url-name"),
            "url": r_url.get("url", {}).get("value")
        })

    # Other Names
    other_names = [n.get("content") for n in resp.get("other-names", {}).get("other-name", [])]

    return {
        "external_ids": ids,
        "researcher_urls": urls,
        "other_names": other_names
    }

def count_works(orcid_id):
    url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
    resp = requests.get(url, headers=HEADERS).json()
    return len(resp.get("group", []))


def get_orcid(author_given, author_family, paper_title):
    print(author_given, author_family, paper_title)
    search_url = f"https://pub.orcid.org/v3.0/search?q=family-name:{author_family}+AND+given-names:{author_given}"
    response = requests.get(search_url, headers=HEADERS).json()

    ids = []

    result = response.get("result", [])
    if result is None:
        return None
    for item in result:
        orcid_id = item["orcid-identifier"]["path"]
        works_url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
        works_resp = requests.get(works_url, headers=HEADERS).json()

        for group in works_resp.get("group", []):
            summary = group.get("work-summary", [])[0]
            title = summary.get("title", {}).get("title", {}).get("value", "")
            if is_title_match(paper_title, title):
                ids.append(orcid_id)
    
    if len(ids) == 0:
        return None
    else:
        return ids[0]

def enrich_author_info(full_name, paper_title):
    splitted_name = full_name.split()
    given_name = splitted_name[0]
    family_name = splitted_name[1]
    orcid_id = get_orcid(given_name, family_name, paper_title)

    education = []
    employment = []
    external_ids = []
    researcher_urls = []
    other_names = []
    work_count = None

    if orcid_id is not None:
        print('id found')
        education = extract_affiliations(orcid_id)['education']
        employment = extract_affiliations(orcid_id)['employment']
        external_ids = extract_person_info(orcid_id)['external_ids']
        researcher_urls = extract_person_info(orcid_id)['researcher_urls']
        other_names = extract_person_info(orcid_id)['other_names']
        work_count = count_works(orcid_id)

    return {
        "full_name": full_name,
        "family_name": family_name,
        "given_name": given_name,
        "orcid_id": orcid_id,
        "paper_cited": paper_title,
        "education": education,
        "employment": employment,
        "external_ids": external_ids,
        "researcher_urls": researcher_urls,
        "other_names": other_names,
        "work_count": work_count
    }

# Load the original JSON
INPUT_PATH = "outputs/papers_metadata.json"
OUTPUT_PATH = "outputs/enriched_authors.json"

with open(INPUT_PATH, "r", encoding="utf-8") as f:
    papers = json.load(f)

enriched_data = []

for paper in papers:
    paper_title = paper.get("title", "")
    enriched_authors = []

    for author_name in paper.get("authors", []):
        enriched_info = enrich_author_info(author_name, paper_title)
        enriched_authors.append(enriched_info)

    enriched_data.append({
        "paper_title": paper_title,
        "authors": enriched_authors
    })

# Save to new JSON
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(enriched_data, f, indent=2, ensure_ascii=False)

print(f"Enriched author data saved to {OUTPUT_PATH}")
