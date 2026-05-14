"use client";

import React from "react";
import Link from "next/link";
import {
  Target,
  Cpu,
  GraduationCap,
  ChevronRight,
  Upload,
  Sparkles,
  TrendingUp,
  ArrowRight,
  Star,
  Mail
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useLanguage } from "@/context/LanguageContext";
import LandingNavbar from "@/components/landing/LandingNavbar";

import styles from "./landing.module.css";

/* ========================================
 * MAIN PAGE COMPONENT
 * ======================================== */

export default function LandingPage() {
  const { language } = useLanguage();

  // Translation object
  const t = {
    vi: {
       hero: {
         title: "Hệ thống cũ nói 'bạn không phù hợp.'<br />Chúng tôi nói 'bạn sắp đến rồi.'",
        description: "Tải CV lên, chọn vị trí mong muốn — nhận lộ trình học tập và match score trong vài phút.",
        getStarted: "Bắt đầu ngay",
        learnMore: "Tìm hiểu thêm"
      },
      problem: {
        heading: "Vấn đề & Nỗi Đau Thị Trường",
        title: "Thiếu một bản đồ phát triển rõ ràng",
        description: "Nhu cầu học tập công nghệ ở Việt Nam là cực lớn — thị trường EdTech đã đạt 1.1 tỷ USD vào 2025, và số lượng người Việt đăng ký các khóa học MOOC kỹ thuật đạt top 3 thế giới. Tuy nhiên, vấn đề lớn nhất không phải thiếu tài liệu học tập, mà là thiếu một lộ trình phát triển rõ ràng.",
        pain1: "28% nhân sự IT là những người 'trái ngành' từ Marketing, Sales chuyển sang — phải tự đọc JD thủ công, học tràn lan, không có lộ trình liên kết",
        pain2: "Mô tả công việc quá tải từ khóa — một JD Junior Backend liệt kê 25+ kỹ năng, nhưng công ty chỉ cần 5-6 cốt lõi. Ứng viên không biết cái nào bắt buộc vs 'nice-to-have'",
        pain3: "Kết quả: học lâu hơn cần thiết (6-12 tháng thay vì 2-3), cơ hội bị bỏ lỡ, động lực giảm, tiềm năng không được khai thác",
        employerHeading: "Góc Nhìn Nhà Tuyển Dụng",
        employerTitle: "ATS đang loại bỏ ứng viên tiềm năng",
        employerDesc: "ATS (Applicant Tracking System) là phần mềm mà hầu hết nhà tuyển dụng dùng để lọc hồ sơ. Nó hoạt động bằng cách so khớp chính xác từ khóa — và nó đang loại bỏ những ứng viên tốt nhất của bạn.",
        employerPain1: "JD liệt kê 25+ keywords → lọc chính xác → 80% ứng viên khả thi không bao giờ đến tay người phỏng vấn",
        employerPain2: "Yêu cầu 'React' → CV có 'Vue.js' → bị từ chối. Sai lầm. Ứng viên đó chỉ cách sẵn sàng 2 tuần.",
        employerPain3: "Chi phí tuyển dụng cao, thời gian đào tạo kéo dài — vì không ai biết ứng viên thực sự cần gì."
      },
      solution: {
        heading: "Giải Pháp & Công Nghệ",
        featuresHeading: "Công Nghệ Của Chúng Tôi",
        title: "Phân Tích CV & JD Thông Minh",
        description: "Chỉ với thao tác tải lên CV và vị trí công việc mong muốn, trong vòng vài phút, Leveller.ai sẽ chỉ ra chính xác những kỹ năng high-impact mà bạn cần.",
        insightTitle: "Kỹ năng kết nối với nhau. ATS không thấy điều đó.",
        insightDesc: "ATS xem từng kỹ năng riêng lẻ. Chúng tôi hiểu mối liên kết giữa chúng — và giúp bạn tận dụng những gì đã biết.",
        compareHeading: "ATS vs Leveller",
        compareMatch: "So khớp",
        compareMatchDesc: "Keyword chính xác — 80% false negatives",
        compareMatchDesc2: "Ngữ nghĩa — tìm kỹ năng gần nhất",
        compareSkill: "Kỹ năng",
        compareSkillDesc: "Tự xưng, người quen endorse",
        compareSkillDesc2: "AI suy luận từ bối cảnh kinh nghiệm",
        compareFeedback: "Phản hồi",
        compareFeedbackDesc: "Im lặng hoặc từ chối tự động",
        compareFeedbackDesc2: "Match score + gap analysis trước khi ứng tuyển",
        feature1: "Multi-modal CV Parsing",
        feature1Desc: "Xử lý CV dưới mọi hình thức — PDF, ảnh chụp, hoặc bản quét — nhờ OCR Engine và LangGraph Orchestrator",
        feature2: "Auto Skill Level Inference",
        feature2Desc: "Tự động suy luận mức độ thành thạo dựa trên mô tả công việc, thời gian làm việc, và bối cảnh kinh nghiệm",
        feature3: "Semantic Skill Matching",
        feature3Desc: "Hiểu được ý nghĩa thực sự của từng kỹ năng — không chỉ so khớp từ khóa, mà tìm ra kỹ năng tương tự dựa trên ngữ cảnh và kinh nghiệm thực tế.",
        feature4: "Real-time Job Market Crawling",
        feature4Desc: "Liên tục cào dữ liệu từ TopCV và các nguồn job listings khác để đảm bảo Gap Analysis dựa trên nhu cầu thị trường thực tế",
        feature5: "Multi-Platform Course Recommendations",
        feature5Desc: "Gợi ý khóa học từ Coursera, YouTube và các nền tảng khác với truy cập trực tiếp để tối ưu hóa thời gian học tập",
        feature6: "Match Score & Salary Impact",
        feature6Desc: "Tự động tính toán Match Score và Salary Impact dựa trên dữ liệu thị trường thực tế để giúp ứng viên hiểu rõ giá trị của mỗi kỹ năng"
      },
      userSteps: {
        heading: "Quy Trình Sử Dụng",
        step1: "Tải CV lên",
        step1Desc: "Upload CV ảnh hoặc PDF → Hệ thống phân tích OCR + extracted skills",
        step2: "Chọn Vị Trí",
        step2Desc: "Select job position (e.g., Junior Backend) → Show Skill Gap Map",
        step3: "Nhận Kết Quả",
        step3Desc: "Xem Match Score, recommended courses, salary data từ TopCV"
      },
      impact: {
        heading: "Tác Động & Giá Trị",
        title: "Tối Ưu Hóa Thời Gian Học Tập",
        description: "Leveller.ai không chỉ chỉ ra gap, mà còn tối ưu hóa thời gian học tập để ứng viên có thể đóng góp ngay và mở khóa cơ hội.",
        metric1: "Prioritized Skill Roadmap",
        metric1Desc: "Thay vì học 25 keywords, hệ thống chỉ ra 5-6 kỹ năng core cần học trước. Kết quả: giảm 60-70% thời gian chuẩn bị, từ 6-12 tháng xuống còn 2-3 tháng",
        metric2: "Skill Transferability & Strength Leverage",
        metric2Desc: "Hệ thống nhận diện kỹ năng liên quan và chỉ ra những gì bạn đã có thể transfer. Vue.js → React (1-2 tuần), Excel → SQL (ứng viên từ Finance/Marketing đã có nền tảng tư duy)",
        metric3: "Prioritized Learning Path",
        metric3Desc: "Mỗi khóa học được gợi ý dựa trên mức độ ảnh hưởng đến vị trí mục tiêu. Ứng viên không phải 'bắt đầu từ đầu' và có thể tối ưu hóa lộ trình học tập",
        transferHeading: "Ba Lớp Chuyển Đổi Kỹ Năng",
        sameCategory: "Cùng danh mục",
        sameCategoryDesc: "Vue.js ↔ React, Java ↔ C#. Chỉ khác cú pháp.",
        adjacentDomain: "Liên quan",
        adjacentDomainDesc: "Excel → SQL. Bề mặt khác, cùng tư duy dữ liệu.",
        professionalLeverage: "Chuyển đổi chuyên môn",
        professionalLeverageDesc: "Sales → Tech. Kỹ năng giao tiếp chuyển đổi trực tiếp."
      },
      roadmap: {
        heading: "Lộ Trình Phát Triển",
        title: "Hệ Sinh Thái Nhà Tuyển Dụng - Ứng Viên",
        description: "Chúng tôi đang xây dựng một hệ sinh thái giúp mở khóa tiềm năng cho hàng triệu người.",
        feature1: "Tích Hợp Nhà Tuyển Dụng",
        feature1Desc: "JD thông minh + dữ liệu sẵn sàng thực tế của ứng viên — vượt xa ATS truyền thống. Nguồn doanh thu chính từ tuyển dụng.",
        feature2: "Kết Nối Cơ Hội Thời Gian Thực",
        feature2Desc: "Nhận thông báo khi có công việc mới phù hợp với lộ trình học tập — doanh thu affiliate theo mỗi placement.",
        feature3: "Gợi Ý CV Thông Minh",
        feature3Desc: "Tự động gợi ý cách hiệu chỉnh CV để tăng Match Score với công việc mục tiêu",
        feature4: "Chuẩn Bị Phỏng Vấn",
        feature4Desc: "Gợi ý các câu hỏi phỏng vấn có khả năng cao và cách trả lời tối ưu",
        feature5: "Hướng Dẫn Xây Dựng Portfolio",
        feature5Desc: "Hướng dẫn xây dựng portfolio, project, hoặc bằng chứng thực tế để showcase kỹ năng",
        feature6: "Đồ Thị Kỹ Năng Ngữ Nghĩa",
        feature6Desc: "Xây dựng đồ thị kỹ năng ngữ nghĩa từ dữ liệu tập thể — càng nhiều người sử dụng, càng chính xác các gợi ý"
      },
      targets: {
        heading: "Ba Hiệu Ứng",
        title: "Xây Dựng Tương Lai của Trí Tuệ Nghề Nghiệp",
        description: "Chúng tôi đang tạo ra ba hiệu ứng liên kết để biến đổi thị trường việc làm công nghệ.",
        target1: "Nâng Cao Độ Chính Xác Cho Thị Trường Việc Làm",
        target1Desc: "Giúp nhà tuyển dụng phân biệt rõ ràng: yêu cầu cốt lõi và kỹ năng có thể đào tạo. Giảm quá tải từ khóa trong JD và tạo động lực cho ứng viên trình bày sản phẩm thực tế — dự án, portfolio, bằng chứng công việc.",
        target2: "Tạo Niềm Tin Cho Cả Hai Phía",
        target2Desc: "Ứng viên biết chính xác khi nào sẵn sàng. Nhà tuyển dụng biết ứng viên có thể đóng góp ngay. Không còn bất bình đẳng thông tin — cả hai bên đều tự tin và thống nhất.",
        target3: "Xây Dựng Lực Lượng Lao Động Lành Nghề",
        target3Desc: "Bằng cách tối ưu hóa thời gian học tập từ 6-12 tháng xuống 2-3 tháng, chúng tôi giúp hàng triệu người sẵn sàng để bước vào thị trường công nghệ — có nền tảng vững chắc để học hỏi, phát triển, và nắm bắt cơ hội sự nghiệp."
      },
      cta: {
        heading: "Sẵn Sàng Mở Khóa Tiềm Năng?",
        description: "Tham gia hàng triệu người đang sử dụng Leveller.ai để tối ưu hóa lộ trình sự nghiệp của họ.",
        button: "Bắt Đầu Ngay"
      },
       vision: {
         heading: "Tầm nhìn & Sứ mệnh",
         text: "Chúng tôi tin rằng tương lai được xây dựng từ những kết nối thông minh. Leveller AI không chỉ là công cụ, mà là một hệ sinh thái tri thức giúp bạn xóa bỏ mọi giới hạn.",
         subtext: "Với công nghệ AI tiên tiến và Đồ thị Tri thức, chúng tôi tạo ra cầu nối giữa kỹ năng hiện tại và cơ hội tương lai của bạn.",
         accurate: "Chính xác",
         accurateDesc: "AI phân tích sâu để đưa ra đánh giá chính xác nhất",
         fast: "Nhanh chóng",
         fastDesc: "Kết quả trong vài phút, không phải vài ngày",
         effective: "Hiệu quả",
         effectiveDesc: "Lộ trình cá nhân hóa giúp bạn tiến nhanh hơn"
       },
       scrollHint: "Scroll to explore",
       testimonials_data: [
         {
           quote: "Leveller AI giúp tôi xác định những khoảng trống kỹ năng mà tôi không biết. Trong 3 tháng, tôi đã đạt được công việc mơ ước tại một công ty công nghệ hàng đầu.",
           author: "Nguyễn Văn A",
           role: "Software Engineer",
           company: "Tech Corp"
         },
         {
           quote: "Các đề xuất được hỗ trợ bởi AI rất chính xác. Lộ trình học tập được cá nhân hóa đã giúp tôi tiết kiệm hàng tháng thử và sai.",
           author: "Trần Thị B",
           role: "Data Analyst",
           company: "Analytics Inc"
         },
         {
           quote: "Là một người chuyển đổi sự nghiệp, Leveller AI đã cho tôi sự tự tin và hướng dẫn mà tôi cần. Phân tích khoảng trống kỹ năng rất chi tiết.",
           author: "Lê Văn C",
           role: "Product Manager",
           company: "Startup XYZ"
         }
        ],
       howItWorks: {
        heading: "Cách hoạt động",
        subheading: "Ba bước đơn giản để mở khóa tiềm năng nghề nghiệp của bạn",
        step1: "Tải CV lên",
        step1Desc: "Tải CV của bạn lên và để AI phân tích kỹ năng, kinh nghiệm và quỹ đạo nghề nghiệp.",
        step2: "Phân tích AI",
        step2Desc: "Thuật toán tiên tiến xác định khoảng trống kỹ năng, khớp cơ hội và tạo đề xuất cá nhân hóa.",
        step3: "Nhận kết quả",
        step3Desc: "Nhận thông tin chi tiết có thể hành động, đề xuất khóa học và lộ trình rõ ràng đến công việc mơ ước."
      },
      features: {
        heading: "Tương lai của tri thức",
        subheading: "Giải pháp toàn diện cho mọi đối tượng",
        professionals: "Chuyên gia",
        professionalsDesc: "Xây dựng và quản trị từ điển tri thức chuyên môn phức tạp thông qua kiến trúc Đồ thị Tri thức tiên tiến. Tự động hóa phân tích kỹ năng và chuẩn hóa quy trình chuyên gia.",
        applicants: "Ứng viên",
        applicantsDesc: "Giải mã khoảng trống kỹ năng (Skill Gap) và tối ưu hóa hồ sơ năng lực để dẫn đầu trong mọi cuộc săn tìm cơ hội.",
        students: "Sinh viên",
        studentsDesc: "Lộ trình học tập cá nhân hóa được tinh chỉnh bởi AI, giúp bạn rút ngắn khoảng cách từ giảng đường đến thực tế doanh nghiệp.",
        learnMore: "Tìm hiểu thêm"
      },
      testimonials: {
        heading: "Được tin tưởng bởi các chuyên gia",
        subheading: "Xem những gì người dùng của chúng tôi nói về trải nghiệm của họ"
      },
      footer: {
        product: "Sản phẩm",
        company: "Công ty",
        resources: "Tài nguyên",
        stayUpdated: "Cập nhật tin tức",
        newsletter: "Nhận tin tức và cập nhật mới nhất được gửi đến hộp thư của bạn.",
        emailPlaceholder: "Nhập email của bạn",
        copyright: "© 2026 Leveller AI. Tất cả quyền được bảo lưu.",
        privacy: "Chính sách bảo mật",
        terms: "Điều khoản dịch vụ",
        cookies: "Chính sách Cookie",
        features: "Tính năng",
        pricing: "Bảng giá",
        about: "Về chúng tôi",
        getStarted: "Bắt đầu ngay",
        careers: "Tuyển dụng",
        blog: "Blog",
        press: "Báo chí",
        contact: "Liên hệ",
        docs: "Tài liệu",
        helpCenter: "Trung tâm trợ giúp",
        api: "API",
        community: "Cộng đồng"
      }
    },
    en: {
       hero: {
         title: "Old systems say 'you don't fit.' We say 'you're this close.'",
        description: "Upload your CV, pick your target role — get a learning roadmap and match score in minutes.",
        getStarted: "Get started",
        learnMore: "Learn more"
      },
      stats: {
        cvs: "CVs Analyzed",
        accuracy: "Match Accuracy",
        companies: "Companies",
        support: "AI Support"
      },
      problem: {
        heading: "The Problem & Market Pain",
        title: "Lack of a clear development roadmap",
        description: "The demand for tech learning in Vietnam is massive — the EdTech market reached $1.1B in 2025, and Vietnamese learners are top 3 in terms of signups to technical MOOC courses. Yet the biggest problem isn't lack of learning materials, but lack of a clear development roadmap.",
        pain1: "28% of IT professionals are 'career changers' from Marketing, Sales — forced to manually read JDs, learn haphazardly, with no connected roadmap",
        pain2: "Job Descriptions are keyword-overloaded — a Junior Backend JD lists 25+ skills, but companies only need 5-6 core. Applicants don't know what's required vs 'nice-to-have'",
        pain3: "Result: learning takes 6-12 months instead of 2-3, missed opportunities, reduced motivation, untapped potential",
        employerHeading: "The Employer Side",
        employerTitle: "Your ATS is Rejecting Good Candidates",
        employerDesc: "ATS (Applicant Tracking System) is the software nearly every employer uses to filter resumes. It works by exact keyword matching — and it's rejecting your best candidates.",
        employerPain1: "JD lists 25+ keywords → exact match filter → 80% of viable candidates never reach a human",
        employerPain2: "Requires 'React' → CV has 'Vue.js' → rejected. False negative. That candidate is 2 weeks from ready.",
        employerPain3: "High hiring costs, long ramp-up time — because no one knows what the candidate actually needs."
      },
      solution: {
        heading: "Solution & Technology",
        featuresHeading: "Our Technology",
        title: "Smart CV & Job Description Analysis",
        description: "With just uploading your CV and desired job position, within minutes, Leveller.ai identifies exactly which high-impact skills you need.",
        insightTitle: "Skills are connected. ATS doesn't see that.",
        insightDesc: "ATS looks at each skill in isolation. We understand the links between them — so you can leverage what you already know.",
        compareHeading: "ATS vs Leveller",
        compareMatch: "Matching",
        compareMatchDesc: "Exact keyword — 80% false negatives",
        compareMatchDesc2: "Semantic proximity — finds what you're close to",
        compareSkill: "Skills",
        compareSkillDesc: "Self-reported endorsements",
        compareSkillDesc2: "AI-inferred from work context",
        compareFeedback: "Feedback",
        compareFeedbackDesc: "Silence or automated rejection",
        compareFeedbackDesc2: "Match score + gap analysis before you apply",
        feature1: "Multi-modal CV Parsing",
        feature1Desc: "Process CVs in any format — PDF, photos, or scans — using OCR Engine and LangGraph Orchestrator",
        feature2: "Auto Skill Level Inference",
        feature2Desc: "Automatically infer proficiency levels based on job descriptions, work duration, and experience context",
        feature3: "Semantic Skill Matching",
        feature3Desc: "Understands the real meaning behind each skill — not just keyword matching, but finding similar skills based on context and actual experience.",
        feature4: "Real-time Job Market Crawling",
        feature4Desc: "Continuously crawl data from TopCV and job listings to ensure Gap Analysis based on real market demand",
        feature5: "Multi-Platform Course Recommendations",
        feature5Desc: "Recommend courses from Coursera, YouTube and other platforms with direct access to optimize learning time",
        feature6: "Match Score & Salary Impact",
        feature6Desc: "Automatically calculate Match Score and Salary Impact based on real market data to help candidates understand skill value"
      },
      userSteps: {
        heading: "How It Works",
        step1: "Upload CV",
        step1Desc: "Upload CV image or PDF → System analyzes OCR + extracted skills",
        step2: "Select Position",
        step2Desc: "Select job position (e.g., Junior Backend) → View Skill Gap Map",
        step3: "Get Results",
        step3Desc: "See Match Score, recommended courses, salary data from TopCV"
      },
      impact: {
        heading: "Impact & Value",
        title: "Optimize Learning Time",
        description: "Leveller.ai not only identifies gaps but optimizes learning time so you can contribute immediately and unlock opportunities.",
        metric1: "Prioritized Skill Roadmap",
        metric1Desc: "Instead of learning 25 keywords, the system identifies 5-6 core skills to learn first. Result: reduce preparation time by 60-70%, from 6-12 months down to 2-3 months",
        metric2: "Skill Transferability & Strength Leverage",
        metric2Desc: "The system identifies related skills and what you can already transfer. Vue.js → React (1-2 weeks), Excel → SQL (Finance/Marketing professionals already have foundational thinking)",
        metric3: "Prioritized Learning Path",
        metric3Desc: "Each course is recommended based on its impact to your target role. You don't have to 'start from scratch' and can optimize your learning roadmap",
        transferHeading: "Three Layers of Transferability",
        sameCategory: "Same-category",
        sameCategoryDesc: "Vue.js ↔ React, Java ↔ C#. Syntax only.",
        adjacentDomain: "Adjacent-domain",
        adjacentDomainDesc: "Excel → SQL. Different surface, same logic.",
        professionalLeverage: "Professional Leverage",
        professionalLeverageDesc: "Sales → customer-facing tech. Communication transfers directly."
      },
      roadmap: {
        heading: "Roadmap",
        title: "Employer-Applicant Ecosystem",
        description: "We're building an ecosystem to unlock potential for millions of people.",
        feature1: "Employer Integration",
        feature1Desc: "Smart JD builder + real candidate readiness data — goes beyond traditional ATS. Primary revenue stream from talent discovery.",
        feature2: "Real-time Opportunity Matching",
        feature2Desc: "Get notified when new jobs match your learning roadmap — affiliate revenue per successful placement.",
        feature3: "AI CV Suggester",
        feature3Desc: "Automatically suggest CV improvements to increase Match Score with target job",
        feature4: "Interview Preparation",
        feature4Desc: "Suggest likely interview questions and optimal answers based on gap analysis",
        feature5: "Artifact Builder Guide",
        feature5Desc: "Guide building portfolio, projects, or real-world proof of skills to showcase expertise",
        feature6: "Semantic Skill Graph",
        feature6Desc: "Build semantic skill graph from collective data — more users means more accurate recommendations"
      },
      targets: {
        heading: "Three Effects",
        title: "Building the Future of Work",
        description: "We're creating three interconnected effects to transform the tech job market.",
        target1: "Cultivate Accuracy in the Tech Job Market",
        target1Desc: "Help employers distinguish core requirements from trainable skills. Reduce keyword overload in job descriptions and create incentives for candidates to showcase real artifacts — portfolios, projects, and proof of work.",
        target2: "Inspire Confidence on Both Sides",
        target2Desc: "Candidates know exactly when they're ready. Employers know candidates can contribute immediately. No more information asymmetry — both sides are confident and aligned.",
        target3: "Build a Skilled Tech Workforce",
        target3Desc: "By optimizing learning time from 6-12 months down to 2-3 months, we help millions get ready to enter the tech market — with a solid foundation to learn, grow, and seize career opportunities."
      },
      cta: {
        heading: "Ready to Unlock Your Potential?",
        description: "Join millions using Leveller.ai to optimize their career path.",
        button: "Get Started"
      },
      vision: {
        heading: "Vision & Mission",
        text: "We believe the future is built from intelligent connections. Leveller AI is not just a tool, but a knowledge ecosystem that helps you break through all limitations.",
        subtext: "With advanced AI technology and Knowledge Graph, we create a bridge between your current skills and future opportunities.",
        accurate: "Accurate",
        accurateDesc: "Deep AI analysis for the most precise assessment",
        fast: "Fast",
        fastDesc: "Results in minutes, not days",
        effective: "Effective",
        effectiveDesc: "Personalized roadmap helps you progress faster"
      },
      howItWorks: {
        heading: "How it works",
        subheading: "Three simple steps to unlock your career potential",
        step1: "Upload CV",
        step1Desc: "Upload your resume and let our AI analyze your skills, experience, and career trajectory.",
        step2: "AI Analysis",
        step2Desc: "Advanced algorithms identify skill gaps, match opportunities, and generate personalized recommendations.",
        step3: "Get Results",
        step3Desc: "Receive actionable insights, course recommendations, and a clear roadmap to your dream job."
      },
      features: {
        heading: "The future of knowledge",
        subheading: "Comprehensive solutions for everyone",
        professionals: "Professionals",
        professionalsDesc: "Build and manage complex professional knowledge dictionaries through advanced Knowledge Graph architecture. Automate skill analysis and standardize expert processes.",
        applicants: "Applicants",
        applicantsDesc: "Decode skill gaps and optimize your competency profile to lead in every opportunity hunt.",
        students: "Students",
        studentsDesc: "AI-refined personalized learning roadmap helps you shorten the gap from classroom to business reality.",
        learnMore: "Learn more"
      },
      testimonials: {
        heading: "Trusted by professionals",
        subheading: "See what our users have to say about their experience"
      },
      footer: {
        product: "Product",
        company: "Company",
        resources: "Resources",
        stayUpdated: "Stay updated",
        newsletter: "Get the latest news and updates delivered to your inbox.",
        emailPlaceholder: "Enter your email",
        copyright: "© 2026 Leveller AI. All rights reserved.",
        privacy: "Privacy Policy",
        terms: "Terms of Service",
        cookies: "Cookie Policy",
        features: "Features",
        pricing: "Pricing",
        about: "About",
        getStarted: "Get Started",
        careers: "Careers",
        blog: "Blog",
        press: "Press",
        contact: "Contact",
        docs: "Documentation",
        helpCenter: "Help Center",
        api: "API",
        community: "Community"
      }
    }
  };

  const currentLang = t[language];

  return (
    <div className={styles.pageRoot}>
      {/* Apple-style Glass Navbar */}
      <LandingNavbar />

      {/* Hero Section - Dark Immersive with Animated Gradient */}
      <div className={styles.sectionWrapper}>
        <section className={styles.heroSection}>
          {/* Background Image with Blur */}
          <div className={styles.heroBackground} />

          {/* Animated Gradient Overlay */}
          <div className={styles.heroGradient} />

          <motion.div
            className={styles.heroContent}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <h1 className={styles.heroTitle} dangerouslySetInnerHTML={{ __html: currentLang.hero.title }} />
            <p className={styles.heroDescription}>
              {currentLang.hero.description}
            </p>
            <div className={styles.heroActions}>
              <Link href="/auth/register" className={styles.primaryBtn}>
                {currentLang.hero.getStarted}
              </Link>
              <Link href="#how-it-works" className={styles.secondaryBtn}>
                {currentLang.hero.learnMore} <ChevronRight size={18} />
              </Link>
            </div>
          </motion.div>

          {/* Scroll Hint */}
          <motion.div
            className={styles.scrollHint}
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <div className={styles.scrollHintText}>Scroll to explore</div>
            <ChevronRight size={20} style={{ transform: 'rotate(90deg)' }} />
          </motion.div>
        </section>
      </div>

      {/* Problem/Pain Points Section */}
      <div className={styles.sectionWrapper}>
        <section className={styles.section}>
          <div className={styles.centeredText}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <h2 className={styles.sectionHeading}>{currentLang.problem.heading}</h2>
            </motion.div>
          </div>

          <motion.div
            className={styles.problemContent}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <p className={styles.problemDescription}>{currentLang.problem.description}</p>
            <div className={styles.painPointsGrid}>
              {[
                currentLang.problem.pain1,
                currentLang.problem.pain2,
                currentLang.problem.pain3
              ].map((pain, idx) => (
                <motion.div
                  key={idx}
                  className={styles.painPoint}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: idx * 0.15 }}
                >
                  <p>{pain}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>
      </div>

      {/* Employer Problem Section */}
      <div className={styles.sectionWrapper}>
        <section className={styles.section}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className={styles.centeredText}
          >
            <h2 className={styles.sectionHeading}>{currentLang.problem.employerHeading}</h2>
          </motion.div>
          <motion.div
            className={styles.problemContent}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <p className={styles.problemDescription}>{currentLang.problem.employerTitle}</p>
            <p className={styles.problemSubtext}>{currentLang.problem.employerDesc}</p>
            <div className={styles.painPointsGrid}>
              {[
                currentLang.problem.employerPain1,
                currentLang.problem.employerPain2,
                currentLang.problem.employerPain3
              ].map((pain, idx) => (
                <motion.div
                  key={idx}
                  className={styles.painPoint}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: idx * 0.15 }}
                >
                  <p>{pain}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>
      </div>

      {/* Solution Technology Features Section */}
      <div className={styles.sectionWrapper}>
        <section className={styles.section}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className={styles.sectionHeading}>{currentLang.solution.heading}</h2>
            <h3 className={styles.columnSubtitle}>{currentLang.solution.title}</h3>
            <p className={styles.columnDescription}>{currentLang.solution.description}</p>

            <motion.div
              className={styles.compareGrid}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <h3 className={styles.compareHeading}>{currentLang.solution.compareHeading}</h3>
              <div className={styles.compareRow}>
                <span className={styles.compareLabel}>{currentLang.solution.compareMatch}</span>
                <span className={styles.compareOld}>{currentLang.solution.compareMatchDesc}</span>
                <span className={styles.compareNew}>{currentLang.solution.compareMatchDesc2}</span>
              </div>
              <div className={styles.compareRow}>
                <span className={styles.compareLabel}>{currentLang.solution.compareSkill}</span>
                <span className={styles.compareOld}>{currentLang.solution.compareSkillDesc}</span>
                <span className={styles.compareNew}>{currentLang.solution.compareSkillDesc2}</span>
              </div>
              <div className={styles.compareRow}>
                <span className={styles.compareLabel}>{currentLang.solution.compareFeedback}</span>
                <span className={styles.compareOld}>{currentLang.solution.compareFeedbackDesc}</span>
                <span className={styles.compareNew}>{currentLang.solution.compareFeedbackDesc2}</span>
              </div>
            </motion.div>

            <motion.div
              className={styles.insightBlock}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <h3 className={styles.insightTitle}>{currentLang.solution.insightTitle}</h3>
              <p className={styles.insightDesc}>{currentLang.solution.insightDesc}</p>
            </motion.div>
          </motion.div>
        </section>
      </div>

      {/* Features / Technology Section */}
      <div className={styles.sectionWrapper}>
        <section className={styles.section}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className={styles.sectionHeading}>{currentLang.solution.featuresHeading}</h2>
            <div className={styles.featuresList}>
              {[
                { title: currentLang.solution.feature1, desc: currentLang.solution.feature1Desc },
                { title: currentLang.solution.feature2, desc: currentLang.solution.feature2Desc },
                { title: currentLang.solution.feature3, desc: currentLang.solution.feature3Desc },
                { title: currentLang.solution.feature4, desc: currentLang.solution.feature4Desc },
                { title: currentLang.solution.feature5, desc: currentLang.solution.feature5Desc },
                { title: currentLang.solution.feature6, desc: currentLang.solution.feature6Desc }
              ].map((feature, idx) => (
                <motion.div
                  key={idx}
                  className={styles.featureItem}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: idx * 0.1 }}
                >
                  <div>
                    <h4 className={styles.featureTitle}>{feature.title}</h4>
                    <p className={styles.featureDesc}>{feature.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>
      </div>

      {/* User Steps Section */}
      <div className={styles.sectionWrapper}>
        <section className={styles.section}>
          <div className={styles.twoColumnLayout} style={{ flexDirection: 'row-reverse' }}>
            <motion.div
              className={styles.columnText}
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <h2 className={styles.sectionHeading}>{currentLang.userSteps.heading}</h2>

              <div className={styles.stepsGrid}>
                {[
                  { step: '01', title: currentLang.userSteps.step1, desc: currentLang.userSteps.step1Desc },
                  { step: '02', title: currentLang.userSteps.step2, desc: currentLang.userSteps.step2Desc },
                  { step: '03', title: currentLang.userSteps.step3, desc: currentLang.userSteps.step3Desc }
                ].map((item, idx) => (
                  <motion.div
                    key={idx}
                    className={styles.stepCard}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.6, delay: idx * 0.15 }}
                  >
                    <div className={styles.stepNumber}>{item.step}</div>
                    <h4 className={styles.stepCardTitle}>{item.title}</h4>
                    <p className={styles.stepCardDesc}>{item.desc}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            <motion.div
              className={styles.columnScreenshot}
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <div className={styles.screenshotPlaceholder} style={{ backgroundImage: 'url(/images/dashboard.png)' }} />
            </motion.div>
          </div>
        </section>
      </div>

      {/* Impact Section */}
      <div className={styles.sectionWrapper}>
        <section className={styles.section}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className={styles.sectionHeading}>{currentLang.impact.heading}</h2>
            <h3 className={styles.columnSubtitle}>{currentLang.impact.title}</h3>
            <p className={styles.columnDescription}>{currentLang.impact.description}</p>

            <div className={styles.metricsGrid}>
              {[
                { title: currentLang.impact.metric1, desc: currentLang.impact.metric1Desc },
                { title: currentLang.impact.metric2, desc: currentLang.impact.metric2Desc },
                { title: currentLang.impact.metric3, desc: currentLang.impact.metric3Desc }
              ].map((metric, idx) => (
                <motion.div
                  key={idx}
                  className={styles.metricItem}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: idx * 0.1 }}
                >
                  <h4 className={styles.metricTitle}>{metric.title}</h4>
                  <p className={styles.metricDesc}>{metric.desc}</p>
                </motion.div>
              ))}
            </div>

            <motion.div
              className={styles.transferSection}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <h3 className={styles.transferHeading}>{currentLang.impact.transferHeading}</h3>
              <div className={styles.transferGrid}>
                <div className={styles.transferItem}>
                  <h4 className={styles.transferLabel}>{currentLang.impact.sameCategory}</h4>
                  <p className={styles.transferDesc}>{currentLang.impact.sameCategoryDesc}</p>
                </div>
                <div className={styles.transferItem}>
                  <h4 className={styles.transferLabel}>{currentLang.impact.adjacentDomain}</h4>
                  <p className={styles.transferDesc}>{currentLang.impact.adjacentDomainDesc}</p>
                </div>
                <div className={styles.transferItem}>
                  <h4 className={styles.transferLabel}>{currentLang.impact.professionalLeverage}</h4>
                  <p className={styles.transferDesc}>{currentLang.impact.professionalLeverageDesc}</p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </section>
      </div>

      {/* Roadmap Section */}
      <div className={styles.sectionWrapper}>
        <section className={styles.section}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className={styles.sectionHeading}>{currentLang.roadmap.heading}</h2>
            <h3 className={styles.columnSubtitle}>{currentLang.roadmap.title}</h3>
            <p className={styles.columnDescription}>{currentLang.roadmap.description}</p>

            <div className={styles.roadmapFeatures}>
              {[
                { title: currentLang.roadmap.feature1, desc: currentLang.roadmap.feature1Desc },
                { title: currentLang.roadmap.feature2, desc: currentLang.roadmap.feature2Desc },
                { title: currentLang.roadmap.feature3, desc: currentLang.roadmap.feature3Desc },
                { title: currentLang.roadmap.feature4, desc: currentLang.roadmap.feature4Desc },
                { title: currentLang.roadmap.feature5, desc: currentLang.roadmap.feature5Desc },
                { title: currentLang.roadmap.feature6, desc: currentLang.roadmap.feature6Desc }
              ].map((feature, idx) => (
                <motion.div
                  key={idx}
                  className={styles.roadmapItem}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: idx * 0.1 }}
                >
                  <div>
                    <h4 className={styles.roadmapTitle}>{feature.title}</h4>
                    <p className={styles.roadmapDesc}>{feature.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>
      </div>

      {/* Targets Section */}
      <div className={styles.sectionWrapper}>
        <section className={styles.section}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className={styles.sectionHeading}>{currentLang.targets.heading}</h2>
            <h3 className={styles.columnSubtitle}>{currentLang.targets.title}</h3>
            <p className={styles.columnDescription}>{currentLang.targets.description}</p>

            <div className={styles.targetsGrid}>
              {[
                { title: currentLang.targets.target1, desc: currentLang.targets.target1Desc },
                { title: currentLang.targets.target2, desc: currentLang.targets.target2Desc },
                { title: currentLang.targets.target3, desc: currentLang.targets.target3Desc }
              ].map((target, idx) => (
                <motion.div
                  key={idx}
                  className={styles.targetItem}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: idx * 0.1 }}
                >
                  <h4 className={styles.targetTitle}>{target.title}</h4>
                  <p className={styles.targetDesc}>{target.desc}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>
      </div>

      {/* CTA Section */}
      <div className={styles.sectionWrapper}>
        <section className={styles.section}>
          <motion.div
            className={styles.ctaContent}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className={styles.ctaHeading}>{currentLang.cta.heading}</h2>
            <p className={styles.ctaDescription}>{currentLang.cta.description}</p>
            <Link href="/auth/register" className={styles.primaryBtn}>
              {currentLang.cta.button}
            </Link>
          </motion.div>
        </section>
      </div>

      {/* Features Section - Testimonials */}
      <div id="testimonials" className={styles.sectionWrapper}>
        <section className={styles.section}>
          <div className={styles.centeredText}>
            <h2 className={styles.sectionHeading}>{currentLang.testimonials.heading}</h2>
            <p className={styles.sectionSubheading}>
              {currentLang.testimonials.subheading}
            </p>
          </div>

          <div className={styles.testimonialsGrid}>
            {[
              {
                quote: "Leveller AI helped me identify skill gaps I didn't even know I had. Within 3 months, I landed my dream job at a top tech company.",
                author: "Nguyễn Văn A",
                role: "Software Engineer",
                company: "Tech Corp",
                rating: 5
              },
              {
                quote: "The AI-powered recommendations were spot-on. The personalized learning roadmap saved me months of trial and error.",
                author: "Trần Thị B",
                role: "Data Analyst",
                company: "Analytics Inc",
                rating: 5
              },
              {
                quote: "As a career switcher, Leveller AI gave me the confidence and direction I needed. The skill gap analysis was incredibly detailed.",
                author: "Lê Văn C",
                role: "Product Manager",
                company: "Startup XYZ",
                rating: 5
              }
            ].map((testimonial, idx) => (
              <motion.div
                key={idx}
                className={styles.testimonialCard}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.6, delay: idx * 0.15 }}
              >
                <div className={styles.testimonialRating}>
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} size={16} fill="var(--color-secondary)" color="var(--color-secondary)" />
                  ))}
                </div>
                <p className={styles.testimonialQuote}>"{testimonial.quote}"</p>
                <div className={styles.testimonialAuthor}>
                  <div className={styles.authorAvatar}>
                    {testimonial.author.charAt(0)}
                  </div>
                  <div>
                    <div className={styles.authorName}>{testimonial.author}</div>
                    <div className={styles.authorRole}>
                      {testimonial.role} at {testimonial.company}
                    </div>
                  </div>
            </div>

          </motion.div>
          ))}
        </div>
      </section>
    </div>

      {/* Enhanced Footer */}
      <div className={styles.sectionWrapper}>
        <footer className={styles.richFooter}>
          <div className={styles.footerContent}>
            <div className={styles.footerGrid}>
              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.product}</h4>
                <Link href="#features">{currentLang.footer.features}</Link>
                <Link href="/auth/login">{currentLang.footer.pricing}</Link>
                <Link href="#philosophy">{currentLang.footer.about}</Link>
                <Link href="/auth/register">{currentLang.footer.getStarted}</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.company}</h4>
                <Link href="/auth/login">{currentLang.footer.careers}</Link>
                <Link href="/auth/login">{currentLang.footer.blog}</Link>
                <Link href="/auth/login">{currentLang.footer.press}</Link>
                <Link href="/auth/login">{currentLang.footer.contact}</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.resources}</h4>
                <Link href="/auth/login">{currentLang.footer.docs}</Link>
                <Link href="/auth/login">{currentLang.footer.helpCenter}</Link>
                <Link href="/auth/login">{currentLang.footer.api}</Link>
                <Link href="/auth/login">{currentLang.footer.community}</Link>
              </div>

              <div className={styles.footerColumn}>
                <h4 className={styles.footerHeading}>{currentLang.footer.stayUpdated}</h4>
                <p className={styles.footerNewsletter}>
                  {currentLang.footer.newsletter}
                </p>
                <div className={styles.newsletterForm}>
                  <input
                    type="email"
                    placeholder={currentLang.footer.emailPlaceholder}
                    className={styles.newsletterInput}
                  />
                  <button className={styles.newsletterButton}>
                    <Mail size={18} />
                  </button>
                </div>
              </div>
            </div>

            <div className={styles.footerBottom}>
              <p className={styles.footerCopyright}>
                {currentLang.footer.copyright}
              </p>
              <div className={styles.footerLinks}>
                <Link href="/auth/login">{currentLang.footer.privacy}</Link>
                <Link href="/auth/login">{currentLang.footer.terms}</Link>
                <Link href="/auth/login">{currentLang.footer.cookies}</Link>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
