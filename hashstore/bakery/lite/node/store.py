import os

from hashstore.bakery import CakeRole
from hashstore.bakery.lite import dal
from hashstore.bakery.lite.node import (
    ServerConfigBase, GlueBase,  CakeShardBase, User, UserType,
    UserState, Permission, Portal, ServerKey, PermissionType as PT)
from hashstore.bakery.lite.node.blobs import BlobStore
from hashstore.utils.db import Dbf
from hashstore.kernel.hashing import shard_name_int, SaltedSha


class CakeStore:
    def __init__(self, store_dir):
        self.store_dir = store_dir
        self._blob_store = None
        self.srvcfg_db = Dbf(
            ServerConfigBase.metadata,
            os.path.join(self.store_dir, 'server.db')
        )
        self.glue_db = Dbf(
            GlueBase.metadata,
            os.path.join(self.store_dir, 'glue.db')
        )
        self.max_shards = None
        self.shards_db = None

    def cake_shard_db(self, cake):
        if self.max_shards is None:
            self.max_shards = self.server_config().num_cake_shards
            self.shards_db = [Dbf(
                CakeShardBase.metadata,
                os.path.join(self.store_dir,
                             'shard_' + shard_name_int(i) + '.db')
            ) for i in range(self.max_shards)]
        db = self.shards_db[cake.shard_num(self.max_shards)]
        if not(db.exists()):
            db.ensure_db()
        return db

    def blob_store(self):
        if self._blob_store is None:
            self._blob_store = BlobStore(
                os.path.join(self.store_dir, 'backend')
            )
        return self._blob_store

    def initdb(self, external_ip, port, num_cake_shards=10):
        if not os.path.exists(self.store_dir):
            os.makedirs(self.store_dir)
        self.srvcfg_db.ensure_db()
        os.chmod(self.srvcfg_db.path, 0o600)
        self.glue_db.ensure_db()
        self.blob_store()
        with self.srvcfg_db.session_scope() as srv_session:
            skey = srv_session.query(ServerKey).one_or_none()
            if skey is None:
                skey = ServerKey()
                skey.num_cake_shards = num_cake_shards
            elif skey.num_cake_shards != num_cake_shards:
                raise ValueError(
                    f'reshard required: '
                    f'{skey.num_cake_shards} != {num_cake_shards}')
            skey.port = port
            skey.external_ip = external_ip
            srv_session.merge(skey)
        with self.glue_db.session_scope() as glue_session:
            make_system_user = lambda n: User(
                email=f'{n}@' ,
                user_type=UserType[n],
                user_state=UserState.active,
                passwd=SaltedSha.from_secret('*'),
                full_name=f'{n} user'
            )
            #ensure guest
            guest = dal.query_users_by_type(
                glue_session,UserType.guest).one_or_none()
            if guest is None:
                guest = make_system_user('guest')
                glue_session.add(guest)
                glue_session.flush()
                index_portal = guest.id.transform_portal(
                    role=CakeRole.NEURON)
                with self.cake_shard_db(index_portal).session_scope() as \
                        shard_session:
                    shard_session.add(Portal(id=index_portal))

            #ensure system
            system = dal.query_users_by_type(
                glue_session, UserType.system).one_or_none()
            if system is None:
                system = make_system_user('system')
                glue_session.add(system)
                glue_session.add(
                    Permission(permission_type=PT.Admin,
                               user=system))


    def server_config(self):
        with self.srvcfg_db.session_scope() as session:
            return session.query(ServerKey).one()

