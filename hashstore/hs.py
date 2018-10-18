from . import hsi
from . import hsd
import sys


def main():
    args = sys.argv[1:]

    if len(args) > 0 and args[0] == 'server' :
        args = args[1:]
        executible = hsd.ca
    else:
        executible = hsi.ca
    executible.run(executible.parse_args(args))


if __name__ == '__main__':
    main()

