from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required

from notification.models import *

def notices(request):
    notice_types = NoticeType.objects.all()
    if request.user.is_authenticated():
        notices = notices_for(request.user)
        settings_table = []
        for notice_type in NoticeType.objects.all():
            settings_row = []
            for medium_id, medium_display in NOTICE_MEDIA:
                setting = NoticeSetting.objects.get(user=request.user, notice_type=notice_type, medium=medium_id).send
                settings_row.append(("%s_%s" % (notice_type.label, medium_id), setting))
            settings_table.append({"notice_type": notice_type, "cells": settings_row})
        
        notice_settings = {
            "column_headers": [medium_display for medium_id, medium_display in NOTICE_MEDIA],
            "rows": settings_table,
        }
    else:
        notices = None
        notice_settings = None
    
    return render_to_response("notification/notices.html", {
        "notices": notices,
        "notice_types": notice_types,
        "notice_settings": notice_settings,
    }, context_instance=RequestContext(request))

@login_required
def archive(request, noticeid=None, next_page=None):
    if noticeid:
        try:
            notice = Notice.objects.get(id=noticeid)
            if request.user == notice.user or request.user.is_superuser:
                notice.archive()
            else:   # you can archive other users' notices
                    # only if you are superuser.
                return HttpResponseRedirect(next_page)
        except Notice.DoesNotExist:
            return HttpResponseRedirect(next_page)
    return HttpResponseRedirect(next_page)

@login_required
def delete(request, noticeid=None, next_page=None):
    if noticeid:
        try:
            notice = Notice.objects.get(id=noticeid)
            if request.user == notice.user or request.user.is_superuser:
                notice.delete()
            else:   # you can delete other users' notices
                    # only if you are superuser.
                return HttpResponseRedirect(next_page)
        except Notice.DoesNotExist:
            return HttpResponseRedirect(next_page)
    return HttpResponseRedirect(next_page)