from hashstore.server import StoreServer
from hashstore.mount import MountDB


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


    backup_group = parser.add_argument_group('backup', 'Register '
                   'directory for  backup on remote store and execute '
                   'backup')

    backup_group.add_argument('--url', metavar='url', nargs='?',
                                default=None,
                                help='a url where server is running')
    backup_group.add_argument('--invitation', metavar='invitation', nargs='?',
                                default=None,
                                help='invitation recieved from server')
    backup_group.add_argument('--dir', metavar='dir', nargs='?',
                        default='.',
                        help='directory to be backed up')
    backup_group.add_argument('--dest', metavar='dest', nargs='?',
                        default=None,
                        help='destination directory where '
                             'files will be restored')
    backup_group.add_argument('--udk', metavar='udk', nargs='?',
                        default=None,
                        help='version of directory to be restored')
    return parser

COMMANDS = 'start stop invite register backup restore scan'.split()
SERVER_COMMANDS = lambda cmds: cmds[:3]
MOUNT_COMMANDS = lambda cmds: cmds[3:]

def main():
    parser = args_parser()
    args = parser.parse_args()
    cmd_picked = [args.command == n for n in COMMANDS]
    doing = dict(zip(COMMANDS, cmd_picked))
    if any(SERVER_COMMANDS(cmd_picked)):
        server = StoreServer(args.store_dir, args.port,
                                          args.secure)
        if doing['invite']:
            print(str(server.create_invitation()))
        else:
            server.shutdown(doing['stop'])
            if doing['start']:
                server.run_server()
        return
    elif any(MOUNT_COMMANDS(cmd_picked)):
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
        return
    raise AssertionError('should never happen: %s' % args.command)


if __name__ == '__main__':
    main()