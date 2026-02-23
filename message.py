ERROR_MESSAGE = 'ERROR'
WARNING_MESSAGE = 'WARNING'
DEBUG_MESSAGE = 'DEBUG'
RESULT_MESSAGE = 'RESULT'


class CMessage(object):
    """Class for printing terminal messages and logging to file."""

    def __init__(self, logfile='log.txt'):
        self._logname = logfile
        self._logfile = None
        self._logFile(self._logname)
        self.timing = {}

    def log_error(self, message, funcname=''):
        """Logs message with the 'ERROR' prefix."""
        self._log(message, ERROR_MESSAGE, funcname)

    def log_warning(self, message, funcname=''):
        """Logs message with the 'WARNING' prefix."""
        self._log(message, WARNING_MESSAGE, funcname)

    def log_debug(self, message, funcname=''):
        """Logs message with the 'DEBUG' prefix."""
        self._log(message, DEBUG_MESSAGE, funcname)

    def log_result(self, message, funcname=''):
        """Logs message with the 'RESULT' prefix."""
        self._log(message, RESULT_MESSAGE, funcname)

    def _log(self, msg, level, funcname=''):
        if funcname:
            formatted = "{0}::{1}::{2}".format(level, funcname, msg)
        else:
            formatted = "{0}::{1}".format(level, msg)
        print(formatted)
        if self._logfile is not None:
            try:
                self._logfile.write((formatted + '\n').encode('utf-8'))
                self._logfile.flush()
            except Exception:
                pass

    def _logFile(self, newname):
        """Open a new log file at the given path."""
        if self._logfile is not None:
            try:
                self._logfile.close()
            except Exception:
                pass
        self._logname = newname
        try:
            self._logfile = open(newname, 'wb')
        except Exception:
            self._logfile = None


message = CMessage()
