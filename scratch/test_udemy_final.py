from curl_cffi import requests
from bs4 import BeautifulSoup

def test_udemy_scraping_final():
    url = "https://www.udemy.com/courses/search/?q=python"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    print("Fetching Udemy HTML with curl_cffi and parsing with BeautifulSoup...")
    try:
        response = requests.get(
            url, 
            headers=headers,
            impersonate="chrome120",
            timeout=15
        )
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Udemy course titles are usually in <h3> tags or a specific class
            # Based on recent Udemy structure: .course-card--course-title--...
            # Or just search for h3 tags inside course cards
            
            courses = []
            # Udemy uses various classes, but h3 is very consistent for titles
            for h3 in soup.find_all('h3'):
                title = h3.get_text().strip()
                # Find the link (usually the parent or a child)
                link_tag = h3.find('a') or h3.find_parent('a')
                if link_tag and 'course' in link_tag.get('href', ''):
                    link = "https://www.udemy.com" + link_tag['href']
                    courses.append({"title": title, "link": link})
            
            if courses:
                print(f"Successfully extracted {len(courses)} courses!")
                for i, c in enumerate(courses[:10], 1):
                    print(f"{i}. {c['title']}")
            else:
                print("No courses found with current selectors. Printing HTML snippet...")
                print(response.text[:1000])
        else:
            print(f"Failed. Status: {response.status_code}")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_udemy_scraping_final()
