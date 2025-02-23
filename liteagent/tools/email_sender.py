import smtplib
import ssl

from email.message import EmailMessage
from liteagent import ToolDef, tool

def email_sender(
    smtp_server: str = "localhost",
    smtp_port: int = 1025,
    sender: str = "test@example.com",
    password: str | None = None,
    sslcontext: ssl.SSLContext | None = ssl.create_default_context()
) -> ToolDef:
    @tool(emoji='✉️')
    def send_email(
        to: str,
        subject: str,
        body: str,
        cc: str | None,
        bcc: str | None
    ) -> str:
        """ use this tool to send an email """

        msg = EmailMessage()

        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = cc

        if bcc:
            msg["Bcc"] = bcc

        msg.set_content(body)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if sslcontext:
                server.starttls(context=sslcontext)

            if password:
                server.login(sender, password)

            server.send_message(msg)

        return "email sent successfully"

    return send_email
