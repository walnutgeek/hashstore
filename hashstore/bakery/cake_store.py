from hashstore.bakery.shard_schema import *
from hashstore.bakery.auth_schema import *

from hashstore.bakery.content import *

import hashlib
import os
import shutil
import datetime
import six
from hashstore.local_store import AccessMode
from hashstore.ids import Cake, NamedCAKes, Cake_TYPE, KeyStructure

from hashstore.bakery.content import ContentAddress, is_it_shard
from .backend import LiteBackend
from hashstore.new_db import Dbf
from hashstore.utils import v2s,quict,ensure_directory,ensure_bytes,\
    read_in_chunks



import logging
log = logging.getLogger(__name__)



class CakeStore:
    def __init__(self, root, access_mode=AccessMode.WRITE_SECURE, init=True):
        self.root = root
        self.access_mode = access_mode
        if init:
            self.initialize()


    def initialize(self):
        if hasattr(self, 'backend'):
            return
        self.backend = LiteBackend(self.root)
        self.auth_db = Dbf(auth_meta, os.path.join(self.root,'auth.db'))
        self.auth_db.ensure_db()



    def create_invitation(self, body=None):
        self.initialize()

        rp = self.auth_db.execute(invitation.insert().values(
            active = True,
            invitation_body=body
        ))
        return rp.lastrowid()

    def register(self, remote_uuid, invitation_id, mount_meta=None):
        if invitation is None:
            rc = 0 if self.access_mode != AccessMode.INSECURE else 1
        else:
            rp = self.in_db.execute( invitation.update().where(
                invitation_id = invitation_id,
                active=True
            ).values(
                active=False
            ))
            rc = rp.rowcount()
        if rc == 1:
            mount_session = udk.quick_hash(remote_uuid)
            return self.in_db.resolve_ak('mount', mount_session)
        return None

    def login(self, remote_uuid):
        mount_session = udk.quick_hash(remote_uuid)
        mount = self.in_db.select_one('mount', quict(mount_session=mount_session))
        if mount is not None:
            mount_id = mount['mount_id']
            auth_session = self.in_db.insert('auth_session', quict(mount_id=mount_id, active=True))
            return auth_session['_auth_session_id'], mount_id
        else:
            raise ValueError("authentication error")

    def logout(self, auth_session):
        return self.in_db.update('auth_session', quict(
            auth_session_id = auth_session, _active = False))

    def check_auth_session(self, auth_session):
        if self.access_mode != AccessMode.INSECURE :
            if auth_session is None:
                raise ValueError("auth_session is required")
            with self.auth_db.connect() as conn:
                q = select([auth])\
                    .where( auth.c.active == True &
                            auth.c.session_id == auth_session)
                n = self.auth_db.execute(q).one_or_none()
                if n is None:
                    raise ValueError("authentication error")

    def store_directories(self, directories, mount_hash=None, auth_session = None):
        self.check_auth_session(auth_session)
        unseen_file_hashes = set()
        dirs_stored = set()
        dirs_mismatch = set()
        for dir_hash, dir_contents in six.iteritems(directories):
            dir_hash = udk.UDK.ensure_it(dir_hash)
            dir_contents = udk.UDKBundle.ensure_it(dir_contents)
            dir_content_dump = str(dir_contents)
            lookup = self.lookup(dir_hash)
            if not lookup.found() :
                w = self.writer(auth_session=auth_session)
                w.write(dir_content_dump, done=True)
                lookup = self.lookup(dir_hash)
                if lookup.found():
                    dirs_stored.add(dir_hash)
                else: # pragma: no cover
                    dirs_mismatch.add(dir_hash)
            for file_name in dir_contents:
                file_hash = dir_contents[file_name]
                if not file_hash.named_udk_bundle:
                    lookup = self.lookup(file_hash)
                    if not lookup.found():
                        unseen_file_hashes.add(file_hash)
        if len(dirs_mismatch) > 0: # pragma: no cover
            raise AssertionError('could not store directories: %r' % dirs_mismatch)
        return len(dirs_stored), list(unseen_file_hashes)


    def get_content(self, k, auth_session = None):
        if self.access_mode == AccessMode.ALL_SECURE:
            self.check_auth_session(auth_session)
        return self.lookup(k).stream()

    def delete(self, k, auth_session = None):
        self.check_auth_session(auth_session)
        return self.lookup(k).delete()

    def writer(self, auth_session = None):
        self.check_auth_session(auth_session)
        return ContentWriter(self.backend)
