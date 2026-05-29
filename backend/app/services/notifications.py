import smtplib
from email.mime.text import MIMEText
import httpx
from app.core.config import settings


async def send_telegram(message: str) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload)
        return response.status_code == 200


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not settings.SMTP_HOST or not settings.EMAIL_FROM:
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, [to_email], msg.as_string())

    return True
