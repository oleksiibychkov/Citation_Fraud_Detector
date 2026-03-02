"""Notification dispatcher — routes score-change alerts to configured channels."""

from __future__ import annotations

import logging

from cfd.config.settings import Settings

logger = logging.getLogger(__name__)


def dispatch_score_change(
    *,
    settings: Settings,
    author_name: str,
    author_id: int | None,
    old_score: float,
    new_score: float,
) -> list[str]:
    """Send score-change notifications to all configured channels.

    Returns list of channel names that were successfully notified.
    Only dispatches if |delta| >= notification_score_threshold.
    """
    delta = abs(new_score - old_score)
    if delta < settings.notification_score_threshold:
        return []

    notified: list[str] = []

    # Email channel
    if settings.notification_email_enabled and settings.notification_email_to:
        from cfd.notifications.email import send_score_change_email

        ok = send_score_change_email(
            to_address=settings.notification_email_to,
            author_name=author_name,
            old_score=old_score,
            new_score=new_score,
            smtp_host=settings.notification_smtp_host,
            smtp_port=settings.notification_smtp_port,
            smtp_user=settings.notification_smtp_user,
            smtp_password=settings.notification_smtp_password,
        )
        if ok:
            notified.append("email")

    # Webhook channel
    if settings.notification_webhook_url:
        from cfd.notifications.webhook import send_score_change_webhook

        ok = send_score_change_webhook(
            url=settings.notification_webhook_url,
            author_name=author_name,
            author_id=author_id,
            old_score=old_score,
            new_score=new_score,
            secret=settings.notification_webhook_secret,
        )
        if ok:
            notified.append("webhook")

    if notified:
        logger.info("Notified %s about score change for %s", notified, author_name)

    return notified
