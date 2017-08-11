from hashstore.server import StoreServer
from hashstore.mount import Mount
import six
import yaml
import logging

def args_parser():
    import argparse

    parser = argparse.ArgumentParser(description='%s - hashstore server' % __name__)

    parser.add_argument('command', choices=COMMANDS)

    parser.set_defaults(secure=None,debug=False)
    parser.add_argument('--port', metavar='port', type=int, nargs='?',
                        default=7532, help='a port to listen.')
    parser.add_argument('--store_dir', metavar='store_dir',
                        nargs='?', default='.',
                        help='a directory where hashstore data '
                             'will reside')
    parser.add_argument('--debug', dest="debug", action='store_true',
                        help='change logging level to debug. '
                             'default is INFO')

    return parser

COMMANDS = 'init start stop'.split()


def main():
    parser = args_parser()
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level)

    cmd_picked = [args.command == n for n in COMMANDS]
    doing = dict(zip(COMMANDS, cmd_picked))
    store_dir = args.store_dir
    port = args.port
    access_mode = AccessMode.from_bool(args.secure)
    mounts = None
    if args.config:
        config = yaml.safe_load(open(args.config))
        store_dir = config['store_dir']
        port = config['port']
        access_mode = AccessMode[config['access_mode']]
        mounts = { n: Mount(n,p) for n,p in six.iteritems(config['mounts'])}
    server = StoreServer(store_dir, port, access_mode, mounts)
    if doing['init']:
        pass
    else:
        server.shutdown(not(doing['stop']))
        if doing['start']:
            server.run_server()


if __name__ == '__main__':
    main()