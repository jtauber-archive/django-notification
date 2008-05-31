from django.template.defaultfilters import stringfilter
from django.utils.translation import ugettext
from django import template

register = template.Library()

def do_ugettext(msg):
    """Given a message this returns its gettext translation"""
    return ugettext(msg)
register.simple_tag('ugettext', do_ugettext)
