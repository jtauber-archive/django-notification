from django.conf.urls.defaults import *

# @@@ from atom import Feed

from notification.views import notices

urlpatterns = patterns('',
    url(r'^$', notices, name="notification_notices"),
)
