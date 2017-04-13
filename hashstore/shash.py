import hashstore.remote_store as remote_store


def args_parser():
    import argparse

    parser = argparse.ArgumentParser(description='shash - hashstore backup server and client')

    parser.add_argument('command', choices='start stop register backup'.split())

    parser.set_defaults(secure=True)
    server_group = parser.add_argument_group('server', 'Start and stop remote hashstore')

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
    doing_start = args.command == 'start'
    doing_stop = args.command == 'stop'
    if doing_start or doing_stop:
        remote_store.shutdown(args.port, doing_stop)
        if doing_start:
            remote_store.run_server(args.store_dir, args.port)
    elif args.command == 'register':
        pass
    elif args.command == 'backup':
        pass

if __name__ == '__main__':
    main()