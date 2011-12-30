import django.dispatch


emitted_notices = django.dispatch.Signal(providing_args=["batches", "sent", "sent_actual", "run_time"])
