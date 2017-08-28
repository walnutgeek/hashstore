import os
from hashstore.bakery.bakery import CakeStore
from hashstore.ndb.models.glue import PermissionType
from hashstore.utils.args import Switch, CommandArgs
from hashstore.bakery.cake_scan import DirScan,backup
import logging

perm_names = ', '.join(p.name for p in PermissionType)

ca = CommandArgs()

USER='email or guid of user'
@ca.app('hsd - hashstore server')
class DaemonApp():

    @ca.command(
        debug=('set logging level to DEBUG. default is INFO', Switch),
        store_dir='a directory where hashstore data resides. '
    )
    def __init__(self, store_dir='.', debug=False):
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(level=level)
        self.store = CakeStore(store_dir)


    @ca.command('initialize storage and set host specific parameters',
                port=('port to listen. ',int),
                external_ip='external IP of server. ')
    def initdb(self, external_ip=None, port=7532):
        self.store.initdb(external_ip, port)

    @ca.command(user='email of user')
    def add_user(self, user, password):
        pass

    @ca.command(user=USER)
    def remove_user(self, user):
        pass

    @ca.command('Manage ACL',
                user=USER,
                acl='should be in form <Permission>[:<Cake>](+|-). '
                     'Permissions are: %s. Permission names that ends '
                     'with "_" require  `Cake` that points to  portal '
                     'or data.' % (perm_names,))
    def acl(self, user, acl):
        pass

    @ca.command('Backup dir',
                dir='directory to be stored. ')
    def backup(self, dir):
        print(backup(dir,self.store))


    @ca.command('start server')
    def start(self):
        pass

    @ca.command('stop server')
    def stop(self):
        pass


main = ca.main

if __name__ == '__main__':
    main()
