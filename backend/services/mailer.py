"""E-posta gönderme servisi.

Gönderim sırası:
1. RESEND_API_KEY tanımlıysa -> Resend HTTP API (önerilen, kurulumu en
   basit ve production'a en uygun olan; domain doğrulaması olmadan
   `onboarding@resend.dev` ile test gönderimi yapılabilir)
2. SMTP_HOST/SMTP_USER/SMTP_PASSWORD tanımlıysa -> düz SMTP (yerleşik
   smtplib, ek bağımlılık gerektirmez)
3. Hiçbiri yapılandırılmamışsa -> DEV MODU: e-posta gönderilmez, içerik
   konsola yazdırılır. Bu sayede herhangi bir sağlayıcı olmadan da
   kayıt/doğrulama akışı yerelde test edilebilir.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests


class EmailSendError(Exception):
    """E-posta hiçbir yöntemle gönderilemediğinde fırlatılır."""


def _resend_configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


def _smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"))


def _send_via_resend(*, to: str, subject: str, body: str) -> None:
    api_key = os.environ["RESEND_API_KEY"]
    from_addr = os.environ.get("RESEND_FROM", "VentureAgent <onboarding@resend.dev>")

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"from": from_addr, "to": [to], "subject": subject, "text": body},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise EmailSendError(f"Resend API'ye ulaşılamadı: {exc}") from exc

    if response.status_code >= 400:
        raise EmailSendError(f"Resend API hatası ({response.status_code}): {response.text}")


def _send_via_smtp(*, to: str, subject: str, body: str) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    from_addr = os.environ.get("SMTP_FROM", user)
    use_tls = os.environ.get("SMTP_USE_TLS", "True").strip().lower() == "true"

    message = MIMEMultipart()
    message["From"] = from_addr
    message["To"] = to
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [to], message.as_string())
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailSendError(f"SMTP üzerinden e-posta gönderilemedi: {exc}") from exc


def send_email(*, to: str, subject: str, body: str) -> None:
    """`to` adresine düz metin bir e-posta gönderir (bkz. modül üstü açıklama)."""
    if _resend_configured():
        _send_via_resend(to=to, subject=subject, body=body)
        return

    if _smtp_configured():
        _send_via_smtp(to=to, subject=subject, body=body)
        return

    print(
        "\n" + "=" * 60
        + f"\n[DEV MODU — e-posta sağlayıcısı yapılandırılmadı] E-posta gönderilmedi.\n"
        + f"Kime: {to}\nKonu: {subject}\n\n{body}\n"
        + "=" * 60 + "\n"
    )


def send_verification_email(*, to: str, name: str, code: str) -> None:
    """Kayıt sırasında gönderilen doğrulama kodu e-postası."""
    subject = "VentureAgent — E-posta Doğrulama Kodun"
    body = (
        f"Merhaba {name},\n\n"
        f"VentureAgent hesabını doğrulamak için aşağıdaki kodu kullan:\n\n"
        f"    {code}\n\n"
        f"Bu kod 15 dakika boyunca geçerlidir.\n\n"
        f"Bu isteği sen yapmadıysan bu e-postayı yok sayabilirsin."
    )
    send_email(to=to, subject=subject, body=body)
