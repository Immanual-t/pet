# File: store/management/commands/update_booking_statuses.py

from django.core.management.base import BaseCommand
from store.models.boarding import PetBoardingBooking
import datetime


class Command(BaseCommand):
    help = 'Automatically update pet boarding booking statuses based on current date and time'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Update booking statuses
        if dry_run:
            # For dry run, just report what would be updated
            today = datetime.date.today()
            now = datetime.datetime.now().time()

            overdue_bookings = PetBoardingBooking.objects.filter(
                status='approved',
                end_date__lt=today
            )

            today_ended_bookings = PetBoardingBooking.objects.filter(
                status='approved',
                end_date=today,
                end_time__lt=now
            )

            self.stdout.write(f'Found {overdue_bookings.count()} overdue bookings')
            self.stdout.write(f'Found {today_ended_bookings.count()} bookings ending today')

            for booking in overdue_bookings:
                self.stdout.write(
                    f'  Would mark overdue: Booking #{booking.id} ({booking.pet_name}) - ended {booking.end_date}')

            for booking in today_ended_bookings:
                self.stdout.write(
                    f'  Would mark completed: Booking #{booking.id} ({booking.pet_name}) - ended at {booking.end_time}')
        else:
            result = PetBoardingBooking.update_booking_statuses()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated {result["total_updated"]} booking(s):'
                )
            )
            self.stdout.write(f'  - {result["overdue_completed"]} overdue bookings marked as completed')
            self.stdout.write(f'  - {result["today_completed"]} bookings ending today marked as completed')

            if result['total_updated'] == 0:
                self.stdout.write(
                    self.style.SUCCESS('No bookings needed status updates.')
                )