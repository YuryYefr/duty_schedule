from .helper import check_week_num

from django.db import models
from datetime import date, timedelta
from django.db.models import Q
import logging

logging.basicConfig(format="%(message)s")
log = logging.getLogger(__name__)


class Unit(models.Model):
    """
    Defining unit to get person from for schedule
    """

    name = models.CharField(max_length=10)
    men_count = models.IntegerField(
        default=4, help_text="How many servicemen required for duty"
    )

    # method to check each day duty by servicemen

    def __str__(self):
        return self.name

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        """
        trigger to refresh duties
        """
        if self.serviceman_set.exists():
            self.serviceman_set.first().save()
        return super().save()


class ServiceMan(models.Model):
    """
    Represents servicemen in Unit
    """

    class Meta:
        verbose_name = "Serviceman"
        verbose_name_plural = "Servicemen"

    name = models.CharField(max_length=20)
    surname = models.CharField(max_length=20)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, blank=False, null=False)
    # last_duty_date = models.DateField(blank=True, null=True)
    # last_duty = models.ForeignKey(DutyScheduler, on_delete=models.PROTECT)
    # last_duty_date = models.DateField(blank=True, null=True)  # read-only
    # next_duty_date = models.DateField(blank=True, null=True)  # read-only computed
    # duty_schedule = models.ManyToManyField(related_name='schedules',
    #                                        to=DutyScheduler,
    #                                        blank=True,
    #                                        null=True,
    #                                        default=None,
    #                                        )
    unavailable = models.BooleanField()

    def _get_next_duty_date(self):
        return self.schedules.first().duty_date

    def get_duties(self):
        return self.schedules.all()

    # def _get_last_duty_date(self):
    #     l_d_day = self.schedules.order_by('-duty_date').first().duty_date
    #     return l_d_day if l_d_day < date.today() else ''
    next_duty_date = property(_get_next_duty_date)  # read-only computed
    # last_duty_date = property(_get_last_duty_date)  # read-only computed
    last_duty_date = models.DateField(null=True, blank=True)  # read-only

    def __str__(self):
        return f"{self.surname}, {self.name}"

    def get_duty_count(self):
        return self.schedules.count()

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        res = super().save()
        week_num = check_week_num()
        tomorrow = date.today() + timedelta(days=1)
        # for each_day in range(date.today() + timedelta(days=7)):
        clean_past_duties()
        for each_day in (tomorrow + timedelta(d) for d in range(7)):
            # d_scheduler, created = DutyScheduler.objects.get_or_create(unit=self.unit, duty_date__gte=date.today(),
            #                                                            week_number=week_num)
            d_scheduler, created = DutyScheduler.objects.get_or_create(
                unit=self.unit, duty_date=each_day
            )
            d_scheduler.calculate(each_day)
        return res


def clean_past_duties():
    """
    removing old duties before recalculation
    """
    DutyScheduler.objects.all().delete()
    ServiceMan.objects.all().update(last_duty_date=None)


class DutyScheduler(models.Model):
    class Meta:
        ordering = ["-duty_date"]

    archived = models.BooleanField(default=False)
    # week_number = models.IntegerField()  # str repr to dates (date - date)
    duty_date = models.DateField(default=date.today())
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    servicemen = models.ManyToManyField(
        related_name="schedules",
        to=ServiceMan,
        # blank=True,
        # null=True,
        # default=None,
    )

    # def get_serviceman_with_min_duties(self, available_servicemen):
    #     servicemen = ServiceMan.objects.all()
    #     # res = min(servicemen, key=servicemen.get_duty_count)
    #     # res = available_servicemen.exclude(min(servicemen, key=servicemen.get_duty_count))
    #     for s_man in available_servicemen:
    #
    #     res = available_servicemen.exclude(min(servicemen, key=servicemen.get_duty_count))
    #     return available_servicemen.exclude(res)
    def duty_balancer(self, available_servicemen, s_men_count):
        """
        balancing duties for servicemen
        :return:
        """
        from django.db.models import Count, Max

        # for s in s_c:
        #     print(s)
        # scheduled_duties = schedule_set.schedules.annotate(c=Count('duty_date'))
        # while len(schedule_set) > self.unit.men_count:
        #     # schedule_set.exclude(max(schedule_set.c))
        #     # schedule_set.exclude(sch)
        #     schedule_set.exclude(max(schedule_set.schedules.all().count()))
        least_duties_s_men_ids = []
        duties_count = {}
        # while len(least_duties_s_men_ids) < len(available_servicemen):
        for s_man in available_servicemen:
            duties_count.update({"id": s_man.id, "duty_count": s_man.schedules.count()})
        sort_ids = sorted(duties_count)
        return sort_ids[:s_men_count]

    def calculate(self, duty_date):
        """
        recalculates scheduler for a UNIT of serviceman on save
        except of unavailable
        :return:
        """
        prev_day = duty_date - timedelta(days=1)
        s_men_count = self.unit.men_count
        from django.db.models import Count

        available_servicemen = (
            ServiceMan.objects.filter(
                Q(schedules__duty_date__isnull=True)
                | Q(last_duty_date__lt=prev_day)
                | Q(last_duty_date__isnull=True),
                unit=self.unit,
                unavailable=False,
            )
            .distinct()
            .annotate(c=Count("schedules"))
            .order_by("c")[:s_men_count]
        )
        ServiceMan.objects.filter(id__in=[s.id for s in available_servicemen]).update(
            last_duty_date=duty_date
        )

        if available_servicemen.count() < s_men_count:
            log.warning(f"Not enough people for {duty_date}")

        self.servicemen.add(*available_servicemen)
        self.save()

    def __str__(self):
        return (
            f"scheduled for {self.duty_date} - "
            + ", ".join(str(s_man.surname) for s_man in self.servicemen.all())
            if (self.servicemen.count() == self.unit.men_count)
            else f"Not enough people"
        )
