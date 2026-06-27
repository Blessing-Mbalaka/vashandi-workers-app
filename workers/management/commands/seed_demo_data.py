from pathlib import Path
import runpy

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed demo users, services, jobs, reviews, and project tracker sample data.'

    def handle(self, *args, **options):
        project_root = Path(__file__).resolve().parents[3]
        script_path = project_root / 'dummydata.py'
        runpy.run_path(str(script_path), run_name='__main__')
