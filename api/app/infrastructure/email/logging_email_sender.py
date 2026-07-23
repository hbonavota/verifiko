import logging

from app.application.ports.email_sender import EmailMessage, EmailSenderPort

logger = logging.getLogger(__name__)


class LoggingEmailSender(EmailSenderPort):
    """Fallback used when no email provider is configured.

    It does not send anything; it logs the message so magic links are usable in
    development (read the link from the logs). Never wire this in production.
    """

    def send(self, message: EmailMessage) -> None:
        logger.info(
            "Email not sent (no provider configured). to=%s subject=%s body=%s",
            message.to,
            message.subject,
            message.text,
        )
