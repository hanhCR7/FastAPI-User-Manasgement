import aiosmtplib
import asyncio
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from models import EmailLogs
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_FROM = os.getenv("SMTP_FROM")

# Tạo một client SMTP dùng lại
smtp_client = aiosmtplib.SMTP(
    hostname=SMTP_SERVER,
    port=SMTP_PORT,
    username=SMTP_USERNAME,
    password=SMTP_PASSWORD,
    start_tls=True,
    timeout=30
)
async def send_email(db: Session, recipient: str, subject: str, body: str):
    """Gửi email bất đồng bộ với SMTP client dùng lại."""
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        if not smtp_client.is_connected:
            await smtp_client.connect()
            await smtp_client.login(SMTP_USERNAME, SMTP_PASSWORD)

        await smtp_client.send_message(msg)
        status = "Success"
    except aiosmtplib.errors.SMTPServerDisconnected:
        status = "Lỗi: Server không kết nối"
        await smtp_client.connect()
    except asyncio.TimeoutError:
        status = "Lỗi: Thời gian chờ trong khi gửi email"
        print("Timeout error: ", status)
    except aiosmtplib.SMTPException as e:
        status = f"Lỗi: {str(e)}"
    except Exception as e:
        status = f"Lỗi: {str(e)}"

    # Lưu log vào database
    email_log = EmailLogs(
        recipient=recipient,
        subject=subject,
        body=body,
        status=status,
        created_at=datetime.utcnow()
    )
    db.add(email_log)
    db.commit()

    return status == "Success"
