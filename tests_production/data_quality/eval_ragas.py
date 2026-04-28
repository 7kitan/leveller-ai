import os
from dotenv import load_dotenv
from ragas import evaluate, RunConfig
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from datasets import Dataset

load_dotenv()

# Giả lập dữ liệu thu thập được từ hệ thống sau khi chạy thực tế (5 cases)
test_data = {
    "question": [
        "Lộ trình để trở thành Senior Backend từ vị trí hiện tại là gì?",
        "Tại sao tôi phù hợp với công việc Python Developer tại TechCorp?",
        "Tôi là Frontend Developer, tôi cần học gì để làm được vị trí Fullstack tại VinGroup?",
        "Kinh nghiệm của tôi có đủ ứng tuyển vị trí AI Engineer không?",
        "Tại sao CV của tôi bị đánh giá là thiếu kỹ năng Cloud?"
    ],
    "answer": [
        "1. Mức độ tương thích: Medium. Bạn đáp ứng tốt về ngôn ngữ (Python, Django) nhưng thiếu kỹ năng hạ tầng.\n2. Lộ trình hành động: Cần học ngay Kubernetes và AWS Cloud để làm quen với môi trường cloud-native.\n3. Lời khuyên tối ưu CV: Nên liệt kê chi tiết các project đã triển khai bằng Docker để làm nổi bật nền tảng Containerization.",
        "1. Mức độ tương thích: High. Bạn hoàn toàn đáp ứng yêu cầu về Python và PostgreSQL.\n2. Lộ trình hành động: Không cần bổ sung kỹ năng cứng, có thể tập trung chuẩn bị cho bài test thuật toán.\n3. Lời khuyên tối ưu CV: Nên nêu bật các project Python có quy mô lớn hoặc xử lý dữ liệu phức tạp với PostgreSQL.",
        "1. Mức độ tương thích: Medium. Bạn đã có nền tảng tốt về React nhưng thiếu hoàn toàn mảng Server-side.\n2. Lộ trình hành động: Tập trung học Node.js (Express) và MongoDB để hoàn thiện kỹ năng Fullstack.\n3. Lời khuyên tối ưu CV: Hãy nhấn mạnh khả năng học hỏi nhanh và các project Frontend phức tạp bạn đã từng làm.",
        "1. Mức độ tương thích: Low. Bạn mạnh về phân tích dữ liệu nhưng thiếu kinh nghiệm triển khai AI thực tế.\n2. Lộ trình hành động: Cần học thêm Docker, FastAPI và quy trình MLOps để đưa model lên Production.\n3. Lời khuyên tối ưu CV: Nên thêm các chứng chỉ liên quan đến ML hoặc các project cá nhân có triển khai API.",
        "1. Mức độ tương thích: Low. CV hiện tại chỉ tập trung vào quản trị server vật lý/local.\n2. Lộ trình hành động: Đăng ký khóa học AWS Certified Cloud Practitioner hoặc Azure Fundamentals.\n3. Lời khuyên tối ưu CV: Cần thay thế các kỹ năng quản trị local bằng các từ khóa tương ứng trên Cloud như EC2, S3 hoặc VPC."
    ],
    "contexts": [
        ["Job yêu cầu: Python, Django, AWS, Kubernetes. Ứng viên có: Python, Django, Docker."],
        ["Job yêu cầu: 3 năm Python, PostgreSQL. Ứng viên có: 4 năm Python, PostgreSQL."],
        ["Vị trí Fullstack VinGroup yêu cầu: React, Node.js, MongoDB. Ứng viên hiện tại: React, CSS, HTML."],
        ["Job AI Engineer yêu cầu: PyTorch, MLOps, Docker. Ứng viên có: Python, SQL, Pandas, Scikit-learn."],
        ["Job yêu cầu: Experience with AWS/Azure/GCP. Ứng viên có: Local server management, Nginx, Linux."]
    ],
    "ground_truth": [
        "Mức độ tương thích: Medium. Bạn cần tập trung bổ sung Kubernetes và AWS Cloud để đạt mức Senior Backend như yêu cầu của Job.",
        "Mức độ tương thích: High. Bạn hoàn toàn đáp ứng đủ yêu cầu về ngôn ngữ (Python) và database (PostgreSQL) cho vị trí này.",
        "Mức độ tương thích: Medium. Bạn cần học thêm Node.js và MongoDB để hoàn thiện kỹ năng Fullstack theo yêu cầu của VinGroup.",
        "Mức độ tương thích: Low. Bạn chưa đủ điều kiện, cần bổ sung gấp kỹ năng MLOps và Docker để ứng tuyển AI Engineer.",
        "Mức độ tương thích: Low. Bạn bị đánh giá thấp do thiếu kinh nghiệm thực tế với các nền tảng Public Cloud (AWS/Azure/GCP)."
    ]
}

def run_ragas_evaluation():
    # 1. Chuyển đổi dữ liệu sang định dạng Dataset của HuggingFace
    dataset = Dataset.from_dict(test_data)
    
    # 2. Khởi tạo LLM và Embeddings (LangChain objects)
    # Ragas sẽ tự động wrap các object này nếu cần
    llm = ChatOpenAI(model="gpt-4o")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # 3. Chạy đánh giá
    print("Đang đánh giá chất lượng AI bằng RAGAS...")
    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision
        ],
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(max_workers=1)
    )
    
    # 4. Xuất kết quả
    print("\n--- KẾT QUẢ ĐÁNH GIÁ RAGAS ---")
    df = result.to_pandas()
    print(df)
    
    # Lưu báo cáo
    df.to_csv("ragas_report.csv", index=False)
    print("\nBáo cáo đã được lưu vào file ragas_report.csv")

if __name__ == "__main__":
    # Lưu ý: Thư viện Ragas yêu cầu cài đặt: pip install ragas
    if os.getenv("OPENAI_API_KEY"):
        run_ragas_evaluation()
    else:
        print("Vui lòng thiết lập OPENAI_API_KEY để chạy đánh giá RAGAS.")
