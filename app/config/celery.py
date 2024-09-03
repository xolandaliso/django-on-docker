import os
from celery import Celery
from celery.schedules import crontab


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.django.dev")
app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")
# app.conf.task_routes = {
#     "cworker.tasks.task1": {"queue": "queue1"},
#     "cworker.tasks.task2": {"queue": "queue2"},
# }

app.conf.beat_schedule = {
    'check-high-priority-tickets-every-minute': {
        'task': 'tickets.utils.check_high_priority_tickets',
        'schedule': crontab(minute='*'),      # runs every minute
    },
}

app.conf.beat_schedule = {
    'create-recurring-tickets-every-minute': {
        'task': 'tickets.utils.send_recurring_ticket_email',
        'schedule': crontab(minute='*/1'),  # Adjust the schedule as needed
    },
}

app.conf.task_default_rate_limit = "20/s"

app.conf.broker_transport_options = {
    "property_steps": list(range(10)),
    "sep": ":",
    "queue_order_strategy": "priority",
}



app.autodiscover_tasks()
