"""Send the rendered edition through Gmail's SMTP server using the app password."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from . import config


def send_email(subject, html_body, to_addr=None):
    user = os.environ.get("GMAIL_USER", "").strip()
    app_pw = os.environ.get("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")
    to_addr = (to_addr or user).strip()

    if not user or not app_pw:
        raise RuntimeError("GMAIL_USER or GMAIL_APP_PASSWORD is missing.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config.PAPER_NAME} <{user}>"
    msg["To"] = to_addr

    plain = f"Your edition of {config.PAPER_NAME} is best viewed as HTML."
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(user, app_pw)
        server.sendmail(user, [to_addr], msg.as_string())

    return to_addr
