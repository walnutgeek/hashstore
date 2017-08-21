import os

import hashstore.ndb.models.server
import hashstore.ndb.models.glue
from hashstore.utils.args import Opt, Switch, CliArgs
from hashstore.ndb import Dbf
from hashstore.bakery.backend import LiteBackend
import logging

ACTIONS = ('view', 'add', 'remove')


perm_names = ', '.join(p.name for p in
                       hashstore.ndb.models.glue.PermissionType)

cli_args = CliArgs('hsd - hashstore server', {
    '':[
        Switch('debug', 'set logging level to DEBUG. default is INFO'),
    ],
    '*': [
        Opt('dir', 'a directory where hashstore data resides. ', '.')
    ],
    'initdb -  initialize storage and set host specific parameters': [
        Opt('port', 'a port to listen. ', 7532, int),
        Opt('external_ip', 'external ip of server.'),
    ],
    'security - maintain user and acl settings': [
        Opt('user', 'email address of user'),
        Opt('acl',
            'should be in form <Permission>:[<Cake>]. Permissions '
            'are: %s. Permission names that ends with "_" require '
            '`Cake` that points to  portal or data' % (perm_names,)),
        Opt('action', choices=ACTIONS),
    ],
    'start - start server': [],
    'stop - stop server': []
})


class Server:
    def __init__(self,store_dir):
        self.store_dir = store_dir
        self.server_db = Dbf(
            hashstore.ndb.models.server,
            os.path.join(store_dir, 'server.db')
        )
        self.glue_db = Dbf(
            hashstore.ndb.models.glue,
            os.path.join(store_dir, 'glue.db')
        )
        self._backend = None


    def backend(self):
        if self._backend is None:
            self._backend = LiteBackend(
                os.path.join(self.store_dir, 'backend')
            )
        return self._backend

    def initdb(self, args):
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
        skey.port = args.port
        skey.external_ip = args.external_ip
        session.merge(skey)
        session.commit()

    def security(self, args):
        print(args)

    def start(self, args):
        print(args)

    def start(self, args):
        print(args)


def main():
    args = cli_args.parse_args()
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level)
    server = Server(args.dir)
    getattr(server,args.command)(args)

if __name__ == '__main__':
    main()