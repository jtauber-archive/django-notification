import datetime

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import render_to_string

from django.contrib.auth.models import User, SiteProfileNotAvailable

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext, get_language, activate

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


class NoticeManager(models.Manager):

    def notices_for(self, user, archived=False):
        """
        returns Notice objects for the given user.

        If archived=False, it only include notices not archived.
        If archived=True, it returns all notices for that user.
        """
        if archived:
            return self.filter(user=user)
        else:
            return self.filter(user=user, archived=archived)

    def unseen_count_for(self, user):
        """
        returns the number of unseen notices for the given user but does not
        mark them seen
        """
        return self.filter(user=user, unseen=True).count()

class Notice(models.Model):
    
    user = models.ForeignKey(User, verbose_name=_('user'))
    message = models.TextField(_('message'))
    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))
    added = models.DateTimeField(_('added'), default=datetime.datetime.now)
    unseen = models.BooleanField(_('unseen'), default=True)
    archived = models.BooleanField(_('archived'), default=False)
    
    objects = NoticeManager()
    
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
    
    class Meta:
        ordering = ["-added"]
        verbose_name = _("notice")
        verbose_name_plural = _("notices")
    
    class Admin:
        list_display = ('message', 'user', 'notice_type', 'added', 'unseen', 'archived')

def create_notice_type(label, display, description, default=2):
    """
    Creates a new NoticeType.
    
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

def get_formatted_messages(formats, label, context):
    """
    Returns a dictionary with the format identifier as the key. The values are
    are fully rendered templates with the given context.
    """
    format_templates = {}
    for format in formats:
        name = format.split(".")[0]
        format_templates[name] = render_to_string((
            'notification/%s/%s' % (label, format),
            'notification/%s' % format), context)
    return format_templates

def send(recipient, label, extra_context={}):
    """
    Creates a new notice.
    
    This is intended to be how other apps create new notices.
    
    notification.send(user, 'friends_invite_sent', {
        'spam': 'eggs',
        'foo': 'bar',
    )
    """
    if not isinstance(recipient, (list, tuple)):
        recipient = (recipient,)

    notice_type = NoticeType.objects.get(label=label)
    backend_recipients = {}
    
    context = Context({
        "notice": ugettext(notice_type.display),
        "notices_url": notices_url,
        "current_site": current_site,
    })
    context.update(extra_context)

    recipients = []
    current_language = get_language()

    formats = (
        'short.txt',
        'plain.txt',
        'teaser.html',
        'full.html',
    ) # TODO make formats configurable

    for user in recipient:
        # get user profiles if available
        try:
            profile = user.get_profile()
        except SiteProfileNotAvailable:
            profile = None

        # activate language of user to send message translated
        if profile is not None:
            # get language attribute of user profile
            language = getattr(profile, "language", None)
            if language is not None:
                # activate the user's language
                activate(language)

        # get prerendered format messages
        messages = get_formatted_messages(formats, label, context)

        # Strip newlines from subject
        subject = ''.join(render_to_string('notification/email_subject.txt', {
            'message': messages['short'],
        }, context).splitlines())
        
        body = render_to_string('notification/email_body.txt', {
            'message': messages['plain'],
        }, context)

        notice = Notice(user=user, message=message, notice_type=notice_type)
        notice.save()
        for key, backend in NOTIFICATION_BACKENDS:
            recipients = backend_recipients.setdefault(key, [])
            if backend.can_send(user, notice_type):
                recipients.append(user)
    for key, backend in NOTIFICATION_BACKENDS:
        backend.deliver(backend_recipients[key], notice_type, message)

    # reset environment to original language
    activate(current_language)

class ObservedItemManager(models.Manager):

    def all_for(self, observed, signal):
        """
        Returns all ObservedItems for an observed object,
        to be sent when a signal is emited.
        """
        content_type = ContentType.objects.get_for_model(observed)
        observed_items = self.filter(content_type=content_type, object_id=observed.id, signal=signal)
        return observed_items
    
    def get_for(self, observed, observer, signal):
        content_type = ContentType.objects.get_for_model(observed)
        observed_item = self.get(content_type=content_type, object_id=observed.id, user=observer, signal=signal)
        return observed_item


class ObservedItem(models.Model):

    user = models.ForeignKey(User, verbose_name=_('user'))
    
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    observed_object = generic.GenericForeignKey('content_type', 'object_id')
    
    notice_type = models.ForeignKey(NoticeType, verbose_name=_('notice type'))
    message_template = models.TextField(verbose_name=_('message template'))
    
    added = models.DateTimeField(_('added'), default=datetime.datetime.now)
    
    # the signal that will be listened to send the notice
    signal = models.TextField(verbose_name=_('signal'))
    
    objects = ObservedItemManager()
    
    class Meta:
        ordering = ['-added']
        verbose_name = _('observed item')
        verbose_name_plural = _('observed items')
    
    class Admin:
        pass
    
    def send_notice(self):
        send([self.user], self.notice_type.label, self.message_template,
             [self.observed_object])


def observe(observed, observer, notice_type_label, message_template, signal='post_save'):
    """
    Create a new ObservedItem.
    
    To be used by applications to register a user as an observer for some object.
    """
    notice_type = NoticeType.objects.get(label=notice_type_label)
    observed_item = ObservedItem(user=observer, observed_object=observed, notice_type=notice_type, message_template=message_template, signal=signal)
    observed_item.save()
    return observed_item

def stop_observing(observed, observer, signal='post_save'):
    """
    Remove an observed item.
    """
    observed_item = ObservedItem.objects.get_for(observed, observer, signal)
    observed_item.delete()

def send_observation_notices_for(observed, signal='post_save'):
    """
    Send a notice for each registered user about an observed object.
    """
    observed_items = ObservedItem.objects.all_for(observed, signal)
    for observed_item in observed_items:
        observed_item.send_notice()
    return observed_items

def is_observing(observed, observer, signal='post_save'):
    try:
        observed_items = ObservedItem.objects.get_for(observed, observer, signal)
        return True
    except ObservedItem.DoesNotExist:
        return False
    except ObservedItem.MultipleObjectsReturned:
        return True

def handle_observations(sender, instance, *args, **kw):
    send_observation_notices_for(instance)
