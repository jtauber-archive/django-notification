import django.dispatch


emitted_notices = django.dispatch.Signal(providing_args=["batches", "sent", "run_time"])
