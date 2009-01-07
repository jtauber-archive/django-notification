
import sys

from django.conf import settings
from django.core import exceptions

from base import BaseBackend

def load_backends():
    backends = []
    for label, backend_path in getattr(settings, "NOTIFICATION_BACKENDS", tuple()):
        dot = backend_path.rindex(".")
        backend_mod, backend_class = backend_path[:dot], backend_path[dot+1:]
        try:
            # import the module and get the module from sys.modules
            __import__(backend_mod)
            mod = sys.modules[backend_mod]
        except ImportError, e:
            raise exceptions.ImproperlyConfigured, 'Error importing notification backend %s: "%s"' % (backend_mod, e)
        # add the backend label and an instantiated backend class to the
        # backends list.
        backends.append(label, getattr(backend_mod, backend_class)(label))
    return dict(backend_list)
