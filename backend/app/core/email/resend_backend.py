"""Resend HTTP-API email backend.

Talks to https://api.resend.com over port 443 instead of SMTP. Required
on PaaS hosts (Railway, Render, Vercel, Heroku-style platforms) where
outbound SMTP on ports 25/465/587 is firewalled — the smtp backend
times out after ~30s in those environments because the SYN packet to
``smtp.resend.com:587`` never gets a SYN-ACK back.

Configuration comes from ``app.config.Settings``:

    ``resend_api_key`` — required; empty disables the backend.
    ``smtp_from``      — reused as the ``From:`` address. Resend
                         requires this domain to be verified in the
                         Resend dashboard.

The Resend SDK is synchronous (requests-based), so the blocking call
runs in ``asyncio.to_thread`` to keep the event loop responsive — same
pattern as ``SmtpEmailBackend``.
"""

from __future__ import annotations

import asyncio
import logging
import re

from app.config import Settings

from .base import BackendName, DeliveryResult, EmailBackend, EmailMessage

# ``resend`` is imported lazily inside ``_send_sync`` so the email package
# stays importable in environments that have not yet ``pip install``-ed
# the new dep (fresh checkouts before ``pip install -e .``, CI on a stale
# image, etc.). The cost is a tiny first-call import; the benefit is no
# package-wide ImportError ripple from a transport that may not be in use.

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _html_to_text(html: str) -> str:
    """Strip HTML tags so inbox-provider scoring sees a text/plain part."""
    text = _TAG_RE.sub(" ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return _WHITESPACE_RE.sub(" ", text).strip()


class ResendApiEmailBackend(EmailBackend):
    """Production transport via the Resend HTTP API."""

    name: BackendName = "resend_api"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _configured(self) -> bool:
        return bool(self._settings.resend_api_key)

    async def send(self, message: EmailMessage) -> DeliveryResult:
        if not self._configured():
            logger.warning(
                "[email:resend_api] dropping message to %s — RESEND_API_KEY not set "
                "(set RESEND_API_KEY to enable the resend_api backend)",
                message.to,
            )
            return DeliveryResult.failure(self.name, reason="resend_api not configured")

        try:
            return await asyncio.to_thread(self._send_sync, message)
        except Exception:  # noqa: BLE001 — convert any exception to a structured result
            logger.exception("[email:resend_api] unexpected failure delivering to %s", message.to)
            return DeliveryResult.failure(self.name, reason="unexpected error")

    def _send_sync(self, message: EmailMessage) -> DeliveryResult:
        import resend  # noqa: PLC0415 — lazy import; see module docstring

        settings = self._settings
        from_addr = message.from_addr or settings.smtp_from
        resend.api_key = settings.resend_api_key

        payload: dict[str, object] = {
            "from": from_addr,
            "to": [message.to],
            "subject": message.subject,
            "html": message.html_body,
            "text": _html_to_text(message.html_body),
        }
        if message.reply_to:
            payload["reply_to"] = message.reply_to
        if message.headers:
            payload["headers"] = dict(message.headers)
        if message.tags:
            # Resend tag format: list of {name, value} objects.
            payload["tags"] = [{"name": "category", "value": t} for t in message.tags]

        try:
            result = resend.Emails.send(payload)
            email_id = (result or {}).get("id") if isinstance(result, dict) else None
            logger.info(
                "[email:resend_api] sent to=%s subject=%r tags=%s id=%s",
                message.to,
                message.subject,
                message.tags or "-",
                email_id or "-",
            )
            return DeliveryResult.success(self.name, reason=f"sent id={email_id}" if email_id else "sent")
        except Exception as exc:  # noqa: BLE001 — Resend SDK exception classes vary by version; catch broadly
            # The SDK raises resend.exceptions.* subclasses for 4xx/5xx and
            # bubbles transport errors (requests / httpx) for network issues.
            # Treat them uniformly here — the structured reason carries the
            # exception class so operators can grep for it.
            logger.exception(
                "[email:resend_api] api error delivering to %s: %s", message.to, exc
            )
            return DeliveryResult.failure(self.name, reason=f"api error: {type(exc).__name__}")
