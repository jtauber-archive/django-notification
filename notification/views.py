from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required

from notification.models import *

@login_required
def notices(request):
    notice_types = NoticeType.objects.all()
    notices = notices_for(request.user)
    settings_table = []
    for notice_type in NoticeType.objects.all():
        settings_row = []
        for medium_id, medium_display in NOTICE_MEDIA:
            form_label = "%s_%s" % (notice_type.label, medium_id)
            setting = get_notification_setting(request.user, notice_type, medium_id)
            if request.method == "POST":
                if request.POST.get(form_label) == "on":
                    setting.send = True
                else:
                    setting.send = False
                setting.save()
            settings_row.append((form_label, setting.send))
        settings_table.append({"notice_type": notice_type, "cells": settings_row})
    
    notice_settings = {
        "column_headers": [medium_display for medium_id, medium_display in NOTICE_MEDIA],
        "rows": settings_table,
    }
    
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