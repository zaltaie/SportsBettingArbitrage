ERROR_MESSAGE = 'ERROR'
WARNING_MESSAGE = 'WARNING'
DEBUG_MESSAGE = 'DEBUG'
RESULT_MESSAGE = 'RESULT'

class CMessage(object):
    '''
    Class for printing terminal messages.
    '''
    def __init__(self, logfile = 'log.txt'):
        self._logname = logfile
        self._logfile = None
        self._logFile(self.logname)
        self.timing = {}


    def log_error(self, message, funcname = ''):
        '''
        Logs message with the 'ERROR' message.
        '''
        self._log(message, ERROR_MESSAGE)


    def log_warning(self, message, funcname = ''):
        '''
        Logs message with the 'WARNING' message.
        '''
        self._log(message, WARNING_MESSAGE)


    def log_debug(self, message, funcname = ''):
        '''
        Logs message with the 'DEBUG' message.
        '''
        self._log(message, DEBUG_MESSAGE)


    def log_result(self, message, funcname = ''):
        '''
        Logs message with the 'RESULT' message.
        '''
        self._log(message, RESULT_MESSAGE)


'''
    def _log(self, msg, level, funcname = ''):
        if funcname != '':
            message = "{0}::{1}::{2}".format(level, funcname, msg)
            print(message)
        else:
            message = "{0}::{1}".format(level, msg)
            print(message)
        if self._logfile is not None:
            self._logfile.write((message + '\n').encode('utf-8'))


    def _logFile(self, newname):
        '''
        #Make a new log file at the given location.
        '''
        if self._logfile is not None:
            self._logfile.close()
        self._logname = newname
        self._logfile = open(newname, 'wb')

'''

message = CMessage()
