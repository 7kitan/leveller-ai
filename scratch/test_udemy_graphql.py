from curl_cffi import requests
import json

def test_udemy_graphql():
    url = "https://www.udemy.com/api/2024-01/graphql/"
    
    # GraphQL Query captured from the site
    query = """
    query SrpMxCourseSearch($query: String, $page: Int, $pageSize: Int, $filters: CourseSearchFilterParams, $sortOrder: CourseSearchSortOrder, $context: CourseSearchContext) {
      search(query: $query, page: $page, pageSize: $pageSize, filters: $filters, sort: $sortOrder, context: $context) {
        courses {
          id
          title
          headline
          rating
          num_reviews
          price_text
          visible_instructors {
            display_name
          }
        }
      }
    }
    """
    
    variables = {
        "context": {"triggerType": "USER_QUERY"},
        "filters": {},
        "page": 0,
        "pageSize": 5,
        "query": "Python",
        "sortOrder": "RELEVANCE"
    }
    
    payload = {
        "operationName": "SrpMxCourseSearch",
        "query": query,
        "variables": variables
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://www.udemy.com",
        "Referer": "https://www.udemy.com/courses/search/?q=Python",
    }

    print("Sending GraphQL request to Udemy using curl_cffi...")
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            impersonate="chrome120"
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Successfully fetched GraphQL data!")
            courses = data.get("data", {}).get("search", {}).get("courses", [])
            for i, course in enumerate(courses, 1):
                print(f"{i}. {course['title']} - {course['price_text']}")
                print(f"   Instructors: {', '.join([ins['display_name'] for ins in course['visible_instructors']])}")
        else:
            print(f"Failed. Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_udemy_graphql()
