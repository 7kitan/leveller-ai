# 🚀 Hướng Dẫn Cài Đặt Dự Án Demo AI

Chào mừng bạn! Đây là hướng dẫn từng bước cực kỳ chi tiết để bạn có thể tự mình cài đặt và chạy hệ thống AI này, ngay cả khi bạn không phải là dân chuyên về công nghệ.

---

## 🛠 Bước 1: Chuẩn bị công cụ (Prerequisites)

Trước tiên, bạn cần tải và cài đặt 3 công cụ cơ bản sau đây (cứ nhấn Next cho đến khi hoàn thành):

1.  **Docker Desktop** (Công cụ để chạy hệ thống): [Tải tại đây](https://www.docker.com/products/docker-desktop/)
2.  **Python** (Cần để chạy các lệnh khởi tạo): [Tải tại đây](https://www.python.org/downloads/)
3.  **VS Code** (Phần mềm để sửa file cấu hình): [Tải tại đây](https://code.visualstudio.com/)

---

## 📁 Bước 2: Tải mã nguồn dự án

Bạn có thể tải dự án này về máy bằng 2 cách:
- **Cách 1**: Nếu biết dùng Git, hãy chạy lệnh `git clone <đường-dẫn-repo>`.
- **Cách 2**: Nhấn vào nút **Code** -> **Download ZIP** trên GitHub, sau đó giải nén ra một thư mục trên máy tính của bạn.

---

## 🔑 Bước 3: Thiết lập "Bộ não" AI (OpenAI API Key)

Đây là bước quan trọng nhất để hệ thống AI có thể hoạt động. Hãy làm theo chính xác các bước sau:

### 1. Lấy mã chìa khóa (API Key)
- Truy cập vào [OpenAI Dashboard](https://platform.openai.com/api-keys).
- Đăng nhập tài khoản OpenAI của bạn.
- Nhấn nút **+ Create new secret key**, đặt tên bất kỳ và **Copy (Sao chép)** cái mã hiện ra (nó thường bắt đầu bằng `sk-...`). **Lưu ý: Chỉ hiện 1 lần nên bạn hãy lưu lại.**

### 2. Tạo file cấu hình `.env`
- Mở thư mục dự án bạn vừa tải về.
- Tìm đến thư mục có tên là **`backend`**.
- Trong thư mục `backend`, bạn sẽ thấy một file tên là **`.env.example`**.
- Nhấn chuột phải vào file đó -> chọn **Rename (Đổi tên)** -> Xóa chữ `.example` đi để file có tên chính xác là **`.env`** (nhớ là có dấu chấm ở đầu).

### 3. Dán mã chìa khóa vào file
- Nhấn chuột phải vào file **`.env`** mới tạo -> chọn **Open with Code** (hoặc mở bằng Notepad).
- Tìm đến dòng số 26 có nội dung: `OPENAI_API_KEY=...`
- Xóa phần nội dung cũ sau dấu `=` và **Dán (Paste)** mã chìa khóa bạn vừa copy ở bước trên vào.
- **Lưu file lại** (nhấn `Ctrl + S`).

---

## 🏗 Bước 4: Khởi động hệ thống

1.  Mở phần mềm **Docker Desktop** đã cài ở Bước 1 lên và đợi nó khởi động xong.
2.  Mở thư mục dự án, nhấn chuột phải vào khoảng trống và chọn **Open in Terminal (hoặc Open PowerShell Here)**.
3.  Gõ lệnh sau và nhấn Enter:
    ```bash
    cd backend
    docker-compose up -d --build
    ```
4.  Đợi khoảng 3-5 phút để hệ thống tự động tải và cài đặt. Khi nào xong, bạn sẽ thấy các dòng chữ xanh báo "Started".

---

## 🧬 Bước 5: Nạp dữ liệu vào hệ thống (Seeding)

Bước này giúp ứng dụng có sẵn dữ liệu về công việc và khóa học để bạn thử nghiệm.

1.  Vẫn tại cửa sổ Terminal ở Bước 4, gõ lệnh sau để cài đặt các thư viện cần thiết:
    ```bash
    pip install -r requirements.txt
    ```
2.  Chạy lệnh nạp dữ liệu:
    ```bash
    python scripts/seed_data.py
    ```

---

## 👤 Bước 6: Tạo tài khoản Quản trị viên (Admin)

Để đăng nhập vào hệ thống, bạn cần tạo một tài khoản admin:

1.  Gõ lệnh sau vào Terminal:
    ```bash
    python scripts/create_admin.py --email admin@demo.ai --password Admin@123
    ```
    *(Bạn có thể thay đổi email và mật khẩu theo ý muốn)*

---

## 🎉 Hoàn tất!

Bây giờ bạn có thể mở trình duyệt web (Chrome, Edge...) và truy cập vào địa chỉ:
👉 [**http://localhost:3000**](http://localhost:3000)

Đăng nhập bằng tài khoản bạn vừa tạo ở Bước 6 để bắt đầu sử dụng!

---

## ❓ Xử lý lỗi thường gặp (Troubleshooting)

- **Lỗi "Docker not found"**: Hãy chắc chắn bạn đã mở phần mềm Docker Desktop lên.
- **Lỗi không chạy được lệnh python**: Khi cài đặt Python, hãy nhớ tích vào ô **"Add Python to PATH"**.
- **Lỗi AI không phản hồi**: Kiểm tra lại file `.env` xem mã OpenAI Key đã dán đúng chưa và tài khoản của bạn còn hạn mức sử dụng không.
