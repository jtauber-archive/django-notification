import datetime

from django.db import models
from django.conf import settings
from django.db.models import Q

from django.contrib.auth.models import User

# favour django-mailer but fall back to django.core.mail
try:
    from mailer import send_mail
except ImportError:
    from django.core.mail import send_mail


class NoticeType(models.Model):
    
    label = models.CharField(max_length=20)
    display = models.CharField(max_length=50)
    description = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.label
    
    class Admin:
        list_display = ('label', 'display', 'description')

# if this gets updated, the create() method below needs to be as well...
NOTICE_MEDIA = (
    ("1", "Email"),
)

class NoticeSetting(models.Model):
    """
    Indicates, for a given user, whether to send notifications
    of a given type to a given medium.
    """
    
    user = models.ForeignKey(User)
    notice_type = models.ForeignKey(NoticeType)
    medium = models.CharField(max_length=1, choices=NOTICE_MEDIA)
    send = models.BooleanField(default=True)
    
    class Admin:
        list_display = ('id', 'user', 'notice_type', 'medium', 'send')

def should_send(notice, medium, default):
    try:
        return NoticeSetting.objects.get(user=notice.user, notice_type=notice.notice_type, medium=medium).send
    except NoticeSetting.DoesNotExist:
        NoticeSetting(user=notice.user, notice_type=notice.notice_type, medium=medium, send=default).save()
        return default


class Notice(models.Model):
    
    user = models.ForeignKey(User)
    message = models.TextField()
    notice_type = models.ForeignKey(NoticeType)
    added = models.DateTimeField(default=datetime.datetime.now)
    unseen = models.BooleanField(default=True)
    archived = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.message
    
    def archive(self):
        self.archived = True
        self.save()
    
    def is_unseen(self):
        """
        returns value of self.unseen but also changes it to false
        """
        unseen = self.unseen
        if unseen:
            self.unseen = False
            self.save()
        return unseen
    
    class Meta:
        ordering = ["-added"]
    
    class Admin:
        list_display = ('message', 'user', 'notice_type', 'added', 'unseen', 'archived')


def create_notice_type(label, display, description):
    """
    create a new NoticeType.
    
    This is intended to be used by other apps as a post_syncdb manangement step.
    """
    notice_type, created = NoticeType.objects.get_or_create(label=label, display=display, description=description)
    if created:
        print "Created %s NoticeType" % label


def create(user, notice_type_label, message):
    """
    create a new notice.
    
    This is intended to be how other apps create new notices.
    """
    notice_type = NoticeType.objects.get(label=notice_type_label)
    notice = Notice(user=user, message=message, notice_type=notice_type)
    notice.save()
    if should_send(notice, "1", default=True) and user.email: # Email
        subject = "%s Notification From Pinax" % notice_type.display # @@@
        message = message # @@@
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    return notice


def notices_for(user, archived=False):
    """
    returns Notice objects for the given user.
    
    If archived=False, it only include notices not archived.
    If archived=True, it returns all notices for that user.
    Superusers receive all notices.
    """
    if user.is_superuser:
        q = Q()
    else:
        q = Q(user=user)
    if archived:
        return Notice.objects.filter(q)
    else:
        return Notice.objects.filter(q, archived=archived)


def unseen_count_for(user):
    """
    returns the number of unseen notices for the given user but does not
    mark them seen
    """
    return Notice.objects.filter(user=user, unseen=True).count()