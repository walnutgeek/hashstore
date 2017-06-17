from hashstore.mount import MountDB
import logging
logging.basicConfig(level=logging.INFO)


def args_parser():
    import argparse

    parser = argparse.ArgumentParser(description='shash - hashstore backup client')

    parser.add_argument('command', choices=COMMANDS)

    parser.set_defaults(secure=None)

    parser.add_argument('--url', metavar='url', nargs='?',
                        default=None,
                        help='a url where server is running')
    parser.add_argument('--invitation', metavar='invitation', nargs='?',
                        default=None,
                        help='invitation recieved from server')
    parser.add_argument('--dir', metavar='dir', nargs='?',
                        default='.',
                        help='directory to be backed up')
    parser.add_argument('--dest', metavar='dest', nargs='?',
                        default=None,
                        help='destination directory where '
                             'files will be restored')
    parser.add_argument('--udk', metavar='udk', nargs='?',
                        default=None,
                        help='version of directory to be restored')
    return parser

COMMANDS = 'register backup restore scan'.split()


def main():
    parser = args_parser()
    args = parser.parse_args()
    cmd_picked = [args.command == n for n in COMMANDS]
    doing = dict(zip(COMMANDS, cmd_picked))
    m = MountDB(directory=args.dir)
    if doing['register']:
        m.register(args.url,args.invitation)
    elif doing['backup']:
        print(m.backup())
    elif doing['restore']:
        m.restore(args.udk,args.dest)
    else: #scan
        _,udk = m.scan()
        print(udk)


if __name__ == '__main__':
    main()