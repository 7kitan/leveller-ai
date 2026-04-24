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
    smtp_host = config_manager.get_setting("smtp_host") or os.getenv("SMTP_HOST")
    smtp_port = int(config_manager.get_setting("smtp_port") or os.getenv("SMTP_PORT", "587"))
    smtp_user = config_manager.get_setting("smtp_user") or os.getenv("SMTP_USER")
    smtp_pass = config_manager.get_setting("smtp_pass") or os.getenv("SMTP_PASS")
    from_email = config_manager.get_setting("smtp_from") or os.getenv("SMTP_FROM", smtp_user)

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
