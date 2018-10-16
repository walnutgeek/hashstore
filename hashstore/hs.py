from . import hsi
from . import hsd
import sys

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) > 0 and args[0] == 'server' :
        args = args[1:]
        executible = hsd.ca
    else:
        executible = hsi.ca
    executible.run(executible.parse_args(args))

