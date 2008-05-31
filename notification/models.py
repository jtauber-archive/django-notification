import datetime

from django.db import models
from django.conf import settings
from django.db.models import Q

from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from notification import backends
from notification.message import encode_message


class NoticeType(models.Model):
    
    label = models.CharField(_('label'), max_length=40)
    display = models.CharField(_('display'), max_length=50)
    description = models.CharField(_('description'), max_length=100)
    
    # by default only on for media with sensitivity less than or equal to this number
    default = models.IntegerField(_('default')) 
    
    def __unicode__(self):
        return self.label
    
    class Admin:
        list_display = ('label', 'display', 'description', 'default')
    
    class Meta:
        verbose_name = _("notice type")
        verbose_name_plural = _("notice types")
        

NOTIFICATION_BACKENDS = backends.load_backends()
NOTICE_MEDIA = tuple(
    ((i, backend_label) for i, backend_label in enumerate(NOTIFICATION_BACKENDS.keys()))
)

# how spam-sensitive is the medium
# TODO: fix this with the backends
NOTICE_MEDIA_DEFAULTS = {
    "1": 2 # email
}

class NoticeSetting(models.Model):
    """
    Indicates, for a given user, whether to send notifications
    of a given type to a given medium.
    """
    
    user = models.ForeignKey(User, verbose_name=_('user'))
    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))
    medium = models.CharField(_('medium'), max_length=1, choices=NOTICE_MEDIA)
    send = models.BooleanField(_('send'))
    
    class Admin:
        list_display = ('id', 'user', 'notice_type', 'medium', 'send')
    
    class Meta:
        verbose_name = _("notice setting")
        verbose_name_plural = _("notice settings")


def get_notification_setting(user, notice_type, medium):
    try:
        return NoticeSetting.objects.get(user=user, notice_type=notice_type, medium=medium)
    except NoticeSetting.DoesNotExist:
        default = (NOTICE_MEDIA_DEFAULTS[medium] <= notice_type.default)
        setting = NoticeSetting(user=user, notice_type=notice_type, medium=medium, send=default)
        setting.save()
        return setting


def should_send(user, notice_type, medium):
    return get_notification_setting(user, notice_type, medium).send


class Notice(models.Model):
    
    user = models.ForeignKey(User, verbose_name=_('user'))
    message = models.TextField(_('message'))
    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))
    added = models.DateTimeField(_('added'), default=datetime.datetime.now)
    unseen = models.BooleanField(_('unseen'), default=True)
    archived = models.BooleanField(_('archived'), default=False)
    
    def __unicode__(self):
        return self.message
    
    def archive(self):
        self.archived = True
        self.save()
    
    def is_unseen(self):
        """
        returns value of self.unseen but also changes it to false.
        
        Use this in a template to mark an unseen notice differently the first
        time it is shown.
        """
        unseen = self.unseen
        if unseen:
            self.unseen = False
            self.save()
        return unseen
    
    def html_message(self):
        return message_to_html(self.message)
    
    class Meta:
        ordering = ["-added"]
        verbose_name = _("notice")
        verbose_name_plural = _("notices")
    
    class Admin:
        list_display = ('message', 'user', 'notice_type', 'added', 'unseen', 'archived')


def create_notice_type(label, display, description, default=2):
    """
    create a new NoticeType.
    
    This is intended to be used by other apps as a post_syncdb manangement step.
    """
    try:
        notice_type = NoticeType.objects.get(label=label)
        updated = False
        if display != notice_type.display:
            notice_type.display = display
            updated = True
        if description != notice_type.description:
            notice_type.description = description
            updated = True
        if default != notice_type.default:
            notice_type.default = default
            updated = True
        if updated:
            notice_type.save()
            print "Updated %s NoticeType" % label
    except NoticeType.DoesNotExist:
        NoticeType(label=label, display=display, description=description, default=default).save()
        print "Created %s NoticeType" % label


def send(users, notice_type_label, message_template, object_list=None, issue_notice=True):
    """
    create a new notice.
    
    This is intended to be how other apps create new notices.
    """
    notice_type = NoticeType.objects.get(label=notice_type_label)
    message = encode_message(message_template, object_list)
    backend_recipients = {}

    for user in users:
        if issue_notice:
            notice = Notice(user=user, message=message, notice_type=notice_type)
            notice.save()
        for key, backend in NOTIFICATION_BACKENDS:
            recipients = backend_recipients.setdefault(key, [])
            if backend.can_send(user, notice_type):
                recipients.append(user)
    for key, backend in NOTIFICATION_BACKENDS:
        backend.deliver(backend_recipients[key], notice_type, message)


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