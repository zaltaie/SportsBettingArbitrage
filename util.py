import sys

from message import message


def exit(code):
    """Exit the program. 0 = failure, 1 = success."""
    if not isinstance(code, int):
        message.log_error('Exit code must be an integer.')
        sys.exit(1)
    if code == 0:
        message.log_error('Exiting program with failure status.')
    elif code == 1:
        message.log_debug('Exiting program with success status.')
    else:
        message.log_error('Exiting program with unknown error status ({0})'.format(code))
    sys.exit(code if code in (0, 1) else 1)
