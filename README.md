#  Hướng Dẫn

## 1. Chuẩn bị công cụ (Prerequisites)

1.  **Docker Desktop** : [Tải tại đây](https://www.docker.com/products/docker-desktop/)
2.  **Python** : [Tải tại đây](https://www.python.org/downloads/)

## 2. Tải mã nguồn dự án

`git clone https://github.com/a20-ai-thuc-chien/A20-App-078.git`

## 3. Thiết lập API Key (OpenAI)

- Project hiện chỉ dùng OpenAI API (11/04/26)
- Tạo file `.env`:

```
OPENAI_API_KEY=sk-proj...
```

## 4. Setup Docker backend

1. Mở phần mềm **Docker Desktop** đã cài ở Bước 1 lên và đợi nó khởi động xong.
2. Mở thư mục dự án, nhấn chuột phải vào khoảng trống và chọn **Open in Terminal (hoặc Open PowerShell Here)**.
3. Gõ lệnh sau và nhấn Enter:
    ```bashP
    cd backend
    docker-compose up -d --build
    ```
4. Đợi khoảng 3-5 phút để hệ thống tự động tải và cài đặt. Khi nào xong, bạn sẽ thấy các dòng chữ xanh báo "Started".
5. Tiếp tục dùng terminal cho bước 5

## 5. Nạp dữ liệu vào hệ thống (Seeding)

Bước này giúp ứng dụng có sẵn dữ liệu về kỹ năng (Skills), công việc (Jobs) và các khóa học (Courses) để hệ thống có thể phân tích và gợi ý.

1.  Vẫn tại cửa sổ Terminal ở Bước 4, gõ lệnh sau để cài đặt các thư viện cần thiết:
    ```bash
    pip install -r requirements.txt
    ```
2.  Chạy lệnh nạp TOÀN BỘ dữ liệu (Kỹ năng, Công việc, 300+ Khóa học):
    ```bash
    python scripts/seed_all.py
    ```
    *Lưu ý: Quá trình này có thể mất vài phút vì hệ thống cần tạo Vector Embedding (tọa độ không gian) cho dữ liệu để phục vụ tìm kiếm thông minh.*

3. Nếu bạn muốn bỏ nạp 300 khóa học Coursera (để chạy nhanh hơn), dùng lệnh:
    ```bash
    python scripts/seed_all.py --skip-extended
    ```

## 6.Tạo tài khoản Admin

Để đăng nhập vào hệ thống, bạn cần tạo một tài khoản admin:

1.  Gõ lệnh sau vào Terminal:
    ```bash
    python scripts/create_admin.py --email admin@demo.ai --password Admin@123
    ```
    *(Bạn có thể thay đổi email và mật khẩu theo ý muốn)*

## Launch
Truy cập vào địa chỉ: [**http://localhost:3000**](http://localhost:3000).
Đăng nhập bằng tài khoản bạn vừa tạo ở Bước 6 để bắt đầu sử dụng.
