
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.translation import ugettext

from notification import backends

# favour django-mailer but fall back to django.core.mail
try:
    from mailer import send_mail
except ImportError:
    from django.core.mail import send_mail


class EmailBackend(backends.BaseBackend):
    def can_send(self, user, notice_type):
        if should_send(user, notice_type, "1") and user.email:
            return True
        return False
        
    def deliver(self, recipients, notice_type):
        notices_url = u"http://%s%s" % (
            unicode(Site.objects.get_current()),
            reverse("notification_notices"),
        )
        subject = render_to_string("notification/notification_subject.txt", {
            "display": ugettext(notice_type.display),
        })
        message_body = render_to_string("notification/notification_body.txt", {
            "message": message_to_text(message),
            "notices_url": notices_url,
            "contact_email": settings.CONTACT_EMAIL,
        })
        send_mail(subject, message_body,
            settings.DEFAULT_FROM_EMAIL, recipients)
