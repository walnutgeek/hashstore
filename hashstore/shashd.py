from hashstore.server import StoreServer


def args_parser():
    import argparse

    parser = argparse.ArgumentParser(description='shashd - hashstore server')

    parser.add_argument('command', choices=COMMANDS)

    parser.set_defaults(secure=None)
    parser.add_argument('--port', metavar='port', type=int, nargs='?',
                        default=7532, help='a port to listen.')
    parser.add_argument('--insecure', dest="secure", action='store_false',
                        help='start insecure server that does not require '
                             'client to register neiter for  read or  write '
                             '(default is when only writes  are secure')
    parser.add_argument('--secure', dest="secure", action='store_true',
                        help='start secure server that does not require '
                             'client to register for write and read '
                             '(default is when only writes  are secure')
    parser.add_argument('--store_dir', metavar='store_dir',
                        nargs='?', default='.',
                        help='a directory where local hashstore will reside')
    parser.add_argument('--config', metavar='config',
                        nargs='?', default=None,
                        help='json configuration file name or json content inlined')

    return parser

COMMANDS = 'start stop invite'.split()


def main():
    parser = args_parser()
    args = parser.parse_args()
    cmd_picked = [args.command == n for n in COMMANDS]
    doing = dict(zip(COMMANDS, cmd_picked))
    server = StoreServer(args.store_dir, args.port,
                                      args.secure)
    if doing['invite']:
        print(str(server.create_invitation()))
    else:
        server.shutdown(not(doing['stop']))
        if doing['start']:
            server.run_server()


if __name__ == '__main__':
    main()