from hashstore.bakery.lite.node.access import (
    PrivilegedAccess, StoreContext)
from hashstore.bakery.cake_server import CakeServer
from hashstore.bakery.lite.node import PermissionType, Acl
from hashstore.bakery.lite.node.store import CakeStore
from hashstore.utils import print_pad
from hashstore.utils.args import Switch, CommandArgs
from hashstore.kernel.hashing import SaltedSha
from hashstore.bakery.cake_scan import pull, backup, ScanPath
from hashstore.kernel.bakery import ensure_cakepath
import getpass

import logging

perm_names = ', '.join(p.name for p in PermissionType)

ca = CommandArgs()
USER='email or guid of user'


@ca.app('hashstore server subcomands')
class DaemonApp():

    @ca.command(
        debug=('set logging level to DEBUG. default is INFO', Switch),
        store_dir='a directory where hashstore data resides. '
    )
    def __init__(self, store_dir='.', debug=False):
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level)
        if debug:
            for l in ('sqlalchemy.engine','sqlalchemy.orm' ):
                logging.getLogger(l).setLevel(logging.INFO)
        self.store = CakeStore(store_dir)


    @ca.command('initialize storage and set host specific parameters',
                port=('port to listen. ',int),
                external_ip='external IP of server. ')
    def initdb(self, external_ip=None, port=7532):
        self.store.initdb(external_ip, port)

    @ca.command(email='email of user')
    def add_user(self, email, password=None, full_name=None):
        if password is None: # pragma: no cover
            password = SaltedSha.from_secret(getpass.getpass())
            retype = getpass.getpass('Retype password:')
            if not password.check_secret(retype):
                raise ValueError('Passwords does not match')
        else:
            password = SaltedSha(password)
        with StoreContext(self.store) as ctx:
            actions = PrivilegedAccess.system_access(ctx)
            actions.add_user(email,password,
                            full_name=full_name)

    @ca.command(user=USER)
    def remove_user(self, user):
        with StoreContext(self.store) as ctx:
            actions = PrivilegedAccess.system_access(ctx)
            actions.remove_user(user)

    @ca.command('Manage ACL',
                user=USER,
                acl='should be in form <Permission>[:<Cake>](+|-). '
                     'Permissions are: %s. Permission names that ends '
                     'with "_" require  `Cake` that points to  portal '
                     'or data.' % (perm_names,))
    def acl(self, user, acl=None):
        with StoreContext(self.store) as ctx:
            actions = PrivilegedAccess.system_access(ctx)
            if acl is not None:
                action = acl[-1]
                acl = Acl(acl[:-1])
            if acl is None or action == '+':
                user,permissions = actions.add_acl(user,acl)
            elif action == '-':
                user,permissions = actions.remove_acl(user,acl)
            else:
                raise AssertionError('unknown action: %s' % action)
            print("User: %s" % user.email)
            print("User.id: %s" % user.id)
            print('')
            print_pad(permissions, ('permission_type', 'cake'), getattr)


    @ca.command('Backup dir', dir='directory to be stored. ')
    def backup(self, dir):
        with StoreContext(self.store) as ctx:
            actions = PrivilegedAccess.system_access(ctx)
            scan_path = ScanPath(dir)
            print('DirId: %s\nCake:  %s' % backup(scan_path, actions))

    @ca.command('Restore dir',
                dir='destination directory.',
                cake='content cake or portal or cake_path' )
    def pull(self, cake, dir):
        with StoreContext(self.store) as ctx:
            actions = PrivilegedAccess.system_access(ctx)
            pull(actions, ensure_cakepath(cake), dir)

    @ca.command('start server')
    def start(self):
        server = CakeServer(self.store)
        server.shutdown(wait_until_down=True)
        server.run_server()

    @ca.command('stop server')
    def stop(self):
        server = CakeServer(self.store)
        server.shutdown(wait_until_down=False)


main = ca.main

