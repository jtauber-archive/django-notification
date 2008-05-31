import datetime

from django.db import models
from django.conf import settings
from django.db.models import Q
from django.db.models import get_model

from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from notification import backends


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

# a notice like "foo and bar are now friends" is stored in the database
# as "{auth.User.5} and {auth.User.7} are now friends".
#
# encode_object takes an object and turns it into "{app.Model.pk}" or
# "{app.Model.pk.msgid}" if named arguments are used in send()
# decode_object takes "{app.Model.pk}" and turns it into the object
#
# encode_message takes either ("%s and %s are now friends", [foo, bar]) or
# ("%(foo)s and %(bar)s are now friends", {'foo':foo, 'bar':bar}) and turns
# it into "{auth.User.5} and {auth.User.7} are now friends".
#
# decode_message takes "{auth.User.5} and {auth.User.7}" and converts it
# into a string using the given decode function to convert the object to
# string representation
#
# message_to_text and message_to_html use decode_message to produce a
# text and html version of the message respectively.

def encode_object(obj, name=None):
    encoded = "%s.%s.%s" % (obj._meta.app_label, obj._meta.object_name, obj.pk)
    if name:
        encoded = "%s.%s" % (encoded, name)
    return "{%s}" % encoded

def encode_message(message_template, objects):
    if objects is None:
        return message_template
    if isinstance(objects, list) or isinstance(objects, tuple):
        return message_template % tuple(encode_object(obj) for obj in objects)
    if type(objects) is dict:
        return message_template % dict((name, encode_object(obj, name)) for name, obj in objects.iteritems())
    return ''

def decode_object(ref):
    decoded = ref.split(".")
    if len(decoded) == 4:
        app, name, pk, msgid = decoded
        return get_model(app, name).objects.get(pk=pk), msgid
    app, name, pk = decoded
    return get_model(app, name).objects.get(pk=pk), None

class FormatException(Exception):
    pass

def decode_message(message, decoder):
    out = []
    objects = []
    mapping = {}
    in_field = False
    prev = 0
    for index, ch in enumerate(message):
        if not in_field:
            if ch == '{':
                in_field = True
                if prev != index:
                    out.append(message[prev:index])
                prev = index
            elif ch == '}':
                raise FormatException("unmatched }")
        elif in_field:
            if ch == '{':
                raise FormatException("{ inside {}")
            elif ch == '}':
                in_field = False
                obj, msgid = decoder(message[prev+1:index])
                if msgid is None:
                    objects.append(obj)
                    out.append("%s")
                else:
                    mapping[msgid] = obj
                    out.append("%("+msgid+")s")
                prev = index + 1
    if in_field:
        raise FormatException("unmatched {")
    if prev <= index:
        out.append(message[prev:index+1])
    result = "".join(out)
    if mapping:
        args = mapping
    else:
        args = tuple(objects)
    return ugettext(result) % args

def message_to_text(message):
    def decoder(ref):
        obj, msgid = decode_object(ref)
        return unicode(obj), msgid
    return decode_message(message, decoder)

def message_to_html(message):
    def decoder(ref):
        obj, msgid = decode_object(ref)
        if hasattr(obj, "get_absolute_url"): # don't fail silenty if get_absolute_url hasn't been defined
            return u"""<a href="%s">%s</a>""" % (obj.get_absolute_url(), unicode(obj)), msgid
        else:
            return unicode(obj), msgid
    return decode_message(message, decoder)


def send(users, notice_type_label, message_template, object_list=None, issue_notice=True):
    """
    create a new notice.
    
    This is intended to be how other apps create new notices.
    """
    backends = NOTIFICATION_BACKENDS
    
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
        backend.deliver(backend_recipients[key], notice_type)


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