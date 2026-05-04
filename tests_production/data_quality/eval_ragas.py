import os
import psycopg2
from dotenv import load_dotenv
from ragas import evaluate, RunConfig
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from datasets import Dataset

load_dotenv()

# Hàm trích xuất dữ liệu thực tế từ Database
def get_real_test_data():
    try:
        # Kết nối vào Database (thay đổi thông tin kết nối nếu cần)
        conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/team078")
        cursor = conn.cursor()

        # Lấy dữ liệu 5 file CV mới nhất đã parse xong
        cursor.execute("""
            SELECT raw_text, cv_parsed_json 
            FROM user_cvs 
            WHERE status = 'completed'
            ORDER BY created_at DESC LIMIT 5
        """)
        rows = cursor.fetchall()
        
        questions = []
        answers = []
        contexts = []
        ground_truths = []

        # Ground truths bạn cần tự điền thủ công dựa trên 5 CV thực tế
        human_answers = [
            "Mức độ tương thích CV 1...",
            "Mức độ tương thích CV 2...",
            "Mức độ tương thích CV 3...",
            "Mức độ tương thích CV 4...",
            "Mức độ tương thích CV 5..."
        ]

        for idx, row in enumerate(rows):
            raw_text, ai_json = row
            
            # Ráp data theo chuẩn RAGAS
            questions.append("Hãy trích xuất số năm kinh nghiệm, kỹ năng và tóm tắt CV này theo chuẩn JSON schema.")
            contexts.append([raw_text])  # List of strings
            answers.append(str(ai_json)) # Đưa JSON AI sinh ra thành string
            
            # Gán ground truth (lưu ý: số lượng human_answers phải khớp với số row trả về)
            gt = human_answers[idx] if idx < len(human_answers) else "Chưa có đáp án chuẩn"
            ground_truths.append(gt)

        return {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths
        }
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu từ DB: {e}")
        return None

# Lấy dữ liệu thực tế để test
test_data = get_real_test_data()

# Nếu không lấy được data, fallback về dữ liệu giả lập
if not test_data:
    test_data = {
        "question": ["Lộ trình để trở thành Senior Backend?"] * 5,
        "answer": ["Bạn cần học AWS."] * 5,
        "contexts": [["Job yêu cầu AWS."]] * 5,
        "ground_truth": ["Bạn cần học AWS."] * 5
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
