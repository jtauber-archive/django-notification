
class BaseBackend(object):
    """
    The base backend.
    """
    def can_send(self, user, notice_type):
        """
        Determines whether this backend is allowed to send a notification to
        the given user and notice_type.
        """
        return False
    
    def deliver(self, recipients, notice_type):
        """
        Called once each recipient has been verified with ``can_send``. This
        will determine the best way to deliver the notification to all
        recipients.
        """
        raise NotImplemented()
