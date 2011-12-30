import sys
import time
import logging
import traceback

try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.conf import settings
from django.core.mail import mail_admins
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

from lockfile import FileLock, AlreadyLocked, LockTimeout

from notification.models import NoticeQueueBatch
from notification.signals import emitted_notices
from notification import models as notification

# lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = getattr(settings, "NOTIFICATION_LOCK_WAIT_TIMEOUT", -1)


def send_all(*args):
    if len(args) == 1:
        lock = FileLock(args[0])
    else:
        lock = FileLock("send_notices")
    
    logging.debug("acquiring lock...")
    try:
        lock.acquire(LOCK_WAIT_TIMEOUT)
    except AlreadyLocked:
        logging.debug("lock already in place. quitting.")
        return
    except LockTimeout:
        logging.debug("waiting for the lock timed out. quitting.")
        return
    logging.debug("acquired.")
    
    batches, sent, sent_actual = 0, 0, 0
    start_time = time.time()
    
    try:
        # nesting the try statement to be Python 2.4
        try:
            for queued_batch in NoticeQueueBatch.objects.all():
                notices = pickle.loads(str(queued_batch.pickled_data).decode("base64"))
                for user, label, extra_context, sender in notices:
                    try:
                        user = User.objects.get(pk=user)
                        logging.info("emitting notice %s to %s" % (label, user))
                        # call this once per user to be atomic and allow for logging to
                        # accurately show how long each takes.
                        if notification.send_now([user], label, extra_context, sender):
                            sent_actual += 1
                    except User.DoesNotExist:
                        # Ignore deleted users, just warn about them
                        logging.warning("not emitting notice %s to user %s since it does not exist" % (label, user))
                    sent += 1
                queued_batch.delete()
                batches += 1
            emitted_notices.send(
                sender=NoticeQueueBatch,
                batches=batches,
                sent=sent,
                sent_actual=sent_actual,
                run_time="%.2f seconds" % (time.time() - start_time)
            )
        except:
            # get the exception
            exc_class, e, t = sys.exc_info()
            # email people
            current_site = Site.objects.get_current()
            subject = "[%s emit_notices] %r" % (current_site.name, e)
            message = "%s" % ("\n".join(traceback.format_exception(*sys.exc_info())),)
            mail_admins(subject, message, fail_silently=True)
            # log it as critical
            logging.critical("an exception occurred: %r" % e)
    finally:
        logging.debug("releasing lock...")
        lock.release()
        logging.debug("released.")
    
    logging.info("")
    logging.info("%s batches, %s sent" % (batches, sent,))
    logging.info("done in %.2f seconds" % (time.time() - start_time))
