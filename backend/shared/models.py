from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from .database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    daily_token_limit = Column(Integer, default=0) # 0 means use global default
    daily_analysis_limit = Column(Integer, default=0) # 0 means use global default
    is_flagged = Column(Boolean, default=False)

    # ── Security & Tracking ──────────────────────────────────────────
    registration_ip = Column(String(50))
    registration_user_agent = Column(Text)
    last_login_ip = Column(String(50))
    last_login_user_agent = Column(Text)

    cvs = relationship("UserCV", back_populates="user")
    last_analysis_id = Column(
        UUID(as_uuid=True), ForeignKey("user_analysis.id", ondelete="SET NULL"), nullable=True
    )
    last_analysis = relationship("UserAnalysis", foreign_keys=[last_analysis_id])

    # ── Market Fit Cache (Update once per day) ────────────────────────
    market_fit_score = Column(Float, default=0.0)
    market_fit_last_updated = Column(DateTime(timezone=True))
    market_fit_data = Column(JSON) # Lưu matched_jobs_count, percentile, vv.


class UserCV(Base):
    __tablename__ = "user_cvs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    file_id = Column(String(100), unique=True)  # ID định danh file trong Local Storage

    full_name = Column(String(255))
    summary = Column(Text)
    raw_text = Column(Text)  # Lưu trữ văn bản thô sau khi OCR (Markdown/Text)
    experience_years_total = Column(Float, default=0)
    file_hash = Column(String(64), index=True)  # SHA256 hash của file

    status = Column(String(20), default="processing")  # processing, completed, failed
    error_message = Column(
        Text
    )  # Lưu trữ thông báo lỗi chi tiết để hiển thị cho người dùng

    # ── CV Parsed Data (v3: parsed 1 lần, dùng nhiều lần) ──────────────
    cv_parsed_json = Column(
        JSON, nullable=True
    )  # Structured CV data (skills, work_history, etc.)
    cv_parsed_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp
    is_verified = Column(Boolean, default=False)  # User has confirmed parsed data

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="cvs")
    skills = relationship("UserSkillProfile", back_populates="cv")
    work_experiences = relationship("UserWorkExperience", back_populates="cv")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(100), unique=True, nullable=False)
    title_raw = Column(Text, nullable=False)
    title_category = Column(String(100), index=True)
    domain_role = Column(String(100), index=True)
    company_name = Column(String(255), index=True)
    source_url = Column(Text)
    source_label = Column(String(100))
    raw_text = Column(Text)
    
    # Parsed sections from job posting
    job_description = Column(Text)  # Mô tả công việc
    requirements = Column(Text)      # Yêu cầu ứng viên
    benefits = Column(Text)          # Quyền lợi

    min_salary_vnd = Column(BigInteger, index=True)
    max_salary_vnd = Column(BigInteger, index=True)
    required_exp_years = Column(Float)
    employment_type = Column(String(50))

    location_raw = Column(Text)
    location_normalized = Column(String(100), index=True)
    location_district = Column(String(100), index=True)

    status = Column(String(20), nullable=False, default="active")

    embedding_context = Column(Text)
    vector = Column(Vector(1536))  # pgvector embedding

    has_insurance = Column(Boolean, default=False)
    has_13th_month = Column(Boolean, default=False)
    remote_friendly = Column(Boolean, default=False)

    indexed_at = Column(DateTime(timezone=True))
    last_analyzed_at = Column(DateTime(timezone=True))
    extracted_requirements_json = Column(JSON)  # Lưu kết quả bóc tách từ LLM
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    skills_required = relationship("JobSkillRequirement", back_populates="job")
    analysis_reports = relationship("UserAnalysis", back_populates="job")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), unique=True, nullable=False)
    category = Column(String(100))
    parent_skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"))
    vector = Column(Vector(1536))

    requirements = relationship("JobSkillRequirement", back_populates="skill")
    user_profiles = relationship("UserSkillProfile", back_populates="skill")


class JobSkillRequirement(Base):
    __tablename__ = "job_skill_requirement"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"))
    importance_weight = Column(Integer)
    required_level = Column(String(20))
    min_years_exp = Column(Float)
    is_mandatory = Column(Boolean, default=True)

    job = relationship("Job", back_populates="skills_required")
    skill = relationship("Skill", back_populates="requirements")
    embedding_context = Column(Text)
    vector = Column(Vector(1536))


class UserSkillProfile(Base):
    __tablename__ = "user_skill_profile"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True))  # Will link to Auth service user if needed
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"))
    years_exp = Column(Float, default=0)
    level = Column(String(20))
    last_used_year = Column(Integer)
    skill_context = Column(Text)
    vector = Column(Vector(1536))
    confidence_score = Column(Float, default=1.0)
    source = Column(String(50), default="cv")
    cv_id = Column(UUID(as_uuid=True), ForeignKey("user_cvs.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cv = relationship("UserCV", back_populates="skills")
    skill = relationship("Skill")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("source_platform", "source_id", name="uq_course_source"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text)
    
    # ── Source Info ──────────────────────────────────────────────────
    source_platform = Column(String(100), index=True) # e.g. coursera, udemy
    source_id = Column(String(255), index=True)       # e.g. slug or internal id
    external_uuid = Column(String(100), index=True)   # e.g. 22-char ID for Coursera
    provider = Column(String(100))                    # e.g. IBM, Stanford
    platform = Column(String(100))                    # Legacy/Display platform name
    url = Column(Text)

    # ── Metadata (Enhanced) ──────────────────────────────────────────
    languages = Column(JSON)                          # List of language codes
    language = Column(String(10))                     # Primary language code
    level = Column(String(50))
    is_certification = Column(Boolean, default=False)
    duration_hours = Column(Float)
    duration_raw = Column(String(100))                # e.g. "2 weeks", "Approx. 6 months"
    cost_usd = Column(Float, default=0)
    
    # ── Rich Content (JSONB) ─────────────────────────────────────────
    skills_raw = Column(JSON)                         # Skills as provided by source
    tools_raw = Column(JSON)                          # Tools as provided by source
    outcomes = Column(JSON)                           # Learning outcomes
    modules = Column(JSON)                             # Modules/Syllabus
    tags = Column(ARRAY(Text))                        # Standardized tags
    
    # ── Vector Search ───────────────────────────────────────────────
    embedding_context = Column(Text)
    vector = Column(Vector(1536))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)


class UserWorkExperience(Base):
    __tablename__ = "user_work_experiences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cv_id = Column(UUID(as_uuid=True), ForeignKey("user_cvs.id", ondelete="CASCADE"))
    position_name = Column(String(255), nullable=False)
    company_name = Column(String(255))
    duration_years = Column(Float, default=0)
    description = Column(Text)
    skills_context = Column(JSON)  # Danh sách skills liên quan đến vị trí này
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cv = relationship("UserCV", back_populates="work_experiences")


class UserAnalysis(Base):
    __tablename__ = "user_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    cv_id = Column(
        UUID(as_uuid=True), ForeignKey("user_cvs.id", ondelete="CASCADE"), index=True
    )
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )

    match_score = Column(Float)
    result_json = Column(JSON)  # Lưu trữ toàn diện Breakdown và Recommendations

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
    cv = relationship("UserCV")
    job = relationship("Job", back_populates="analysis_reports")


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    analysis_id = Column(String(100), nullable=False)
    rating = Column(Integer)
    is_accurate = Column(Boolean)
    missing_skills = Column(JSON)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MarketSkillStats(Base):
    __tablename__ = "market_skill_stats"

    skill_name = Column(String(200), primary_key=True)
    category = Column(String(100), index=True)
    
    avg_salary_min = Column(BigInteger)
    avg_salary_max = Column(BigInteger)
    salary_premium_pct = Column(Float) # Phần trăm chênh lệch lương so với trung bình cùng nhóm
    
    job_count_30d = Column(Integer, default=0)
    growth_rate_30d = Column(Float, default=0.0) # Tỷ lệ tăng trưởng so với 30 ngày trước
    
    demand_score = Column(Float) # Điểm nhu cầu (0-100) dựa trên job_count và growth
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class YouTubeCourse(Base):
    __tablename__ = "youtube_courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(String(50), unique=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    thumbnail = Column(String(255))
    channel_name = Column(String(255))
    url = Column(Text)
    
    # Vector search support
    embedding_context = Column(Text)
    vector = Column(Vector(1536))
    
    # Metadata
    duration_raw = Column(String(50))
    published_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True), index=True) # Thời điểm hết hạn cache
    last_verified_at = Column(DateTime(timezone=True), index=True) # Thời điểm kiểm tra tính khả dụng gần nhất
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMLog(Base):
    __tablename__ = "llm_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    model_id = Column(String(100), nullable=False)
    provider = Column(String(50))
    call_type = Column(String(50))  # e.g., 'cv_parsing', 'gap_analysis', 'general'
    
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    latency_ms = Column(Integer)  # Time taken in milliseconds
    status = Column(String(20))   # 'success', 'failed'
    error_message = Column(Text)
    
    # Metadata for filtering/debugging
    request_metadata = Column(JSON) # Store additional info like call_id, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User")


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(String(20), index=True) # INFO, WARNING, ERROR, CRITICAL
    module = Column(String(100), index=True) # Email, AI, DB, Worker, Crawler
    message = Column(Text)
    details = Column(JSON) # Stacktrace, metadata, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
