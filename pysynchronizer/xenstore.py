
from subprocess import Popen, PIPE

from .errors import PlatformError

class Xenstore:

    @staticmethod
    def read(key):
        xs = Popen(['xenstore-read', key], stdout=PIPE, close_fds=True, text=True)
        output, _ = xs.communicate()
        if xs.returncode != 0:
            raise PlatformError('unable to read syncvm object path: '
                                'xenstore-read failed')

        return output
