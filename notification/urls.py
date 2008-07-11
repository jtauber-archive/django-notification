from django.conf.urls.defaults import *

# @@@ from atom import Feed

from notification.views import notices, mark_all_seen

urlpatterns = patterns('',
    url(r'^$', notices, name="notification_notices"),
    url(r'^mark_all_seen/$', mark_all_seen, name="notification_mark_all_seen"),
)
