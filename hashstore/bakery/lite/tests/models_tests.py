from hashstore.bakery import Cake, CakeRole
from hashstore.utils.hashing import SaltedSha
from hashstore.tests import TestSetup, doctest_it


from hashstore.utils.db import Dbf

from hashstore.bakery.lite.client import ClientConfigBase, ScanBase
from hashstore.bakery.lite.node import (
    GlueBase, CakeShardBase, ServerConfigBase, UserState, User, Portal,
    PermissionType, Permission)

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_glue():
    dbf = Dbf(GlueBase.metadata, test.file_path('test_glue.sqlite3'))
    dbf.ensure_db()
    glue_session = dbf.session()
    shard_dbf = Dbf(CakeShardBase.metadata, test.file_path('test_shard.sqlite3'))
    shard_dbf.ensure_db()
    shard_session = shard_dbf.session()
    joe = User(id=Cake.new_portal(CakeRole.SYNAPSE),
                    email='joe@doe.com',
                    user_state=UserState.invitation,
                    passwd=SaltedSha.from_secret('xyz'))
    cake = Cake.from_bytes(b'a' * 100)
    portal = Portal(id=Cake.new_portal(), latest=cake)
    shard_session.add(portal)
    perm1 = Permission(
        user=joe, cake=portal.id,
        permission_type=PermissionType.Read_,
    )
    perm2 = Permission(
        user=joe, cake=cake,
        permission_type=PermissionType.Read_,
    )
    glue_session.add(
        perm1,perm2
    )
    shard_session.commit()
    glue_session.commit()
    # ok_(False)

def test_models():
    for b in (ClientConfigBase, ScanBase, GlueBase, CakeShardBase,
              ServerConfigBase):
        dbf = Dbf(b.metadata,test.file_path(
            f'test_models_{b.__name__}.sqlite3'))
        dbf.ensure_db()
