import argparse
import os
import sys
from pathlib import Path


def configure_django():
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vashandi_project.settings')

    import django
    django.setup()


def parse_args():
    parser = argparse.ArgumentParser(description='Send one sample HTML email for each notification type.')
    parser.add_argument('--recipient', required=True, help='Recipient email address for all sample notifications.')
    return parser.parse_args()


def main():
    args = parse_args()
    configure_django()

    from workers.email_utils import send_notification_samples

    results = send_notification_samples(args.recipient)
    failures = []
    for label, result in results:
        success, error = result
        if success:
            print(f'{label}: sent')
        else:
            failures.append((label, error))
            print(f'{label}: failed - {error}')

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
