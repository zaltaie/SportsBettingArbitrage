import sys
import numpy as np

from util.message import messages

def exit(code):
    '''
    Exit the program 0 is failure, while 1 is a success.
    '''
    if not isinstance(code, int):
        message.log_error('Exit code must be an interger.')
        exit(0)
    if code == 0:
        message.log_error('Exiting program with failure status.')
    elif code == 1:
        message.log_debug('Exiting program with success status.')
    else:
        message.log_error('Exiting program with unknown error status ('+str(code)+')')
    sys.exit()        
