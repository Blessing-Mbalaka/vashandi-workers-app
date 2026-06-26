import argparse
import os
import socket
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Test the SMTP configuration used by this Django project."
    )
    parser.add_argument(
        "--recipient",
        help=(
            "Email address to receive a test email. Defaults to SMTP_TEST_RECIPIENT, "
            "TEST_EMAIL_RECIPIENT, or DEFAULT_FROM_EMAIL if available."
        ),
    )
    parser.add_argument(
        "--skip-send",
        action="store_true",
        help="Only test the SMTP connection without sending an email.",
    )
    return parser.parse_args()


def configure_django():
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vashandi_project.settings")

    import django

    django.setup()


def mask_secret(value):
    if not value:
        return "(empty)"
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"


def print_settings(settings):
    print("SMTP settings")
    print(f"  backend: {settings.EMAIL_BACKEND}")
    print(f"  host: {settings.EMAIL_HOST}")
    print(f"  port: {settings.EMAIL_PORT}")
    print(f"  user: {settings.EMAIL_HOST_USER or '(empty)'}")
    print(f"  password: {mask_secret(settings.EMAIL_HOST_PASSWORD)}")
    print(f"  use_tls: {settings.EMAIL_USE_TLS}")
    print(f"  use_ssl: {settings.EMAIL_USE_SSL}")
    print(f"  from_email: {settings.DEFAULT_FROM_EMAIL}")


def resolve_recipient(cli_recipient, settings):
    return (
        cli_recipient
        or os.getenv("SMTP_TEST_RECIPIENT")
        or os.getenv("TEST_EMAIL_RECIPIENT")
        or settings.DEFAULT_FROM_EMAIL
    )


def test_connection(settings):
    from django.core.mail import get_connection

    connection = get_connection(
        backend=settings.EMAIL_BACKEND,
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        use_ssl=settings.EMAIL_USE_SSL,
        timeout=20,
    )

    connection.open()
    try:
        print("SMTP connection opened successfully.")
    finally:
        connection.close()
        print("SMTP connection closed.")


def send_test_email(settings, recipient):
    from django.core.mail import EmailMessage, get_connection

    connection = get_connection(
        backend=settings.EMAIL_BACKEND,
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        use_ssl=settings.EMAIL_USE_SSL,
        timeout=20,
    )

    message = EmailMessage(
        subject="Vashandi SMTP test email",
        body=(
            "This is a test email sent by smtp_test.py.\n\n"
            "If you received this message, the configured SMTP server is working."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        connection=connection,
    )

    sent_count = message.send(fail_silently=False)
    print(f"Test email send result: {sent_count} message(s) accepted by the server.")


def main():
    args = parse_args()
    configure_django()

    from django.conf import settings

    print_settings(settings)

    try:
        socket.gethostbyname(settings.EMAIL_HOST)
        print(f"DNS lookup succeeded for {settings.EMAIL_HOST}.")
    except socket.gaierror as exc:
        print(f"DNS lookup failed for {settings.EMAIL_HOST}: {exc}")
        return 1

    try:
        test_connection(settings)
    except Exception as exc:
        print(f"SMTP connection test failed: {exc.__class__.__name__}: {exc}")
        return 1

    if args.skip_send:
        print("Skipping email send as requested.")
        return 0

    recipient = resolve_recipient(args.recipient, settings)
    if not recipient or recipient.endswith("@vashandi.local"):
        print(
            "SMTP connection works, but no real recipient email is configured. "
            "Set SMTP_TEST_RECIPIENT or pass --recipient to send a real test email."
        )
        return 0

    try:
        send_test_email(settings, recipient)
        print(f"SMTP send test completed successfully to {recipient}.")
        return 0
    except Exception as exc:
        print(f"SMTP send test failed: {exc.__class__.__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
