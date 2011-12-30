import logging

from django.core.management.base import BaseCommand

from notification.engine import send_all


class Command(BaseCommand):
    help = "Emit queued notices."
    
    def handle(self, *args, **options):
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        logging.info("-" * 72)
        send_all(*args)
