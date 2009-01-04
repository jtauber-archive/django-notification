VERSION = (0, 1, 0, "pre")

def get_version():
    return "%s.%s.%s%s" % (VERSION[0], VERSION[1], VERSION[2], VERSION[3])

__version__ = get_version()