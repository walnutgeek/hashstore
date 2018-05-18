import getpass
import logging
import os
import sys
from hashstore.bakery.cake_client import ClientUserSession, CakeClient
from hashstore.bakery import Cake, PORTAL_TYPES, \
    portal_from_name, CakeRole, CakePath, process_stream, CakeType, \
    PatchAction, ensure_cakepath
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

    def _check_cu_session(self, dir):
        client = CakeClient()
        self.cu_session = client.check_mount_session(dir)
        if self.cu_session is None:
            log.warning('{dir} is not mounted, use login command to '
                        'establish mount_session with server')
            sys.exit(-1)

    def remote(self):
        return self.cu_session.proxy


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
        cake = cscan.DirScan(cscan.ScanPath(dir)).entry.cake
        print(cake)

    @ca.command('save local files on remote server',
                portal_type=('Type of portal. Only used if '
                             'remote_path is not provided. ',
                             portal_from_name,
                             (CakeType.VTREE, CakeType.PORTAL)),
                remote_path=('CakePath where data should be saved. ',
                             CakePath.ensure_it_or_none),
                )
    def backup(self, dir='.', remote_path=None,
               portal_type=None ):
        self._check_cu_session(dir)
        scan_path = cscan.ScanPath(dir)
        dirkey = scan_path.cake_entries().dir_key()
        if remote_path is None:
            if portal_type is not None:
                remote = dirkey.id.transform_portal(portal_type)
                remote_path = CakePath(None, _root=remote)
            else:
                print(dirkey.id)
                if dirkey.last_backup_path is None:
                    remote = dirkey.id.transform_portal(CakeType.PORTAL)
                    remote_path = CakePath(None, _root=remote)
                else:
                    remote_path = dirkey.last_backup_path
        scan_path.set_remote_path(remote_path)
        portal_id,latest_cake = cscan.backup(scan_path, self.remote())
        print('DirId: {portal_id!s}\n'
              'RemotePath: {remote_path!s}\n'
              'Cake: {latest_cake!s}\n'
              ''.format(**locals()))


    @ca.command('download remote changes for a dir',
                dir='directory where to restore. ',
                cake='content address or portal to restore from')
    def pull(self, cake, dir='.'):
        client = CakeClient()
        self._check_cu_session(dir)
        src = ensure_cakepath(cake)
        cake = cscan.pull(self.remote(), src, dir)
        print('From: {src!s} \nCake: {cake!s}\n'
              .format(**locals()))

    @ca.command('backup and pull. Use dir_id as portal.')
    def sync(self, dir='.'):
        pass

    @ca.command('Create portal',
                portal_type=('Type of portal. Only needed if portal_id '
                             'is not provided. ',
                             portal_from_name, PORTAL_TYPES),
                portal_role=('CakeRole of portal. Only needed if portal_id '
                             'is not provided. ',
                             CakeRole.from_name, list(CakeRole)),
                portal_id=('Portal to be created. If omitted new '
                           'random portal_id will be created .', Cake),
                cake=('Optional. Cake that created portal points to. ',
                      Cake),
                dir=('directory, used to lookup mount session. ')
                )
    def create_portal(self, portal_id=None, portal_role=None,
                      portal_type=None, cake=None, dir='.'):
        self._check_cu_session(dir)
        if portal_id is None:
            portal_id = Cake.new_portal(
                role=portal_role, type=portal_type)
        self.remote().create_portal(portal_id=portal_id,
                                       cake=cake)
        print('Portal: {portal_id!s} \nCake: {cake!s}\n'
                .format(**locals()) )

    @ca.command('Update file in vtree',
                cake_path=('Cake path in VTree portal where file should '
                           'be stored.', CakePath),
                cake=('Cake of the file. Warning is displayed if file '
                      'is not on server.', Cake),
                file=('File to be stored in vtree. If file is not on '
                      'server file will be stored there'),
                dir=('directory, used to lookup mount session. ')
                )
    def update_vtree(self, cake_path, cake=None, file=None, dir=None):
        self._check_cu_session(dir or file or '.')
        if cake is None:
            digest, _, buff = process_stream(
                open(file, 'rb')
            )
            cake = Cake.from_digest_and_inline_data(digest, buff)

        unseen = self.remote().edit_portal_tree(
            files=[(PatchAction.update, cake_path,cake),])
        for cake_to_write in map(Cake.ensure_it, unseen):
            if cake != cake_to_write:
                raise AssertionError('{cake} != {cake_to_write}'
                                     .format(**locals()))
            elif file is None:
                log.warning('Server does not have %s stored.'%cake)
            else:
                fp = open(file, 'rb')
                stored = self.remote().write_content(fp)

        print('CPath: {cake_path!s} \nCake: {cake!s}\n'
                .format(**locals()) )

    @ca.command('Delete path in vtree')
    def delete_in_vtree(self, cake_path, dir='.'):
        self._check_cu_session(dir)
        deleted = self.remote().delete_in_portal_tree(cake_path=cake_path)
        print(('Deleted: ' if deleted else 'Not there: ') + cake_path)

main = ca.main

if __name__ == '__main__':
    main()
