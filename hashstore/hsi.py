import getpass
import logging
import os

from hashstore.bakery.cake_client import ClientUserSession, CakeClient
from hashstore.bakery import cake_or_path, Cake, portal_structs, \
    portal_from_name, Role
from hashstore.ndb.models.scan import FileType
from hashstore.utils.args import CommandArgs, Switch

from hashstore.utils import print_pad, exception_message
import hashstore.bakery.cake_scan as cscan


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
                email='email used for login. Password '
                     'will be prompted.',
                dir='mount dir. Any directory within mount tree '
                   'will be authorized to access url above. ',
                default=('use login as default', Switch)
                )
    def login(self, url, email, passwd=None, dir='.', default=False):
        if passwd is None:
            passwd = getpass.getpass()
        client = CakeClient()
        if not client.has_db():
            client.initdb()
        cu_session = ClientUserSession(client, url)
        cu_session.login(email, passwd=passwd)
        cu_session.create_mount_session(dir,default=default)


    @ca.command('logout from server',
                dir='directory within mount that was authorized '
                    'with server previously. ')
    def logout(self, dir='.'):
        pass

    @ca.command('list directory as of last scan.',cake=('Display cakes', Switch))
    def ls(self, dir='.', cake=False):
        cake = 'cake' if cake else ''
        entries = cscan.CakeEntries(dir)
        usage = entries.directory_usage()
        print("DirId: %s" % entries.dir_key().id)
        print("Cake: %s" % entries.bundle().cake())
        print('')
        print_pad(usage, ('file_type size '+cake+' name').split(), getattr)
        print('total_size: %d' % sum( r.size for r in usage))

    @ca.command('find file with particular criteria.')
    def find(self, cake, dir='.'):
        results = []

        def find_recursively(directory, cake):
            files=cscan.CakeEntries(directory).directory_usage()
            for f in files:
                path = os.path.join(directory, f.name)
                if f.cake == cake:
                    e = {k: getattr(f, k) for k in
                         'file_type size'.split()}
                    e['path'] = path
                    results.append(e)
                elif f.file_type == FileType.DIR:
                    find_recursively(path, cake)
        find_recursively(dir, Cake.ensure_it(cake))
        print_pad(results, 'file_type size path'.split())

    @ca.command('scan tree and recalculate hashes for all changed files')
    def scan(self, dir='.'):
        cake = cscan.DirScan(dir).entry.cake
        print(cake)

    @ca.command('save local files on remote server')
    def backup(self, dir='.'):
        client = CakeClient()
        cu_session = client.check_mount_session(dir)
        if cu_session is None:
            log.warning('{dir} is not mounted, use login command to '
                        'establish mount_session with server')
        else:
            portal_id,latest_cake = cscan.backup(dir, cu_session.proxy)
            print('DirId: {portal_id!s}\n'
                  'Cake: {latest_cake!s}\n'
                  ''.format(**locals()))


    @ca.command('download remote changes for a dir',
                dir='directory where to restore. ',
                cake='content address or portal to restore from')
    def pull(self, cake, dir='.'):
        client = CakeClient()
        cu_session = client.check_mount_session(dir)
        if cu_session is None:
            log.warning('{dir} is not mounted, use login command to '
                        'establish mount_session with server')
        else:
            src = cake_or_path(cake)
            cake = cscan.pull(cu_session.proxy, src, dir)
            print('From: {src!s} \nCake: {cake!s}\n'
                  .format(**locals()))

    @ca.command('backup and pull. Use dir_id as portal.')
    def sync(self, dir='.'):
        pass

    @ca.command('Create portal',
                portal_type=('Type of portal. Only needed if portal_id '
                             'is not provided. ',
                             portal_from_name, portal_structs ),
                portal_role=('Role of portal. Only needed if portal_id '
                             'is not provided. ',
                             Role.from_name, list(Role) ),
                portal_id=('Portal to be created. If omitted new '
                           'random portal_id will be created .', Cake),
                cake=('Optional. Cake that created portal points to. ',
                      Cake),
                dir=('directory, used to lookup mount session. ')
                )
    def create_portal(self, portal_id=None, portal_role=None,
                      portal_type=None, cake=None, dir='.'):
        if portal_id is None:
            portal_id = Cake.new_portal(role=portal_role,
                                        key_structure=portal_type)
        client = CakeClient()
        cu_session = client.check_mount_session(dir)
        if cu_session is None:
            log.warning('{dir} is not mounted, use login command to '
                        'establish mount_session with server')
        else:
            cu_session.proxy.create_portal(portal_id=portal_id,
                                           cake=cake)
        print('Portal: {portal_id!s} \nCake: {cake!s}\n'
                .format(**locals()) )

    @ca.command('Update path in vtree')
    def update_vtree(self, cake_path, cake=None, path=None ):
        pass

    @ca.command('Delete path in vtree')
    def delete_in_vtree(self, cake_path, cake=None ):
        pass

main = ca.main

if __name__ == '__main__':
    main()
