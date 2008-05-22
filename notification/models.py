import datetime

from django.db import models

from django.contrib.auth.models import User

class NoticeType(models.Model):
    
    label = models.CharField(max_length=20)
    display = models.CharField(max_length=50)
    description = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.label
    
    class Admin:
        list_display = ('label', 'display', 'description')


class Notice(models.Model):
    
    user = models.ForeignKey(User)
    message = models.TextField()
    notice_type = models.ForeignKey(NoticeType)
    added = models.DateTimeField(default=datetime.datetime.now)
    archived = models.BooleanField(default=False)
    
    def __unicode__(self):
        return self.message
    
    def archive(self):
        self.archived = True
        self.save()
    
    class Meta:
        ordering = ["-added"]
    
    class Admin:
        list_display = ('message', 'user', 'notice_type', 'added', 'archived')


def create_notice_type(label, display, description):
    notice_type, created = NoticeType.objects.get_or_create(label=label, display=display, description=description)
    if created:
        print "Created %s NoticeType" % label


def create(user, notice_type_label, message):
    notice_type = NoticeType.objects.get(label=notice_type_label)
    notice = Notice(user=user, message=message, notice_type=notice_type)
    notice.save()
    return notice


def notices_for(user, archived=False):
    """
    Returns all the Notices for a User.
    If archived is True, it includes archived Notices.
    """
    return Notice.objects.filter(user=user)
