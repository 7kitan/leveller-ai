# KỊCH BẢN PITCHING: LEVELLER.AI (CAREER INTELLIGENCE PLATFORM)

---

## 1. MỞ ĐẦU: SỨ MỆNH & NIỀM TIN
**** Xin chào Ban Giám Khảo. Chúng tôi là **Leveller.ai** — nền tảng upskilling thông minh.

**** **Niềm tin của chúng tôi:** Sự nghiệp không phải là hành trình mù mờ. Mỗi ứng viên xứng đáng biết chính xác mình cần học gì, thiếu gì, và bao lâu để sẵn sàng cho công việc mơ ước.

**** **Tên gọi Leveller.ai có hai ý nghĩa:**
* **** **Levelling Up**: Nâng cao kỹ năng và tiến bộ sự nghiệp.
* **** **Levelling the Playing Field**: Cung cấp hướng dẫn chất lượng cao cho **mọi người**, không phân biệt. Hiện nay, ứng viên phải tự mò mẫm — đọc JD thủ công, học tràn lan, không biết khóa học nào thực sự giúp họ. Leveller.ai loại bỏ sự bất bình đẳng thông tin bằng **dữ liệu thị trường thực tế**.

---

## 2. VẤN ĐỀ & "NỖI ĐAU" THỊ TRƯỜNG
**** *============= CHIẾU VIDEO INTRO (Cảnh ứng viên bối rối khi đọc JD với 20+ kỹ năng yêu cầu) ============*

**** Như mọi người đã thấy trong video, vấn đề lớn nhất hiện nay của nhóm nhân sự trẻ (Gen Z) hay những người đang có ý định chuyển ngành không phải là thiếu tài liệu học tập, mà là **thiếu một bản đồ phát triển rõ ràng**.

**** Thực tế, quy mô thị trường EdTech Việt Nam đã đạt mốc 1.1 tỷ USD vào năm 2025, và số lượng người Việt đăng ký các khoá học MOOC kĩ thuật (v.d AI, machine learning) đạt top 3 thế giới cho thấy nhu cầu học tập là cực lớn. Tuy nhiên:
* **** Khoảng 28% nhân sự IT hiện nay là những người "trái ngành" từ Marketing, Sales chuyển sang.
* **** Họ đang phải tự đọc JD thủ công và học một cách tràn lan, không có lộ trình liên kết.
* **** Họ bị "mất phương hướng" giữa hàng ngàn chứng chỉ mà không biết cái nào thực sự giúp họ lọt vào mắt xanh của nhà tuyển dụng.
* **** Thêm vào đó, các Job Descriptions quá tải keyword — một JD cho vị trí Junior Backend có thể liệt kê 25+ kỹ năng, nhưng thực tế công ty chỉ cần 5-6 kỹ năng core. Ứng viên không biết cái nào là bắt buộc, cái nào là "nice-to-have", dẫn đến **học lâu hơn cần thiết, mất 6-12 tháng để "chuẩn bị" thay vì 2-3 tháng**. Kết quả: cơ hội bị bỏ lỡ, động lực giảm, và tiềm năng không được khai thác.

---

## 3. GIẢI PHÁP & CÔNG NGHỆ
**** *============== DEMO: PHÂN TÍCH CV & JD (THAO TÁC TRÊN GIAO DIỆN) ==========================*

**** Chỉ với thao tác tải lên CV và vị trí công việc mong muốn, trong vòng vài phút, **Leveller.ai** sẽ chỉ ra chính xác những kỹ năng **high-impact** mà bạn cần để sẵn sàng đóng góp ngay, thay vì học tất cả 25+ keywords.

* **** **Multi-modal CV Parsing:** Hệ thống xử lý CV dưới mọi hình thức — PDF, ảnh chụp, hoặc bản quét — nhờ tích hợp **OCR Engine** và **LangGraph Orchestrator**. Mỗi CV được phân tích qua nhiều bước kiểm định để đảm bảo độ chính xác tối đa.

* **** **Auto Skill Level Inference:** Hệ thống tự động suy luận mức độ thành thạo (Beginner/Intermediate/Advanced/Expert) cho mỗi kỹ năng dựa trên mô tả công việc trước đó, thời gian làm việc, và bối cảnh kinh nghiệm. Ứng viên không cần tự đánh giá mình — AI làm điều đó một cách khách quan.

* **** **Vector Semantic Search (pgvector):** Thay vì so khớp từ khóa đơn thuần, chúng tôi chuyển đổi kỹ năng thành vector 1536 chiều và sử dụng **pgvector** trên PostgreSQL để tìm kiếm ngữ nghĩa. 
  - *Ví dụ:* Hệ thống cũ (ATS - exact keyword match): JD yêu cầu "React" → CV có "Vue.js" → Không match (false negative). 
  - *Leveller.ai:* Hiểu cả hai đều là "Frontend Frameworks" → Nhận ra ứng viên có core concept, chỉ cần 1-2 tuần để chuyển sang React. Tương tự, "Python" và "JavaScript" đều là "Programming Languages" — nếu bạn thành thạo một cái, học cái khác sẽ nhanh hơn.

* **** **Real-time Job Market Crawling:** Hệ thống liên tục cào dữ liệu từ **TopCV** và các nguồn job listings khác để đảm bảo Gap Analysis dựa trên nhu cầu thị trường thực tế, không phải lý thuyết. Mỗi gợi ý đều được xác thực bằng dữ liệu sống từ các công việc đang tuyển dụng.

* **** **Multi-Platform Course Recommendations:** Hệ thống gợi ý khóa học từ nhiều nền tảng — **Coursera**, **YouTube**, và các nguồn học tập khác — với truy cập trực tiếp từ platform. Ứng viên không chỉ nhận được danh sách khóa học mà còn có thể bắt đầu học ngay lập tức, tối ưu hóa thời gian và chi phí.

* **** **Match Score & Salary Impact Calculation:** Hệ thống tự động tính toán Match Score (mức độ phù hợp với công việc mục tiêu) và Salary Impact (mức tăng lương dự kiến) dựa trên dữ liệu thị trường thực tế, giúp ứng viên hiểu rõ giá trị của mỗi kỹ năng.

---

## 4. GIÁ TRỊ VÀ TÁC ĐỘNG CÔNG NGHỆ
**** *=============== XEM KẾT QUẢ PHÂN TÍCH (SKILL GAP MAP & RADAR CHART) ===============*

**** Leveller.ai không chỉ chỉ ra gap, mà còn **tối ưu hóa thời gian học tập** để ứng viên có thể **đóng góp ngay** và **mở khóa cơ hội**:

* **** **Prioritized Skill Roadmap:** Thay vì học 25 keywords, hệ thống chỉ ra 5-6 kỹ năng core cần học trước. Kết quả: **giảm 60-70% thời gian chuẩn bị**, từ 6-12 tháng xuống còn 2-3 tháng.

* **** **Skill Transferability & Strength Leverage:** Hệ thống nhận diện kỹ năng liên quan và chỉ ra những gì bạn đã có thể transfer. Ví dụ: biết Vue.js → React chỉ cần 1-2 tuần; biết Python → JavaScript nhanh hơn vì cùng core concepts. Thậm chí, biết Excel (data manipulation, formulas, logic) → SQL (database queries) — ứng viên từ Finance, Marketing đã có nền tảng tư duy, chỉ cần học syntax. Ứng viên thấy rằng họ không phải "bắt đầu từ đầu" và có thể tối ưu hóa lộ trình học tập.

* **** **Prioritized Learning Path:** Mỗi khóa học được gợi ý dựa trên mức độ ảnh hưởng đến vị trí mục tiêu — giúp ứng viên ưu tiên học những gì quan trọng nhất. Không phải tất cả kỹ năng đều bằng nhau.

---

## 5. TẦM NHÌN TƯƠNG LAI
**** Tầm nhìn của chúng tôi không dừng lại ở một công cụ phân tích CV. Chúng tôi đang xây dựng một **"Career Intelligence Ecosystem"** giúp **mở khóa tiềm năng** cho hàng triệu người.

**** Roadmap tiếp theo tập trung vào **tăng tốc độ đóng góp** và **mở rộng cơ hội**:
* **** **AI CV Suggester:** Không chỉ phân tích, mà còn tự động gợi ý cách hiệu chỉnh CV để tăng Match Score với công việc mục tiêu — giúp ứng viên "nổi bật" hơn khi apply.
* **** **Artifact Builder Guide:** Hướng dẫn ứng viên xây dựng portfolio, project, hoặc bằng chứng thực tế để showcase kỹ năng. Hệ thống gợi ý loại artifact nào phù hợp nhất với mỗi kỹ năng và vị trí mục tiêu — giúp ứng viên không chỉ "có kỹ năng" mà còn "chứng minh được".
* **** **Interview Preparation:** Dựa trên Gap Analysis, hệ thống sẽ gợi ý các câu hỏi phỏng vấn có khả năng cao và cách trả lời tối ưu — giảm lo lắng, tăng tỷ lệ thành công.
* **** **Real-time Opportunity Matching:** Ứng viên sẽ nhận được thông báo khi có công việc mới phù hợp với lộ trình của họ — không phải chờ đợi, mà chủ động bắt cơ hội.
* **** **Employer Integration:** Giúp nhà tuyển dụng hiểu rõ hơn về ứng viên — không chỉ CV, mà còn mức độ sẵn sàng thực tế và tiềm năng phát triển. Kết nối tốt hơn giữa người tìm việc và nhà tuyển dụng.
* **** **Semantic Skill Graph (Neo4j):** Xây dựng đồ thị kỹ năng ngữ nghĩa từ dữ liệu tập thể của hàng triệu ứng viên. Mỗi lần ai đó thành công với một lộ trình học tập, hệ thống học được mối quan hệ mới giữa các kỹ năng. Kết quả: **Càng nhiều người sử dụng, càng chính xác các gợi ý** — tạo ra một flywheel hiệu ứng mạng lực.

**** Leveller.ai sẽ trở thành **"Career Accelerator"** — một hệ sinh thái giúp mỗi cá nhân **tập trung vào những gì quan trọng, đóng góp nhanh hơn, và mở khóa cơ hội** dựa trên dữ liệu thực tế.

---

## 6. KẾT LUẬN
**** **Leveller.ai ra đời từ một niềm tin đơn giản:** Mỗi cá nhân nên được trao quyền và chủ động trong việc phát triển kỹ năng của mình — **với sự hỗ trợ tối đa, cho hàng triệu người, ở bất kỳ đâu**.

**** **Chúng tôi xây dựng ba effect:**

1. **Cultivate Accuracy in the Tech Job Market:** Thay vì JD quá tải 25+ keywords, chúng tôi giúp nhà tuyển dụng phân biệt rõ ràng: **core requirements** (kỹ năng bắt buộc trước khi tuyển) vs. **trainable on the job** (kỹ năng có thể học sau khi vào công ty). Ứng viên không lãng phí thời gian học những kỹ năng không cần thiết. Nhà tuyển dụng giảm rủi ro bằng cách yêu cầu **artifact showcase** — portfolio, project, hoặc bằng chứng thực tế, tạo ra incentive refine lại yêu cầu.

2. **Inspire Confidence on Both Sides:** Ứng viên biết chính xác mình sẵn sàng khi nào. Nhà tuyển dụng biết ứng viên có thể đóng góp ngay. Không còn sự bất bình đẳng thông tin — cả hai bên đều tự tin.

3. **Build a Skilled Tech Workforce:** Bằng cách tối ưu hóa thời gian học tập (từ 6-12 tháng xuống 2-3 tháng), chúng tôi giúp hàng triệu người nhanh chóng trở thành những kỹ sư, nhà phân tích, và chuyên gia công nghệ mà thị trường cần.

**** **Leveller.ai là cầu nối — kết nối ứng viên với cơ hội, nhà tuyển dụng với tài năng, và cả hai bên với dữ liệu thị trường thực tế. Chúng tôi là hệ thống hỗ trợ để mỗi cá nhân tự tin bước vào tương lai.**

---

### 🚩 DEMO CHECKLIST (VERIFIED FEATURES):
1. **[1 phút]** Upload CV ảnh → Show OCR parsing + extracted skills.
2. **[1 phút]** Select job position (e.g., Junior Backend) → Show Skill Gap Map.
3. **[30 giây]** Highlight Match Score → "Bạn phù hợp 65% với vị trí này."
4. **[30 giây]** Show recommended courses from Coursera → "Dựa trên dữ liệu thị trường thực tế."
5. **[30 giây]** Show salary data from TopCV → "Mức lương trung bình cho vị trí này là..."
