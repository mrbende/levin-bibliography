import sys, re
import pandas as pd
import requests
import PyPDF2
from tqdm import tqdm

class LevinBibtex:
    #################################################
    ### This class compiles the list of citations ###
    #################################################
    def __init__(self):
        self.base_dir = "/Users/reedbender/Repositories/indrasnet/resources/bibtex/"
        self.txt_file = f"{self.base_dir}Levin-endnote-BibTex.txt"
        self.pdf_file = f"{self.base_dir}Levin-references.pdf"
        self.pdf_write_dir = "/Volumes/Samsung_SSD/levin-references/"
        self.email = "reedbndr@gmail.com"
        self.testing = False
        self.chunk_size = 200
    
    def get_doi_from_title(self,
                           title):
        ### GIVEN A PAPER TITLE, FIND THE DOI
        base_url = "https://api.crossref.org/works"
        response = requests.get(base_url, params={'query.title': title, 'rows': 1})

        ### QUERRYING CROSSREF
        if response.status_code != 200:
            print(f"Error {response.status_code}: Unable to fetch data from Crossref.")
            return None

        data = response.json()
        items = data.get("message", {}).get("items", [])

        ### RETURN NULL
        if not items:
            print("No DOI was found in CrossRef.")
            return None

        ### RETURN THE DOI
        return items[0].get("DOI")
    
    def try_unpaywall_download(self,
                               doi,
                               title):                   
        ### CONSTRUCT URL
        api_url = f"https://api.unpaywall.org/v2/{doi}?email={self.email}"

        ### REQUEST SCIHUB API
        response = requests.get(doi)
        if response.status_code == 200:
            data = response.json()
            if data.get("is_oa"):
                pdf_url = data['best_oa_location']['url_for_pdf']
            else:
                return "NA"
        else:
            return "NA"
        if '[Error]' in openaccess_pdf_url:
            return "NA"

        ### DOWNLOAD THE PDF
        pdf_out_name = title.lower()
        pdf_out_name = pdf_out_name.replace(' ', '_')
        pdf_out_name = re.sub(r'[^a-z0-9_]', '', pdf_out_name)
        pdf_out_name += ".pdf"
        try:
            pdf_response = requests.get(download_url, stream=True)
            pdf_response.raise_for_status()
        except:
            return "NA"
        try:
            with open(f"{self.pdf_write_dir}{pdf_out_name}", "wb") as pdf_file:
                for chunk in pdf_response.iter_content(chunk_size=8192):
                    pdf_file.write(chunk)
        except:
            return "NA"

        if "[successful pdf download]" not in download_result:
            return "NA"
        
        return pdf_out_name, pdf_url

    def try_scihub_download(self,
                            doi,
                            title):
        ### CONSTRUCT URL
        api_url = f"http://sci-hub.se/{doi}"

        ### REQUEST SCIHUB API
        response = requests.get(download_url)
        if response.status_code == 200:
            pdf_content = response.content

            ### DOWNLOAD THE PDF
            pdf_out_name = title.lower()
            pdf_out_name = pdf_out_name.replace(' ', '_')
            pdf_out_name = re.sub(r'[^a-z0-9_]', '', pdf_out_name)
            pdf_out_name += ".pdf"
            with open(f"{self.pdf_write_dir}{pdf_out_name}", "wb") as pdf_file:
                pdf_file.write(pdf_content)
            
        ### HANDLE FAILURE
        else:
            print(f"Failed to download paper with DOI from Scihub: {doi}. Error code: {response.status_code}")
            pdf_out_name = "NA"
            
        return pdf_out_name, api_url
    
    #######################
    ### ENDNOTE LIBRARY ###
    #######################
    def extract_citations_from_txt(self):
        with open(self.txt_file, 'r') as file:
            content = file.read()

        ### SPLIT ARTICLES
        articles = re.split(r'@article\{', content)[1:]
        if self.testing:
            articles = articles[:100]
            
        ### REGEX FOR TITLE AND DOI
        title_pattern = r"title = \{(.+?)\},"
        doi_pattern = r"DOI = \{(.+?)\},"

        ### KEEP RAM SLIM BY PROCESSING IN CHUNKS
        total_articles = len(articles)
        for start in tqdm(range(0, total_articles, self.chunk_size)):
            end = min(start + self.chunk_size, total_articles)
            current_chunk = articles[start:end]
            titles = []
            dois = []

            for article in current_chunk:
                ### TITLE
                title_match = re.search(title_pattern, article)
                title = title_match.group(1).strip() if title_match else 'No Title'
                titles.append(title)

                # DOI
                doi_match = re.search(doi_pattern, article)
                doi = doi_match.group(1).strip() if doi_match else self.get_doi_from_title(title)
                doi = doi if doi else "NA"
                dois.append(doi)

            ### DATAFRAME OF CHUNK
            df_chunk = pd.DataFrame({'Title': titles, 'DOI': dois})

            ### TO CSV
            if start == 0:
                df_chunk.to_csv('levin-bibtex-sources.csv', index=False, mode='w', header=True)
            else:
                df_chunk.to_csv('levin-bibtex-sources.csv', index=False, mode='a', header=False)
                
        print("Processing complete.")
        
    ####################
    ### BIBLIOGRAPHY ###
    ####################
    def extract_citations_from_pdf(self):
        ### READ PDF
        with open(self.pdf_file, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text()

        ### REGEX TO ISOLATE CITATIONS
        pattern = r"([A-Za-z\s,\.-]+), \((\d{4})\), ([^,]+), [^,]+, [^:]+"
        citations = re.findall(pattern, text)
        if self.testing:
            citations = citations[:100]
        total_citations = len(citations)

        ### KEEP RAM SLIM BY PROCESSING IN CHUNKS
        for start in tqdm(range(0, total_citations, self.chunk_size)):
            end = min(start + self.chunk_size, total_citations)
            current_chunk = citations[start:end]
            titles = []
            dois = []

            for citation in current_chunk:
                authors, year, title = citation

                ### TITLE
                title = title.replace('\n', '').strip()
                titles.append(title)

                ### DOI
                try:
                    doi = self.get_doi_from_title(title)
                except:
                    doi = "NA"
                dois.append(doi)

            ### DATAFRAME OF CHUNK
            df_chunk = pd.DataFrame({'Title': titles, 'DOI': dois})

            ### TO CSV
            if start == 0:
                df_chunk.to_csv('levin-pdf-references.csv', index=False, mode='w', header=True)
            else:
                df_chunk.to_csv('levin-pdf-references.csv', index=False, mode='a', header=False)

        print("Processing complete.")
        
if __name__ == "__main__":   
    Levin = LevinBibtex()
    # txt_citations = Levin.extract_citations_from_txt()
    # pdf_citations = Levin.extract_citations_from_pdf()