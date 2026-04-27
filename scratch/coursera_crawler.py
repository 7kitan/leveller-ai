import requests
import xml.etree.ElementTree as ET
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class CourseraCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # Tech keywords để lọc
        self.tech_keywords = [
            "frontend", "backend", "fullstack",
            "typescript", "javascript", "php", "python", "java",
            "c-plus-plus", "c-sharp", "go-lang", "rust", "swift", "kotlin",
            "artificial-intelligence", "machine-learning", "generative-ai",
            "llm", "nlp", "computer-vision", "deep-learning",
            "data-science", "data-engineering", "big-data",
            "cloud-computing", "aws", "azure", "google-cloud-platform",
            "devops", "docker", "kubernetes", "ci-cd", "terraform",
            "microservices", "cybersecurity",
            "react-js", "next-js", "vue-js", "angular",
            "node-js", "nest-js", "spring-boot", "django", "laravel", "fastapi",
            "flutter", "react-native",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "firebase",
            "git", "system-design", "software-architecture", "api-design",
            "agile", "scrum"
        ]

    def crawl_coursera(self, limit=None):
        """Crawl Coursera courses từ sitemap"""
        sitemap_url = "https://www.coursera.org/sitemap~www~courses.xml"
        
        try:
            print(f"[*] Đang crawl: {sitemap_url}")
            response = requests.get(sitemap_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except Exception as e:
            print(f"[!] Lỗi khi crawl: {e}")
            return []

        tech_urls = []
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        for url_tag in root.findall('ns:url', ns):
            loc_tag = url_tag.find('ns:loc', ns)
            if loc_tag is not None:
                url = loc_tag.text
                # Kiểm tra có chứa tech keyword không
                if any(kw in url.lower() for kw in self.tech_keywords):
                    tech_urls.append(url)
                    if limit and len(tech_urls) >= limit:
                        break
        
        return tech_urls

    def save_to_txt(self, urls, filename="coursera_tech_urls.txt"):
        """Lưu URLs vào file txt, mỗi dòng 1 URL"""
        with open(filename, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(url + '\n')
        print(f"[+] Đã lưu {len(urls)} URLs vào {filename}")

if __name__ == "__main__":
    crawler = CourseraCrawler()
    
    print("Bắt đầu crawl Coursera...")
    # Không giới hạn số lượng (limit=None) để lấy tất cả
    urls = crawler.crawl_coursera(limit=None)
    
    if urls:
        crawler.save_to_txt(urls)
        print(f"\n✓ Hoàn thành! Tổng cộng: {len(urls)} khóa học tech")
    else:
        print("\n✗ Không tìm thấy URL nào")
