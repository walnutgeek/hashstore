import logging
import os
from hashstore.utils.args import CliArgs, Switch, Opt

from hashstore import utils
from hashstore.udk import UDK
from hashstore.utils import print_pad

log = logging.getLogger(__name__)

cli_args = CliArgs('hsi - hashstore client', {
    '':[
        Switch('debug', 'set logging level to DEBUG. default is INFO'),
    ],
    'login -  authorize client to interact with server': [
        Opt('url', 'a url where server is running'),
        Opt('email', 'email used for login. password '
                     'will be prompted.'),
        Opt('token', 'API token recived from server.'),
        Opt('dir', 'mount dir. Any directory within mount tree '
                   'will be authorized to access particular server',
            default='.')
    ],
    'logout - logout from server ': [
        Opt('dir', 'directory within mount that was authorized '
                   'with server. ',
            default='.'),
        Switch('all', 'logout out of all mounts for this user'),
    ],
    'ls -  list directory from last scan': [
        Opt('dir', 'directory to list information about. ', '.'),
    ],
    'find - find file with particular criteria': [
        Opt('dir', 'directory where to strat looking. ', '.'),
        Opt('cake', 'all files that have same content address'),
    ],
    'scan - scan  tree and recalcualte hashes for all changed files': [
        Opt('dir', 'directory to scan. ', '.'),
    ],
    'backup - save local files on remote server': [
        Opt('dir', 'directory to backup. ', '.'),
    ],
    'pull - download remote changes for a dir': [
        Opt('dir', 'directory where to restore. ', '.'),
        Opt('portal')
    ],
    'sync - backup and pull': [
        Opt('dir', 'directory where to restore. ', '.'),

    ]
})

import hashstore.dir_scan as dscan

class Logic:

    def login(self, args):
        m = dscan.Remote(args.dir)
        m.register(args.url, args.invitation)

    def logout(self, args):
        pass

    def ls(self, args):
        shamo = dscan.Shamo(args.dir)
        usage = shamo.directory_usage()
        print(shamo.dir_id())
        print_pad(usage, 'file_type size name'.split())
        print('total_size: %d' % sum( r['size'] for r in usage))

    def find(self,args):
        results = []
        def find(directory, udk):
            try:
                files=dscan.Shamo(directory).directory_usage()
                for f in files:
                    f['name'] = os.path.join(directory, f['name'])
                    if f['file_type'] == 'DIR':
                        find(f['name'], udk)
                    f_udk = UDK.ensure_it(f['udk'])
                    if f_udk == udk:
                        results.append(f)
            except:
                log.warning(utils.exception_message())
        find(args.dir,UDK.ensure_it(args.udk))
        print_pad(results, 'file_type size udk name'.split())

    def scan(self, args):
        udk = dscan.DirScan(args.dir).udk
        print(udk)

    def backup(self, args):
        m = dscan.Remote(args.dir)
        print(m.backup())

    def pull(self, args):
        m = dscan.Remote(args.dir)
        m.restore(args.udk, args.dest)

    def sync(self, args):
        pass


def main():
    args = cli_args.parse_args()
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level)
    logic = Logic()
    getattr(logic, args.command)(args)


if __name__ == '__main__':
    main()