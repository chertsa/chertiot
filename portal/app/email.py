"""Minimal SMTP sender for portal-originated mail (project invites, M5.6). Best-effort: a send
failure is logged, never raised — the caller's action (e.g. creating an invite) still succeeds and
the invite link works regardless. Uses the same SMTP creds ThingsBoard uses (dev → mailpit)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

log = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True on success, False (logged) otherwise."""
    s = get_settings()
    if not s.smtp_host:
        log.info("SMTP not configured; skipping email to %s", to)
        return False
    msg = EmailMessage()
    msg["From"] = s.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
            if s.smtp_starttls:
                server.starttls()
            if s.smtp_user:
                server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError) as e:
        log.warning("invite email to %s failed: %s", to, e)
        return False
