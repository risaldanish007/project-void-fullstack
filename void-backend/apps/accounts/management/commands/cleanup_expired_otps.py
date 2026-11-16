from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import EmailVerificationOTP


class Command(BaseCommand):
    help = (
        "Delete email verification OTP rows older than 24 hours. "
        "Recent rows are kept because the resend limit counts the last hour."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Minimum age in hours before an OTP row is deleted. Default: 24 (minimum 2).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many rows would be deleted without deleting them.",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        if hours < 2:
            raise CommandError("--hours must be at least 2 to protect the resend limit.")

        now = timezone.now()
        stale = EmailVerificationOTP.objects.filter(
            created_at__lt=now - timedelta(hours=hours),
            expires_at__lt=now,
        )
        count = stale.count()

        if options["dry_run"]:
            self.stdout.write(f"{count} old OTP row(s) would be deleted.")
            return

        stale.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} old OTP row(s)."))