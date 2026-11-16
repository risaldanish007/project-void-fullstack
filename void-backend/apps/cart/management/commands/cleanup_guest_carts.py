from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cart.models import Cart


class Command(BaseCommand):
    help = "Delete guest carts that have been inactive for more than 31 days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many carts would be deleted without deleting them.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=31)

        old_guest_carts = Cart.objects.filter(
            user__isnull=True,
            guest_token__isnull=False,
            updated_at__lt=cutoff,
        )

        count = old_guest_carts.count()

        if options["dry_run"]:
            self.stdout.write(f"{count} abandoned guest cart(s) would be deleted.")
            return

        old_guest_carts.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} abandoned guest cart(s)."))