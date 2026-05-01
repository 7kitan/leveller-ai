import os
import requests
import json
import time
import subprocess

# Cấu hình
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/cv/upload"
LOGIN_URL = f"{BASE_URL}/auth/login"
SAMPLES_DIR = "./samples"
REPORT_FILE = "parsing_report.json"

# Thông tin đăng nhập mặc định
ADMIN_CREDENTIALS = {
    "email": "admin@lumix.ai",
    "password": "Admin@123"
}

def get_auth_token():
    """Đăng nhập để lấy Access Token"""
    print(f"Đang đăng nhập vào {LOGIN_URL}...")
    try:
        # Sử dụng json= và đổi username thành email
        response = requests.post(LOGIN_URL, json=ADMIN_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            print(" -> Đăng nhập thành công!")
            return token
        else:
            print(f" -> Đăng nhập thất bại: {response.text}")
            return None
    except Exception as e:
        print(f" -> Lỗi kết nối khi đăng nhập: {e}")
        return None

def test_batch_parsing():
    if not os.path.exists(SAMPLES_DIR):
        print(f"Lỗi: Thư mục {SAMPLES_DIR} không tồn tại. Hãy tạo và bỏ các file CV mẫu vào đó.")
        return

    # Bước 0: Dọn dẹp Database (Xóa CV cũ để tránh cache is_duplicate) và Restart Worker
    print("Đang dọn dẹp database và khởi động lại Worker để nạp code mới...")
    try:
        subprocess.run(
            ["docker", "exec", "advisor_db", "psql", "-U", "postgres", "-d", "career_advisor", "-c", "DELETE FROM user_cvs;"],
            check=True,
            capture_output=True
        )
        print(" -> Đã dọn dẹp database thành công!")
        
        # Tự động restart Celery Worker để nạp code Python mới
        print(" -> Đang khởi động lại advisor_worker_parsing (có thể mất vài giây)...")
        subprocess.run(
            ["docker", "restart", "advisor_worker_parsing"],
            check=True,
            capture_output=True
        )
        print(" -> Đã khởi động lại Worker thành công!")
    except Exception as e:
        print(f" -> Cảnh báo: Lỗi khi dọn dẹp/restart tự động ({e}).")

    # Bước 1: Lấy Token
    token = get_auth_token()
    if not token:
        print("Không thể tiếp tục test vì không có Token.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    results = []
    files = [f for f in os.listdir(SAMPLES_DIR) if f.endswith(('.pdf', '.jpg', '.png'))]
    
    print(f"Đang bắt đầu test bóc tách cho {len(files)} file...")

    for filename in files:
        file_path = os.path.join(SAMPLES_DIR, filename)
        print(f" -> Đang xử lý: {filename}")
        
        start_time = time.time()
        try:
            with open(file_path, 'rb') as f:
                # 1. Gửi file lên
                response = requests.post(API_URL, files={'file': f}, headers=headers)
            
            status = "FAILED"
            parsed_name = "N/A"
            skills_count = 0
            error_detail = ""

            if response.status_code == 200:
                data = response.json()
                cv_id = data.get("cv_id")
                print(f"    -> Upload thành công! ID: {cv_id}")
                
                # 2. Đợi kết quả bóc tách (Polling) - tối đa 60 giây
                print(f"    -> Đang đợi AI bóc tách {filename}...", end="", flush=True)
                for i in range(30):  # 30 lần * 2s = 60s
                    time.sleep(2)
                    print(".", end="", flush=True)
                    status_url = f"{BASE_URL}/cv/{cv_id}"
                    status_resp = requests.get(status_url, headers=headers)
                    
                    if status_resp.status_code == 200:
                        cv_data = status_resp.json()
                        if cv_data.get("status") in ["completed", "failed"]:
                            if cv_data.get("status") == "completed":
                                status = "SUCCESS"
                                parsed_name = cv_data.get("full_name") or "Unknown"
                                skills_count = len(cv_data.get("skills", []))
                                print(" [XONG]")
                            else:
                                status = "FAILED"
                                error_detail = cv_data.get("error_message", "AI parsing failed")
                                print(" [LỖI]")
                            
                            # Format data to match LLM prompt JSON schema exactly
                            skills_schema = []
                            for s in cv_data.get("skills", []):
                                skills_schema.append({
                                    "name": s.get("name"),
                                    "category": s.get("category", "Other"),
                                    "experience_years": float(s.get("experience_years", s.get("years_exp", 0.0)))
                                })
                                
                            schema_output = {
                                "status": "success" if cv_data.get("status") == "completed" else "fail",
                                "error_message": cv_data.get("error_message") or None,
                                "full_name": cv_data.get("full_name") or None,
                                "summary": cv_data.get("summary") or None,
                                "seniority": cv_data.get("seniority") or None,
                                "experience_years_total": float(cv_data.get("experience_years_total") or 0.0),
                                "skills": skills_schema,
                                "work_history": cv_data.get("work_history", []),
                                "education": cv_data.get("education", []),
                                "certifications": cv_data.get("certifications", []),
                                "ocr_confidence": float(cv_data.get("ocr_confidence", 1.0))
                            }
                            
                            # Lưu dữ liệu chi tiết vào file riêng
                            results_dir = "detailed_results"
                            if not os.path.exists(results_dir):
                                os.makedirs(results_dir)
                            
                            detail_file = os.path.join(results_dir, f"{filename.replace('.pdf', '')}_parsed.json")
                            with open(detail_file, "w", encoding="utf-8") as df:
                                json.dump(schema_output, df, indent=4, ensure_ascii=False)
                                
                            if status == "SUCCESS":
                                error_detail = f"Chi tiết lưu tại: {detail_file}"
                                
                            break
                    else:
                        status = "FAILED"
                        error_detail = f"Status check failed: {status_resp.status_code}"
                        print(" [LỖI KẾT NỐI]")
                        break
                else:
                    status = "TIMEOUT"
                    error_detail = "Parsing took quá lâu (>60s)"
                    print(" [HẾT GIỜ]")
            else:
                status = "FAILED"
                error_detail = f"Upload failed ({response.status_code}): {response.text}"
                print(f"    -> {error_detail}")

            duration = time.time() - start_time
            results.append({
                "filename": filename,
                "status": status,
                "duration": f"{duration:.2f}s",
                "parsed_name": parsed_name,
                "skills_count": skills_count,
                "detail_file": detail_file if status == "SUCCESS" else None,
                "error_detail": error_detail if status != "SUCCESS" else ""
            })
        except Exception as e:
            results.append({
                "filename": filename,
                "status": "ERROR",
                "error": str(e)
            })

    # Xuất báo cáo
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print("-" * 30)
    print(f"Xong! Báo cáo chi tiết đã được lưu tại: {REPORT_FILE}")

if __name__ == "__main__":
    test_batch_parsing()
