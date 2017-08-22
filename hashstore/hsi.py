import logging
import os

from hashstore.ids import Cake
from hashstore.utils.args import CommandArgs, Switch

from hashstore import utils
from hashstore.udk import UDK
from hashstore.utils import print_pad
import hashstore.dir_scan as dscan


log = logging.getLogger(__name__)


ca = CommandArgs()

@ca.app('hsi - hashstore client')
class ClientApp:

    @ca.command(
        debug=('set logging level to DEBUG. default is INFO', Switch),
    )
    def __init__(self,debug):
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level)

    @ca.command('authorize client to interact with server',
                url='a url where server is running',
                user='email used for login. password '
                     'will be prompted.',
                dir='mount dir. Any directory within mount tree '
                   'will be authorized to access url above. '
                )
    def login(self, url, user, dir='.'):
        pass

    @ca.command('logout from server',
                dir='directory within mount that was authorized '
                   'with server previously. ')
    def logout(self, dir='.'):
        pass

    @ca.command('list directory as of last scan.')
    def ls(self, dir='.'):
        shamo = dscan.Shamo(dir)
        usage = shamo.directory_usage()
        print(shamo.dir_id())
        print_pad(usage, 'file_type size name'.split())
        print('total_size: %d' % sum( r['size'] for r in usage))

    @ca.command('find file with particular criteria.')
    def find(self, cake, dir='.'):
        results = []

        def find_recursively(directory, cake):
            try:
                files=dscan.Shamo(directory).directory_usage()
                for f in files:
                    f['name'] = os.path.join(directory, f['name'])
                    if f['file_type'] == 'DIR':
                        find_recursively(f['name'], cake)
                    f_cake = UDK.ensure_it(f['cake'])
                    if f_cake == cake:
                        results.append(f)
            except:
                log.warning(utils.exception_message())
        find_recursively(dir, Cake.ensure_it(cake))
        print_pad(results, 'file_type size cake name'.split())

    @ca.command('scan tree and recalcualte hashes for all changed files')
    def scan(self, dir='.'):
        udk = dscan.DirScan(dir).udk
        print(udk)

    @ca.command('save local files on remote server')
    def backup(self, dir):
        m = dscan.Remote(dir)
        print(m.backup())

    @ca.command('download remote changes for a dir',
                dir='directory where to restore. ',
                cake='content address or portal to restore from')
    def pull(self, cake, dir='.'):
        m = dscan.Remote(dir)
        m.restore(cake, dir)

    @ca.command('backup and pull. Use dir_id as portal.')
    def sync(self, dir='.'):
        pass

if __name__ == '__main__':
    ca.main()
