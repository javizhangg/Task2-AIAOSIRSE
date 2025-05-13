import json
import os

from rapidfuzz import fuzz
import requests
import re

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

    def fetch(endpoint):
        try:
            url = f"{base_url}/{endpoint}"
            resp = requests.get(url, headers=HEADERS)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("affiliation-group", [])
        except Exception as e:
            print(f"Failed to fetch {endpoint} for {orcid_id}: {e}")
            return []

    def simplify(summary):
        org = summary.get("organization", {}) or {}
        disambiguated = org.get("disambiguated-organization") or {}
        start_date = summary.get("start-date") or {}
        end_date = summary.get("end-date") or {}

        return {
            "institution": (org.get("name") or "").strip(),
            "city": org.get("address", {}).get("city"),
            "country": org.get("address", {}).get("country"),
            "role": summary.get("role-title"),
            "start_year": start_date.get("year", {}).get("value"),
            "end_year": end_date.get("year", {}).get("value"),
            "identifier": disambiguated.get("disambiguated-organization-identifier")
        }


    def extract_summaries(raw_data, summary_key):
        results = []
        for group in raw_data:
            for s in group.get("summaries", []):
                summary = s.get(summary_key)
                if summary:
                    results.append(simplify(summary))
        return results

    # Fetch both education and employment summaries
    education_raw = fetch("educations")
    employment_raw = fetch("employments")

    education = extract_summaries(education_raw, "education-summary")
    employment = extract_summaries(employment_raw, "employment-summary")

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


def extract_keywords(title, min_length=5):
    """Extract key title words of sufficient length (ignores common stopwords)."""
    stopwords = {'the', 'with', 'from', 'using', 'based', 'in', 'on', 'by', 'and', 'for', 'into', 'into'}
    words = re.findall(r'\b\w+\b', title.lower())
    return [w for w in words if len(w) >= min_length and w not in stopwords]

def work_matches_keywords(work_title, keywords, min_score=60):
    """Check if the title fuzzily matches enough of the keywords."""
    match_scores = [fuzz.partial_ratio(work_title.lower(), kw) for kw in keywords]
    return sum(score >= min_score for score in match_scores) >= max(1, len(keywords) // 2)

def get_orcid(author_given, author_family, paper_title, affiliation=None):
    print(f"Searching ORCID for: {author_given} {author_family}")

    # Build search query
    query_parts = [f"family-name:{author_family}", f"given-names:{author_given}"]
    query = "+AND+".join(query_parts)
    search_url = f"https://pub.orcid.org/v3.0/search?q={query}"
    
    response = requests.get(search_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Search failed: {response.status_code}")
        return None

    results = response.json().get("result", [])
    if not results:
        return None

    title_keywords = extract_keywords(paper_title)

    for item in results:
        orcid_id = item["orcid-identifier"]["path"]

        # Check affiliation match first
        if affiliation:
            aff_data = extract_affiliations(orcid_id)
            all_affiliations = [
                a["institution"] for a in aff_data.get("education", []) + aff_data.get("employment", [])
                if a.get("institution")
            ]
            if any(fuzz.partial_ratio(aff.lower(), affiliation.lower()) >= 60 for aff in all_affiliations):
                print(f"Matched via affiliation: {orcid_id}")
                return orcid_id

        # If no affiliation or no match, try work title keywords
        works_url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
        works_resp = requests.get(works_url, headers=HEADERS)
        if works_resp.status_code != 200:
            continue

        works = works_resp.json().get("group", [])
        for group in works:
            summary = group.get("work-summary", [])[0]
            work_title = summary.get("title", {}).get("title", {}).get("value", "")
            if work_title and work_matches_keywords(work_title, title_keywords):
                print(f"Matched via keywords: {orcid_id} | Work: {work_title}")
                return orcid_id

    return None



def split_name(full_name):
    parts = full_name.strip().split()
    if len(parts) < 2:
        return full_name, ""  # fallback
    given_name = parts[0]
    family_name = " ".join(parts[1:])
    return given_name, family_name

def enrich_author_info(full_name, paper_title, affiliation=None):
    given_name, family_name = split_name(full_name)
    orcid_id = get_orcid(given_name, family_name, paper_title, affiliation)

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

    for author_obj in paper.get("authors", []):
        author_name = author_obj.get("name")
        raw_affiliation = author_obj.get("affiliation", "")
        cleaned_affiliation = " ".join(raw_affiliation.split()) if raw_affiliation else None
        print(cleaned_affiliation)
        enriched_info = enrich_author_info(author_name, paper_title, cleaned_affiliation)
        enriched_data.append(enriched_info)

# Save to new JSON
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(enriched_data, f, indent=2, ensure_ascii=False)

print(f"Enriched author data saved to {OUTPUT_PATH}")
