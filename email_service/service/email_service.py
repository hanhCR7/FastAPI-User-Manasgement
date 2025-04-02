import smtplib  
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from models import EmailLogs
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Load SMTP config từ .env
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_FROM = os.getenv("SMTP_FROM")

async def send_email(db: Session, recipient: str, subject: str, body: str):
    """Gửi email đồng bộ và lưu log vào database."""
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as smtp_client:
            smtp_client.set_debuglevel(1)  # Bật log SMTP
            smtp_client.ehlo()  # Xác thực EHLO trước khi TLS
            smtp_client.starttls()
            smtp_client.ehlo()  # Xác thực lại sau khi TLS
            smtp_client.login(SMTP_USERNAME, SMTP_PASSWORD)
            # Kiểm tra kết nối
            status_code, response = smtp_client.noop()
            if status_code != 250:
                raise Exception(f"SMTP connection failed: {response}")
            smtp_client.sendmail(SMTP_FROM, recipient, msg.as_string())
        # Lưu log vào database
        email_log = EmailLogs(
            recipient=recipient,
            subject=subject,
            body=body,
            status="Success",
            created_at=datetime.utcnow()
        )
        db.add(email_log)
        db.commit()

        return True
    except smtplib.SMTPAuthenticationError:
        print("❌ Lỗi xác thực! Kiểm tra lại username/password.")
    except smtplib.SMTPConnectError:
        print("❌ Không thể kết nối SMTP! Kiểm tra server hoặc cổng.")
    except Exception as e:
        print(f"❌ Lỗi gửi email: {e}")
    return False
