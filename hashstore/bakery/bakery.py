import os
from hashstore.bakery.backend import LiteBackend
from hashstore.bakery.ids import Cake, NamedCAKes
from hashstore.ndb import Dbf
from hashstore.utils import ensure_dict

from hashstore.ndb.models.server import ServerKey, Base as ServerBase
from hashstore.ndb.models.glue import PortalType, Portal, \
    PortalHistory, Base as GlueBase

import logging
log = logging.getLogger(__name__)


class CakeStore:
    def __init__(self, store_dir):
        self.store_dir = store_dir
        self._backend = None
        self.server_db = Dbf(
            ServerBase.metadata,
            os.path.join(self.store_dir, 'server.db')
        )
        self.glue_db = Dbf(
            GlueBase.metadata,
            os.path.join(self.store_dir, 'glue.db')
        )

    def backend(self):
        if self._backend is None:
            self._backend = LiteBackend(
                os.path.join(self.store_dir, 'backend')
            )
        return self._backend

    def initdb(self, external_ip, port):
        if not os.path.exists(self.store_dir):
            os.makedirs(self.store_dir)
        self.server_db.ensure_db()
        os.chmod(self.server_db.path, 0o600)
        self.glue_db.ensure_db()
        self.backend()
        with self.server_db.session_scope() as session:
            skey = session.query(ServerKey).one_or_none()
            if skey is None:
                skey = ServerKey()
            skey.port = port
            skey.external_ip = external_ip
            session.merge(skey)


    def store_directories(self, directories):
        directories = ensure_dict( directories, Cake, NamedCAKes)
        unseen_file_hashes = set()
        dirs_stored = set()
        dirs_mismatch_input_cake = set()
        for dir_cake in directories:
            dir_contents =directories[dir_cake]
            lookup = self.backend().lookup(dir_cake)
            if not lookup.found() :
                w = self.backend().writer()
                w.write(dir_contents.in_bytes(), done=True)
                lookup = self.backend().lookup(dir_cake)
                if lookup.found():
                    dirs_stored.add(dir_cake)
                else: # pragma: no cover
                    dirs_mismatch_input_cake.add(dir_cake)
            for file_name in dir_contents:
                file_cake = dir_contents[file_name]
                if not(file_cake.has_data()) and \
                        file_cake not in  directories:
                    lookup = self.backend().lookup(file_cake)
                    if not lookup.found():
                        unseen_file_hashes.add(file_cake)
        if len(dirs_mismatch_input_cake) > 0: # pragma: no cover
            raise AssertionError('could not store directories: %r' % dirs_mismatch_input_cake)
        return len(dirs_stored), list(unseen_file_hashes)

    def get_content(self, k):
        return self.backend().lookup(k).stream()

    def writer(self):
        return self.backend().writer()

    def write_content(self, fp):
        w = self.writer()
        while True:
            buf = fp.read(65355)
            if len(buf) == 0:
                break
            w.write(buf)
        return w.done()

    def create_portal(self,portal_id, cake,
                      portal_type = PortalType.content):
        portal_id = Cake.ensure_it(portal_id)
        cake = Cake.ensure_it(cake)
        with self.glue_db.session_scope() as session:
            portal = session.query(Portal)\
                .filter(Portal.id == portal_id).one_or_none()
            if portal is not None and portal.portal_type != portal_type:
                raise ValueError('cannot change type. portal:%s %r->%r' %
                                 (portal_id, portal.portal_type, portal_type))
            session.merge(Portal(id=portal_id, latest=cake,
                   portal_type=portal_type))
            session.add(PortalHistory(portal_id = portal_id, cake=cake))



