from django.contrib import admin


from .models import Unit, ServiceMan, DutyScheduler


@admin.register(ServiceMan)
class ServiceAdmin(admin.ModelAdmin):
    readonly_fields = ('next_duty_date', 'last_duty_date', 'scheduled_duties')
    fields = ('name', 'surname', 'unit', 'last_duty_date', 'next_duty_date', 'scheduled_duties', 'unavailable')
    filter = ('schedules_count', )

    @staticmethod
    def scheduled_duties(obj):
        from django.db.models import Count
        res = ServiceMan.objects.filter(pk=obj.id).aggregate(Count('schedules'))
        return res["schedules__count"]

    @staticmethod
    def next_duty_date(obj):
        return obj.schedules.first().duty_date


@admin.register(DutyScheduler)
class DutySchedulerAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(Unit)
