import hashstore.server as remote_store

COMMANDS = 'start stop invite register backup'.split()
SERVER_COMMANDS = COMMANDS[:3]

def args_parser():
    import argparse

    parser = argparse.ArgumentParser(description='shash - hashstore backup server and client')

    parser.add_argument('command', choices=COMMANDS)

    parser.set_defaults(secure=True)
    server_group = parser.add_argument_group('server', 'Server oprations: '
                                                       'Start/stop or invite')

    server_group.add_argument('--port', metavar='port', type=int, nargs='?',
                              default=7532, help='a port to listen.')
    server_group.add_argument('--insecure', dest="secure", action='store_false',
                             help='start insecure server that does not require '
                                  'mounts to register for backup')
    server_group.add_argument('--store_dir', metavar='store_dir',
                             nargs='?', default='.',
                             help='a directory where local hashstore will reside')


    backup_group = parser.add_argument_group('backup', 'Register directory for backup on remote store and execute backup')

    backup_group.add_argument('--url', metavar='url', nargs='?',
                                default=None,
                                help='a url where server is running')
    backup_group.add_argument('--dir', metavar='dir', nargs='?',
                        default='.',
                        help='directory to be backed up')
    return parser


def main():
    parser = args_parser()
    args = parser.parse_args()

    server_cmd_picked = [args.command == n for n in SERVER_COMMANDS]
    if any(server_cmd_picked):
        doing = dict(zip(SERVER_COMMANDS,server_cmd_picked))
        server = remote_store.StoreServer(args.store_dir, args.port,
                                          args.secure)
        print(doing)
        if doing['invite']:
            print(str(server.create_invitation()))
        else:
            server.shutdown(doing['stop'])
            if doing['start']:
                server.run_server()

    # mount commands
    elif args.command == 'register':
        pass
    elif args.command == 'backup':
        pass
    else:
        raise AssertionError('should never happen: %s' % args.command)


if __name__ == '__main__':
    main()