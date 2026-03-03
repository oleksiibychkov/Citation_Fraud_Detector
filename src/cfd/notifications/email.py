"""Email notification sender (§4.4/§11)."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_score_change_email(
    *,
    to_address: str,
    author_name: str,
    old_score: float,
    new_score: float,
    smtp_host: str,
    smtp_port: int = 587,
    smtp_user: str = "",
    smtp_password: str = "",
    from_address: str = "cfd-alerts@localhost",
) -> bool:
    """Send an email notification about a fraud score change.

    Returns True on success, False on failure (non-blocking).
    """
    subject = f"[CFD] Score change for {author_name}: {old_score:.3f} → {new_score:.3f}"
    body = (
        f"Citation Fraud Detector — Score Change Alert\n"
        f"==============================================\n\n"
        f"Author: {author_name}\n"
        f"Previous score: {old_score:.4f}\n"
        f"New score: {new_score:.4f}\n"
        f"Delta: {new_score - old_score:+.4f}\n\n"
        f"This is an automated alert. Please review in the CFD dashboard.\n"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address

    try:
        if smtp_port == 465:
            ctx = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            ctx = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        with ctx as server:
            if smtp_port != 465:
                server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_address, [to_address], msg.as_string())
        logger.info("Score change email sent to %s for %s", to_address, author_name)
        return True
    except Exception:
        logger.warning("Failed to send score change email to %s", to_address, exc_info=True)
        return False
