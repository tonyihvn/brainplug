"""URL reader utility."""
import requests
from bs4 import BeautifulSoup
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class URLReader:
    """Reads and extracts content from URLs."""
    
    def __init__(self, timeout=10):
        """Initialize URL reader."""
        self.timeout = timeout
    
    def read_url(self, url):
        """Read content from a URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Extract text from HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator='\n')
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Error reading URL: {str(e)}")
            raise
    
    def extract_links(self, url):
        """Extract all links from a URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                links.append({
                    'text': link.get_text(strip=True),
                    'href': link['href']
                })
            
            return links
        except Exception as e:
            logger.error(f"Error extracting links: {str(e)}")
            raise
