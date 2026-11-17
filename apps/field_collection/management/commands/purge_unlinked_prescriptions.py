from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.field_collection.models import FieldPrescription

# The privacy notice tells patients unlinked prescriptions are deleted after
# 6 months (frontend src/lib/consent-notice.ts) — keep the two in sync.
RETENTION_DAYS = 183


class Command(BaseCommand):
    help = (
        f'Delete field prescriptions never linked to an account (unclaimed or disputed) '
        f'more than {RETENTION_DAYS} days after collection, including their image files. '
        'Run daily from cron.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='List what would be deleted without deleting.')

    def handle(self, *args, dry_run=False, **options):
        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        expired = FieldPrescription.objects.filter(
            patient__isnull=True, status__in=('unclaimed', 'disputed'), collected_at__lt=cutoff,
        ).prefetch_related('images')

        count = expired.count()
        if dry_run:
            self.stdout.write(f'{count} unlinked prescription(s) collected before {cutoff:%Y-%m-%d} would be deleted.')
            return

        files = 0
        for rx in expired:
            with transaction.atomic():
                for image in rx.images.all():
                    # Deleting rows leaves files on disk; remove them explicitly.
                    if image.file:
                        image.file.delete(save=False)
                        files += 1
                rx.delete()

        self.stdout.write(self.style.SUCCESS(
            f'Deleted {count} unlinked prescription(s) and {files} file(s) collected before {cutoff:%Y-%m-%d}.'
        ))
