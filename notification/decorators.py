from django.utils.translation import ugettext as _
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.conf import settings

def basic_auth_required(test_func=None, realm=None):
    if realm is None:
        realm = getattr(settings, 'HTTP_AUTHENTICATION_REALM', _('Restricted Access'))
    if test_func is None:
        test_func = lambda u: u.is_authenticated()

    def decorator(view_func):
        def basic_auth(request, *args, **kwargs):
            # Just return the original view because already logged in
            if test_func(request.user):
                return view_func(request, *args, **kwargs)

            # Not logged in, look if login credentials are provided
            if 'HTTP_AUTHORIZATION' in request.META:        
                auth_method, auth = request.META['HTTP_AUTHORIZATION'].split(' ',1)
                if 'basic' == auth_method.lower():
                    auth = auth.strip().decode('base64')
                    username, password = auth.split(':',1)
                    user = authenticate(username=username, password=password)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            request.user = user
                            return view_func(request, *args, **kwargs)

            response =  HttpResponse(_('Authorization Required'), mimetype="text/plain")
            response.status_code = 401
            response['WWW-Authenticate'] = 'Basic realm="%s"' % realm
            return response
        return basic_auth
    return decorator
