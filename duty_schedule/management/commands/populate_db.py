from django.core.management.base import BaseCommand
from duty_schedule.models import ServiceMan, Unit


class Command(BaseCommand):
    help = "Populates DB with Unit and servicemen"

    # def add_arguments(self, parser):
    #     parser.add_argument("poll_ids", nargs="+", type=int)

    def handle(self, *args, **options):
        unit = Unit.objects.create(name='UAV')
        objs = (ServiceMan(name=f'Test{i}', surname=f'test{i}', unit=unit,
                           unavailable=False) for i in range(1, 12))
        ServiceMan.objects.bulk_create(objs)

        self.stdout.write(
            self.style.SUCCESS('Successfully populated db')
        )