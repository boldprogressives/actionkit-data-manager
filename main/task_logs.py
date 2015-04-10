import logging
logger = logging.getLogger('aktasks')

class TaskLogger(object):

    def _str(self, task, *args):
        log_str = [unicode(task)]
        for arg in args:
            log_str.append(repr(arg))
        return " ".join(log_str)

    def activity_log(self, task, *args):
        logger.debug(self._str(task, *args))

    def sql_log(self, task, *args):
        logger.info(self._str(task, *args))

    def error_log(self, task, *args):
        logger.error(self._str(task, *args))

    def success_log(self, task, *args):
        logger.warn(self._str(task, *args))
