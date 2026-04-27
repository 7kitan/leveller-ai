from curl_cffi import requests

def test_udemy_html():
    url = "https://www.udemy.com/courses/search/?q=python"
    
    print("Testing Udemy Search Page (HTML) with curl_cffi...")
    try:
        response = requests.get(
            url, 
            impersonate="chrome120",
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Successfully fetched HTML!")
            print(f"Title snippet: {response.text.find('<title>')}")
            print(f"Page content length: {len(response.text)}")
        else:
            print(f"Failed. Status: {response.status_code}")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_udemy_html()
