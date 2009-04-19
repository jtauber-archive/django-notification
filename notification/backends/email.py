from django.conf import settings
from django.db.models.loading import get_app
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.translation import ugettext
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured

from notification import backends
from notification.message import message_to_text

# favour django-mailer but fall back to django.core.mail
if "mailer" in settings.INSTALLED_APPS:
    from mailer import send_mail
else:
    from django.core.mail import send_mail

class EmailBackend(backends.BaseBackend):
    spam_sensitivity = 2
    
    def can_send(self, user, notice_type):
        from notification.models import should_send
        if should_send(user, notice_type, self.label) and user.email:
            return True
        return False
        
    def deliver(self, recipient, notice_type, extra_context):
        # TODO: require this to be passed in extra_context
        current_site = Site.objects.get_current()
        notices_url = u"http://%s%s" % (
            unicode(Site.objects.get_current()),
            reverse("notification_notices"),
        )
        
        # update context with user specific translations
        context = Context({
            "user": recipient,
            "notice": ugettext(notice_type.display),
            "notices_url": notices_url,
            "current_site": current_site,
        })
        context.update(extra_context)
        
        messages = self.get_formatted_messages((
            "short.txt",
            "full.txt"
        ), notice_type.label, context)
        
        subject = "".join(render_to_string("notification/email_subject.txt", {
            "message": messages["short.txt"],
        }, context).splitlines())
        
        body = render_to_string("notification/email_body.txt", {
            "message": messages["full.txt"],
        }, context)
        
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient])
