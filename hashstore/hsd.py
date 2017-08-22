import os

import hashstore.ndb.models.server
import hashstore.ndb.models.glue
from hashstore.utils.args import Switch, CommandArgs
from hashstore.ndb import Dbf
from hashstore.bakery.backend import LiteBackend
import logging

perm_names = ', '.join(p.name for p in
                       hashstore.ndb.models.glue.PermissionType)

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
        self.store_dir = store_dir
        self.server_db = Dbf(
            hashstore.ndb.models.server,
            os.path.join(self.store_dir, 'server.db')
        )
        self.glue_db = Dbf(
            hashstore.ndb.models.glue,
            os.path.join(self.store_dir, 'glue.db')
        )
        self._backend = None

    def backend(self):
        if self._backend is None:
            self._backend = LiteBackend(
                os.path.join(self.store_dir, 'backend')
            )
        return self._backend

    @ca.command('initialize storage and set host specific parameters',
                port=('port to listen. ',int),
                external_ip='external IP of server. ')
    def initdb(self, external_ip=None, port=7532):
        if not os.path.exists(self.store_dir):
            os.makedirs(self.store_dir)
        self.server_db.ensure_db()
        os.chmod(self.server_db.path, 0o600)
        self.glue_db.ensure_db()
        self.backend()
        session = self.server_db.session()
        ServerKey = hashstore.ndb.models.server.ServerKey
        skey = session.query(ServerKey).one_or_none()
        if skey is None:
            skey = ServerKey()
        skey.port = port
        skey.external_ip = external_ip
        session.merge(skey)
        session.commit()

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


    @ca.command('start server')
    def start(self):
        pass

    @ca.command('stop server')
    def stop(self):
        pass


if __name__ == '__main__':
    ca.main()