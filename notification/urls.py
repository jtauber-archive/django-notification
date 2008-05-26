from django.conf.urls.defaults import *

# @@@ from atom import Feed

urlpatterns = patterns('',
    (r'^$', 'notification.views.notices', name="notification_notices"),
)
