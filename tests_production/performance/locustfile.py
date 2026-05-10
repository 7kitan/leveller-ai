from locust import HttpUser, task, between, events
import os
import itertools

# Pool of test accounts - mỗi user ảo sẽ lấy 1 account riêng
TEST_ACCOUNTS = [
    {"email": f"testuser_{i}@leveller.ai", "password": "Password@123"}
    for i in range(1, 11)
]
_account_cycle = itertools.cycle(TEST_ACCOUNTS)

class LevellerUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        """Được chạy khi mỗi user ảo được khởi tạo - Thực hiện đăng nhập"""
        account = next(_account_cycle)
        response = self.client.post("/auth/login", json=account)
        if response.status_code == 200:
            self.token = response.json().get("access_token")
        else:
            print(f"FAILED TO LOGIN ({account['email']}): {response.status_code} - {response.text[:200]}")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(5)
    def view_cv_list(self):
        """Giả lập người dùng xem danh sách CV (Action phổ biến nhất)"""
        self.client.get("/cv/list", headers=self._headers())

    @task(1)
    def upload_cv_stress_test(self):
        """Giả lập người dùng upload CV - Đây là task nặng nhất cho hệ thống"""
        if not self.token:
            return

        # Sử dụng một file PDF nhỏ để test tải
        file_path = "tests_production/data_quality/samples/1. StandardCV.pdf"
        
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                self.client.post(
                    "/cv/upload",
                    headers=self._headers(),
                    files={"file": ("test.pdf", f, "application/pdf")}
                )
        else:
            # Fallback nếu không tìm thấy file
            self.client.get("/cv/list", headers=self._headers())

    @task(3)
    def check_jd_market(self):
        """Giả lập người dùng xem thị trường việc làm"""
        self.client.get("/jd/list?limit=10", headers=self._headers())
