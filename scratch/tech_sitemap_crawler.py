import requests
import xml.etree.ElementTree as ET
import json
import os

class TechCourseCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # Bộ từ khóa lọc ngành Tech
        self.tech_keywords = [
            "frontend",
            "backend",
            "fullstack",
            "typescript",
            "javascript",
            "php",
            "python",
            "java",
            "c-plus-plus",
            "c-sharp",
            "go-lang",
            "rust",
            "swift",
            "kotlin",
            "artificial-intelligence",
            "machine-learning",
            "generative-ai",
            "llm",
            "nlp",
            "computer-vision",
            "deep-learning",
            "data-science",
            "data-engineering",
            "big-data",
            "vector-database",
            "cloud-computing",
            "aws",
            "azure",
            "google-cloud-platform",
            "devops",
            "docker",
            "kubernetes",
            "ci-cd",
            "terraform",
            "microservices",
            "cybersecurity",
            "react-js",
            "next-js",
            "vue-js",
            "angular",
            "node-js",
            "nest-js",
            "spring-boot",
            "django",
            "laravel",
            "fastapi",
            "flutter",
            "react-native",
            "postgresql",
            "mysql",
            "mongodb",
            "redis",
            "elasticsearch",
            "firebase",
            "git",
            "system-design",
            "software-architecture",
            "api-design",
            "agile",
            "scrum"
        ]

    def _fetch_xml(self, url):
        try:
            print(f"[*] Fetching: {url}")
            response = requests.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
            return ET.fromstring(response.content)
        except Exception as e:
            print(f"[!] Error fetching {url}: {e}")
            return None

    def crawl_coursera_tech(self, limit=50):
        """Crawl Coursera bằng cách lọc keywords từ sitemap courses"""
        sitemap_url = "https://www.coursera.org/sitemap~www~courses.xml"
        root = self._fetch_xml(sitemap_url)
        if root is None: return []

        tech_urls = []
        count = 0
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        for url_tag in root.findall('ns:url', ns):
            loc_tag = url_tag.find('ns:loc', ns)
            if loc_tag is not None:
                loc = loc_tag.text
                if any(kw in loc.lower() for kw in self.tech_keywords):
                    tech_urls.append({"source": "Coursera", "url": loc})
                    count += 1
                    if count >= limit: break
        
        return tech_urls

    def crawl_udemy_tech(self, limit=50):
        """Crawl Udemy bằng cách duyệt qua sitemap topics"""
        topic_sitemap = "https://www.udemy.com/sitemap/topic.xml"
        root = self._fetch_xml(topic_sitemap)
        if root is None: return []

        tech_urls = []
        count = 0
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        for url_tag in root.findall('ns:url', ns):
            loc_tag = url_tag.find('ns:loc', ns)
            if loc_tag is not None:
                loc = loc_tag.text
                if any(kw in loc.lower() for kw in self.tech_keywords):
                    tech_urls.append({"source": "Udemy", "url": loc})
                    count += 1
                    if count >= limit: break
        
        return tech_urls

if __name__ == "__main__":
    crawler = TechCourseCrawler()
    
    print("Starting crawl...")
    all_results = []
    
    # Lấy 50 URL mỗi bên để test
    all_results.extend(crawler.crawl_coursera_tech(limit=50))
    all_results.extend(crawler.crawl_udemy_tech(limit=50))
    
    output_file = "tech_urls.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)
    
    print(f"\n[+] Successfully saved {len(all_results)} URLs to {os.path.abspath(output_file)}")
