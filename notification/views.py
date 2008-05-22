from django.shortcuts import render_to_response
from django.template import RequestContext
from notification.models import notices_for, NoticeType

def notices(request):
    notice_types = NoticeType.objects.all()
    if request.user.is_authenticated():
        notices = notices_for(request.user)
    else:
        notices = None
    return render_to_response("notification/notices.html", {
        "notices": notices,
        "notice_types": notice_types,
    }, context_instance=RequestContext(request))
