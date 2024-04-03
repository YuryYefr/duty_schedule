from datetime import date, timedelta
# from .models import DutyScheduler


def check_week_num():
    today = date.today()
    year, month, day = today.year, today.month, today.day
    week_num = date(year, month, day).isocalendar().week
    return week_num


# def clean_past_duties():
#     # removing old duties
#     DutyScheduler.objects.filter(duty_date__lte=date.today() - timedelta(days=7)).delete()
