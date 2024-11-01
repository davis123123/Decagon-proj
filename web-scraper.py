import requests
from bs4 import BeautifulSoup
import json

class NotionHelpScraper:
    def __init__(self):
        self.base_url = "https://www.notion.so"
        self.help_center_url = f"{self.base_url}/help"
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def get_article_links(self):
        """Retrieve all help article links from the Notion help center homepage."""
        response = requests.get(self.help_center_url, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        article_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/help" in href and "academy" not in href:
                article_links.append(self.base_url + href)
        
        return list(set(article_links))

    def fetch_article_content(self, url):
        """Fetch the main content from an article page and return as structured data."""
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        content = []
        title = soup.find("h1").text if soup.find("h1") else "Untitled"
        
        for element in soup.find_all(["h1", "h2", "p", "ul", "ol", "table"]):
            if element.name in ["h1", "h2"]:
                content.append({"type": "header", "text": element.text.strip()})
            elif element.name == "p":
                content.append({"type": "paragraph", "text": element.text.strip()})
            elif element.name in ["ul", "ol"]:
                bullets = [li.text.strip() for li in element.find_all("li")]
                content.append({"type": "list", "items": bullets})
            elif element.name == "table":
                table_text = self.parse_table(element)
                content.append({"type": "table", "text": table_text})
            else:
                content.append({"type": "other", "text": f"Unsupported format found in article at {url}"})
        
        return {"title": title, "content": content, "url": url}

    def parse_table(self, table):
        """Extract and format a table's text content."""
        table_rows = []
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            row_text = " | ".join(cell.get_text(strip=True) for cell in cells)
            table_rows.append(row_text)
        return "\n".join(table_rows)

    def scrape_articles(self, max_size=50):
        """Scrape all articles and process content to save as chunks directly to a JSON file."""
        links = self.get_article_links()
        
        with open("notion_help_articles.json", "w", encoding="utf-8") as outfile:
            outfile.write("[")  # Start JSON array
            
            first_item = True
            fetched = 0
            for link in links:
                if fetched > max_size:
                    break
                article_data = self.fetch_article_content(link)
                chunks = self.chunk_content(article_data["content"])
                
                for chunk in chunks:
                    chunk_data = {
                        "title": article_data["title"],
                        "content": chunk,
                        "metadata": {"url": article_data["url"]}
                    }
                    
                    if not first_item:
                        outfile.write(",\n")
                    first_item = False
                    
                    # Dump JSON object with indentation and no additional formatting
                    json.dump(chunk_data, outfile, ensure_ascii=False, indent=2)

                print("Fetched article: ", link)
                fetched += 1
            outfile.write("]")  # End JSON array

    def chunk_content(self, content, max_length=750):
        """Split content into chunks, preserving headers, paragraphs, tables, and lists."""
        chunks = []
        current_chunk = ""
        
        for element in content:
            if element["type"] == "header":
                current_chunk += element["text"] + "\n\n"

            elif element["type"] == "paragraph":
                current_chunk += element["text"] + " "

            elif element["type"] == "list":
                list_text = "\n".join([f"• {item}" for item in element["items"]])
                current_chunk += list_text + "\n"

            elif element["type"] == "table":
                current_chunk += element["text"]

            elif element["type"] == "other":
                current_chunk += element["text"]

            if len(current_chunk) >= max_length:
                chunks.append(current_chunk.strip())
                current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

# Run the scraper and chunking process with streaming to file
scraper = NotionHelpScraper()
scraper.scrape_articles()
