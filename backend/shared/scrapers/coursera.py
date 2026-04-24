import requests
from bs4 import BeautifulSoup
import json
import re
import sys
import io
import logging

logger = logging.getLogger("crawler_worker")

# Cấu hình encoding để hiển thị tiếng Việt trên terminal Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def scrape_coursera_course(url):
    # Normalize URL: Remove language suffixes like -zhcn, -es, etc.
    # Coursera localized URLs usually end with -[language_code]
    url = re.sub(r'-[a-z]{4}$', '', url.split('?')[0])
    
    logger.info(f"🕸️ [SCRAPER] Bắt đầu trích xuất dữ liệu: {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        # Force UTF-8 encoding
        response.encoding = 'utf-8'
    except Exception as e:
        return {"error": f"Lỗi truy cập: {str(e)}"}

    soup = BeautifulSoup(response.text, 'html.parser')
    html_content = response.text

    # 0. Khởi tạo các trường dữ liệu
    course_info = {"name": None, "provider": None, "subject": "", "description": ""}
    level = None
    duration_raw = None
    duration_hours = None
    languages = []
    skills = []
    tools = []
    modules = []
    
    # 1. Trích xuất metadata từ JSON-LD
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    
    bc_names = []
    modules_from_json = []
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            blocks = data.get('@graph', [data])
            for block in blocks:
                # 1.1 Course main info
                if block.get('@type') == 'Course':
                    course_info['name'] = block.get('name')
                    course_info['provider'] = block.get('provider', {}).get('name')
                    course_info['description'] = block.get('description')
                    
                    edu_level = block.get('educationalLevel')
                    if edu_level:
                        if isinstance(edu_level, list):
                            level = ", ".join([str(l) for l in edu_level])
                        else:
                            level = str(edu_level)
                    
                    # 1.1.2 Languages
                    langs = block.get('availableLanguage')
                    if langs:
                        if isinstance(langs, list):
                            languages = [str(l) for l in langs]
                        else:
                            languages = [str(langs)]
                    
                    # 1.1.3 Duration (ISO 8601 từ CourseInstance)
                    has_instances = block.get('hasCourseInstance', [])
                    if has_instances and isinstance(has_instances, list):
                        workload = has_instances[0].get('courseWorkload')
                        if workload:
                            # Parse ISO 8601 duration đơn giản (e.g. PT24H20M -> 24.3)
                            h_match = re.search(r'(\d+)H', workload)
                            m_match = re.search(r'(\d+)M', workload)
                            hrs = int(h_match.group(1)) if h_match else 0
                            mins = int(m_match.group(1)) if m_match else 0
                            duration_hours = hrs + (mins / 60.0)

                    # 1.1.4 Syllabus (Modules)
                    syllabus = block.get('syllabusSections', [])
                    for s in syllabus:
                        s_name = s.get('name')
                        if s_name: modules_from_json.append(s_name.strip())



                # 1.2 Breadcrumbs (Subject)
                if block.get('@type') == 'BreadcrumbList':
                    items = block.get('itemListElement', [])
                    for item in items:
                        name = item.get('item', {}).get('name') or item.get('name')
                        if name and name not in ["Browse", "Coursera"]:
                            bc_names.append(name)
                
                # 1.3 Syllabus (Nằm lẻ - rare but possible)
                if block.get('@type') == 'Syllabus':
                    m_name = block.get('name')
                    if m_name:
                        modules_from_json.append(m_name.strip())
        except: continue
    course_info['subject'] = " > ".join(bc_names)



    # 2. Tìm TRUE COURSE ID (Mã 22 ký tự)
    true_course_id = None
    id_match = re.search(r'courseTypeMetadata\.v1["\']?\\?:\s*\\?\{?["\']([a-zA-Z0-9_-]{22})["\']', html_content)
    if not id_match:
        id_match = re.search(r'courseId["\']?\s*[:=]\s*["\']([a-zA-Z0-9_-]{22})["\']', html_content)
    if id_match:
        true_course_id = id_match.group(1)

    # 3. Kỹ năng & Công cụ (Skills & Tools)
    skills = []
    tools = []
    
    # Tìm kiếm các thẻ kỹ năng
    skill_tags = soup.find_all('span', {'data-testid': re.compile(r'^skill-tag-')})
    if skill_tags:
        skills = [s.get_text().strip() for s in skill_tags]
    
    # Tìm kiếm các thẻ công cụ (Tools you'll learn)
    tool_tags = soup.find_all('span', {'data-testid': re.compile(r'^tool-tag-')})
    if tool_tags:
        tools = [t.get_text().strip() for t in tool_tags]

    # 4. Thời gian (Duration) & 5. Trình độ (Level)
    # Nếu level đã lấy từ JSON-LD thì dùng luôn, nếu không thì quét regex
    
    # Quét toàn văn bản để tìm các mẫu đặc trưng
    duration_match = re.search(r'(\d+|Approx\.\s\d+)\s(hours|weeks|months)', html_content, re.I)
    if duration_match: duration_raw = duration_match.group(0)
    
    if not level:
        level_match = re.search(r'(Beginner|Intermediate|Mixed|Advanced)\sLevel', html_content, re.I)
        if level_match: level = level_match.group(0)

    # 6. Modules
    # Ưu tiên lấy từ JSON-LD Syllabus nếu có
    if modules_from_json:
        modules = modules_from_json
    
    if not modules:
        # Trích xuất bằng cách quét thô syllabusSections - Đây là cách cuối cùng
        blacklist = ["instructor", "offered by", "certificate", "enroll", "faq", "review", "testimonial", "recommendation", "learn more"]
        
        # Tìm kiếm mảng syllabusSections bằng Regex nới lỏng
        # Chúng ta tìm chuỗi "syllabusSections" và lấy toàn bộ nội dung mảng sau đó
        syllabus_patterns = [
            r'\"syllabusSections\"\:\[(.+?)\]',
            r'syllabusSections\\?\":\\?\[(.+?)\\?\]'
        ]
        
        for pattern in syllabus_patterns:
            match = re.search(pattern, html_content)
            if match:
                blob = match.group(1)
                # Tìm tất cả các giá trị của trường "name" trong blob này
                # Cần giải quyết cả trường hợp có dấu backslash (nếu nằm trong script string)
                names = re.findall(r'\"name\"\:\"([^\"]+)\"', blob)
                for n in names:
                    try:
                        # Giải mã Unicode (ví dụ: \u0020)
                        decoded = n.encode().decode('unicode-escape')
                        if decoded and not any(b in decoded.lower() for b in blacklist):
                            # Làm sạch tên module
                            clean = re.split(r'[•\u2022|â€¢]', decoded)[0].strip()
                            if len(clean) > 3:
                                modules.append(clean)
                    except: pass
            if modules: break


    # Loại bỏ trùng lặp và giữ nguyên thứ tự
    modules = list(dict.fromkeys(modules))

    # 7. Kết quả đầu ra (Outcomes)

    outcomes = []
    outcomes_section = soup.find('div', {'data-testid': 'outcomes-section'}) or soup.find('div', {'id': 'outcomes'})
    if outcomes_section:
        outcomes = [li.get_text().strip() for li in outcomes_section.find_all('li')]

    # 8. Description
    description = course_info['description']
    if not description:
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc: description = meta_desc.get('content')

    return {
        "source_platform": "coursera",
        "source_id": url.split('/')[-1].split('?')[0].split('#')[0],
        "external_uuid": true_course_id,
        "name": course_info['name'] or (soup.title.string.split('|')[0].strip() if soup.title else "Unknown"),
        "provider": course_info['provider'],
        "subject": course_info['subject'],
        "level": level,
        "languages": languages,
        "duration_raw": duration_raw,
        "duration_hours": duration_hours,
        "skills": sorted(list(set(skills))),
        "tools": sorted(list(set(tools))),
        "outcomes": outcomes,
        "modules": modules,
        "description": description,
        "url": url
    }
