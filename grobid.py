import os
import requests
import xml.etree.ElementTree as ET
import json

# GROBID Server URLs
GROBID_DOCKER_URL = "http://grobid:8070/api/isalive"
GROBID_LOCAL_URL = "http://localhost:8070/api/isalive"

def check_grobid_status(url):
    """Checks if the GROBID service is active."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pass
    return False

# Automatically select the GROBID URL
if check_grobid_status(GROBID_DOCKER_URL):
    GROBID_URL = "http://grobid:8070/api/processFulltextDocument"
    print(f"Using GROBID at {GROBID_URL}")
elif check_grobid_status(GROBID_LOCAL_URL):
    GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
    print(f"Using GROBID at {GROBID_URL}")
else:
    raise ConnectionError("No instance of GROBID (Docker or Local) is available!")

# Directories
PDF_DIR = "pdfs/"
OUTPUT_DIR = "outputs/"

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Function to process PDFs with GROBID
def process_pdf(pdf_path):
    with open(pdf_path, "rb") as pdf_file:
        files = {"input": pdf_file}
        response = requests.post(GROBID_URL, files=files, data={"teiCoordinates": "figure"})
    if response.status_code == 200:
        return response.text  # Returns TEI XML
    else:
        print(f"Error processing {pdf_path}: {response.status_code}")
        return None

def extract_info(tei_xml, filename):
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    root = ET.fromstring(tei_xml)

    # Title
    title_el = root.find(".//tei:titleStmt/tei:title", ns)
    title = title_el.text.strip() if title_el is not None else ""

    # Authors (only from header)
    authors = []
    tei_header = root.find("tei:teiHeader", ns)
    if tei_header is not None:
        for author in tei_header.findall(".//tei:author", ns):
            pers_name = author.find("tei:persName", ns)
            if pers_name is not None:
                forename = pers_name.find("tei:forename", ns)
                surname = pers_name.find("tei:surname", ns)
                name_parts = []
                if forename is not None:
                    name_parts.append(forename.text)
                if surname is not None:
                    name_parts.append(surname.text)
                if name_parts:
                    authors.append(" ".join(name_parts))
    # Abstract
    abstract_el = root.find(".//tei:abstract", ns)
    abstract = " ".join(abstract_el.itertext()).strip() if abstract_el is not None else ""

    # Date of publication
    date_el = root.find(".//tei:publicationStmt/tei:date", ns)
    date = date_el.text.strip() if date_el is not None else ""

    # Acknowledgement
    ack_text = ""
    for div in root.findall(".//tei:div", ns):
        head = div.find("tei:head", ns)
        if head is not None and "acknowledg" in head.text.lower():
            ack_text = " ".join(div.itertext()).strip()
            break

    # References
    references = []
    for bibl in root.findall(".//tei:listBibl/tei:biblStruct", ns):
        # Reference authors
        ref_authors = []
        for author in bibl.findall(".//tei:author", ns):
            pers_name = author.find("tei:persName", ns)
            if pers_name is not None:
                forename = pers_name.find("tei:forename", ns)
                surname = pers_name.find("tei:surname", ns)
                name_parts = []
                if forename is not None:
                    name_parts.append(forename.text)
                if surname is not None:
                    name_parts.append(surname.text)
                if name_parts:
                    ref_authors.append(" ".join(name_parts))

        # Reference title
        title_el = bibl.find(".//tei:title", ns)
        
        if title_el is not None and title_el.text is not None:
            ref_title = title_el.text.strip() 
        else:
            ref_title = ""

        # Reference DOI or other ID
        doi = None
        idno = bibl.find(".//tei:idno", ns)
        if idno is not None:
            doi = idno.text.strip()

        references.append({
            "authors": ref_authors,
            "title": ref_title,
            "identifier": doi
        })

    return {
        "filename": filename,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "publication_date": date,
        "acknowledgements": ack_text,
        "references": references
    }


# Process all PDFs
results = []
for pdf in os.listdir(PDF_DIR):
    if pdf.endswith(".pdf"):
        pdf_path = os.path.join(PDF_DIR, pdf)
        print(f"Processing {pdf_path}...")
        tei_xml = process_pdf(pdf_path)
        if tei_xml:
            info = extract_info(tei_xml, pdf)
            results.append(info)


# Save as JSON
with open(os.path.join(OUTPUT_DIR, "papers_metadata.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
