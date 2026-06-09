from __future__ import annotations

import html
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage


@dataclass(frozen=True)
class SMTPConfig:
    host: str
    port: int
    username: str
    password: str
    from_email: str
    use_tls: bool = True


class EmailNotificationService:
    """Send email digests using SMTP settings loaded from encrypted DB secrets."""

    def send_daily_agenda_email(
        self,
        *,
        smtp_config: SMTPConfig,
        to_email: str,
        subject: str,
        text_body: str,
    ) -> dict:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = smtp_config.from_email
        message["To"] = to_email
        message.set_content(text_body)
        message.add_alternative(self._to_html(text_body), subtype="html")

        with smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=30) as server:
            if smtp_config.use_tls:
                server.starttls()
            server.login(smtp_config.username, smtp_config.password)
            server.send_message(message)

        return {
            "ok": True,
            "provider": "smtp",
            "to_email": to_email,
            "subject": subject,
        }

    @staticmethod
    def _to_html(text_body: str) -> str:
        escaped = html.escape(text_body).replace("\n", "<br>")
        return f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.5;">
            <h2>Daily Agenda</h2>
            <p>{escaped}</p>
          </body>
        </html>
        """.strip()
