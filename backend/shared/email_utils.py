import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

from shared.config_utils import config_manager

logger = logging.getLogger("email_utils")

def send_email(
    to_email: str,
    subject: str,
    body: str,
    is_html: bool = False
) -> bool:
    """
    Sends an email using SMTP settings from DB (via config_manager) or environment variables.
    """
    smtp_host = config_manager.get_setting("SMTP_HOST") or os.getenv("SMTP_HOST")
    smtp_port = int(config_manager.get_setting("SMTP_PORT") or os.getenv("SMTP_PORT", "587"))
    smtp_user = config_manager.get_setting("SMTP_USER") or os.getenv("SMTP_USER")
    smtp_pass = config_manager.get_setting("SMTP_PASS") or os.getenv("SMTP_PASS")
    from_email = config_manager.get_setting("SMTP_FROM") or os.getenv("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass]):
        logger.warning(f"[EMAIL] SMTP not configured. Would have sent email to {to_email}: {subject}")
        # Log the body for debugging
        logger.info(f"[EMAIL BODY]: {body[:100]}...")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        
        msg.attach(MIMEText(body, "html" if is_html else "plain"))

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"✓ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {e}")
        return False

def notify_queue_delay(user_email: str, queue_pos: int):
    """
    Specifically notify user about queue delay.
    """
    subject = "Thông báo: Hệ thống đang xử lý nhiều yêu cầu"
    body = f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
        <h2 style="color: #f59e0b;">Hệ thống đang bận</h2>
        <p>Chào bạn,</p>
        <p>Hiện tại hệ thống đang có <b>{queue_pos}</b> yêu cầu đang chờ xử lý trước bạn.</p>
        <p>Phân tích của bạn đã được đưa vào hàng đợi và sẽ hoàn thành trong giây lát. Chúng tôi sẽ cập nhật trạng thái ngay khi có kết quả.</p>
        <p>Cảm ơn bạn đã kiên nhẫn!</p>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #666;">Đây là email tự động từ hệ thống Lumix AI.</p>
    </div>
    """
    return send_email(user_email, subject, body, is_html=True)

def send_password_reset_email(user_email: str, reset_link: str):
    """
    Send password reset link to user.
    """
    subject = "Đặt lại mật khẩu - Lumix AI Advisor"
    body = f"""
    <div style="font-family: sans-serif; padding: 30px; border: 1px solid #e2e8f0; border-radius: 16px; background-color: #f8fafc; max-width: 500px; margin: auto;">
        <h2 style="color: #6366f1; text-align: center; margin-bottom: 24px;">Đặt lại mật khẩu</h2>
        <p>Chào bạn,</p>
        <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản Lumix AI của bạn. Vui lòng nhấn vào nút bên dưới để tiến hành thay đổi mật khẩu:</p>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{reset_link}" style="background-color: #6366f1; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                Đặt lại mật khẩu
            </a>
        </div>
        
        <p style="font-size: 14px; color: #64748b;">Nếu bạn không yêu cầu thay đổi mật khẩu, bạn có thể bỏ qua email này. Liên kết sẽ hết hạn trong vòng 1 giờ.</p>
        
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <p style="font-size: 12px; color: #94a3b8; text-align: center;">Lumix AI Advisor - Hệ thống tư vấn lộ trình nghề nghiệp AI</p>
    </div>
    """
    return send_email(user_email, subject, body, is_html=True)

def notify_cv_parsing_complete(user_email: str, cv_name: str, experience_years: int = None, skills_count: int = 0, frontend_url: str = None):
    """
    Notify user when CV parsing is completed.
    Checks EMAIL_NOTIFY_CV_COMPLETE setting before sending.
    """
    # Check if CV completion emails are enabled
    setting_value = config_manager.get_setting("EMAIL_NOTIFY_CV_COMPLETE", default="false")
    is_enabled = str(setting_value).lower() == "true" if setting_value else False
    
    if not is_enabled:
        logger.info(f"[EMAIL] CV completion notification disabled for {user_email}")
        return False
    
    subject = "✓ CV của bạn đã được phân tích xong - Lumix AI"
    
    exp_text = f"{experience_years} năm kinh nghiệm" if experience_years else "Chưa xác định kinh nghiệm"
    view_link = f"{frontend_url or os.getenv('FRONTEND_URL', 'http://localhost:3000')}/user/cv"
    
    body = f"""
    <div style="font-family: sans-serif; padding: 30px; border: 1px solid #e2e8f0; border-radius: 16px; background-color: #f8fafc; max-width: 500px; margin: auto;">
        <h2 style="color: #10b981; text-align: center; margin-bottom: 24px;">✓ CV đã được phân tích</h2>
        <p>Chào <strong>{cv_name or 'bạn'}</strong>,</p>
        <p>CV của bạn đã được hệ thống AI phân tích thành công!</p>
        
        <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 8px 0;"><strong>📄 Tên:</strong> {cv_name or 'N/A'}</p>
            <p style="margin: 8px 0;"><strong>💼 Kinh nghiệm:</strong> {exp_text}</p>
            <p style="margin: 8px 0;"><strong>🛠️ Kỹ năng:</strong> {skills_count} kỹ năng được trích xuất</p>
        </div>
        
        <p>Bạn có thể xem chi tiết CV hoặc bắt đầu phân tích Gap để tìm việc phù hợp!</p>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{view_link}" style="background-color: #10b981; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                Xem CV & Bắt đầu phân tích
            </a>
        </div>
        
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <p style="font-size: 12px; color: #94a3b8; text-align: center;">Lumix AI Advisor - Hệ thống tư vấn lộ trình nghề nghiệp AI</p>
    </div>
    """
    return send_email(user_email, subject, body, is_html=True)

def notify_gap_analysis_complete(user_email: str, match_score: float, skill_gaps_count: int, courses_count: int, cv_name: str = None, job_title: str = None, frontend_url: str = None):
    """
    Notify user when gap analysis is completed.
    Checks EMAIL_NOTIFY_GAP_COMPLETE setting before sending.
    """
    # Check if Gap analysis completion emails are enabled
    setting_value = config_manager.get_setting("EMAIL_NOTIFY_GAP_COMPLETE", default="false")
    is_enabled = str(setting_value).lower() == "true" if setting_value else False
    
    if not is_enabled:
        logger.info(f"[EMAIL] Gap analysis completion notification disabled for {user_email}")
        return False
    
    subject = f"✓ Kết quả phân tích Gap: {match_score}% phù hợp - Lumix AI"
    
    match_color = "#10b981" if match_score >= 70 else "#f59e0b" if match_score >= 50 else "#ef4444"
    match_emoji = "🎉" if match_score >= 70 else "💪" if match_score >= 50 else "📚"
    
    job_text = f" cho vị trí <strong>{job_title}</strong>" if job_title else ""
    view_link = f"{frontend_url or os.getenv('FRONTEND_URL', 'http://localhost:3000')}/user/analysis"
    
    body = f"""
    <div style="font-family: sans-serif; padding: 30px; border: 1px solid #e2e8f0; border-radius: 16px; background-color: #f8fafc; max-width: 500px; margin: auto;">
        <h2 style="color: {match_color}; text-align: center; margin-bottom: 24px;">{match_emoji} Kết quả phân tích Gap</h2>
        <p>Chào <strong>{cv_name or 'bạn'}</strong>,</p>
        <p>Phân tích khoảng cách kỹ năng{job_text} đã hoàn tất!</p>
        
        <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <div style="font-size: 48px; font-weight: bold; color: {match_color}; margin-bottom: 10px;">
                {match_score}%
            </div>
            <p style="color: #64748b; margin: 0;">Độ phù hợp với yêu cầu công việc</p>
        </div>
        
        <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 8px 0;"><strong>📊 Khoảng cách kỹ năng:</strong> {skill_gaps_count} kỹ năng cần cải thiện</p>
            <p style="margin: 8px 0;"><strong>🎓 Khóa học đề xuất:</strong> {courses_count} khóa học phù hợp</p>
        </div>
        
        <p>Xem chi tiết lộ trình học tập và các khóa học được đề xuất để nâng cao cơ hội nghề nghiệp!</p>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{view_link}" style="background-color: #6366f1; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                Xem kết quả chi tiết
            </a>
        </div>
        
        <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <p style="font-size: 12px; color: #94a3b8; text-align: center;">Lumix AI Advisor - Hệ thống tư vấn lộ trình nghề nghiệp AI</p>
    </div>
    """
    return send_email(user_email, subject, body, is_html=True)
