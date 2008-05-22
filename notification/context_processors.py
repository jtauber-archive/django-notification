from notification.models import unseen_count_for

def notification(request):
    if request.user.is_authenticated():
        return {'notice_unseen_count': unseen_count_for(request.user)}
    else:
        return {}
    