from nose.tools import eq_,ok_
from hashstore.bakery import Cake, SaltedSha, CakeRole
from hashstore.tests import TestSetup, doctest_it


from hashstore.ndb import Dbf
from hashstore.ndb.models import glue, cake_shard
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__,ensure_empty=True)
log = test.log



def test_server():
    #'sqlite:///:memory:'
    pass


def test_glue():
    dbf = Dbf(glue.GlueBase.metadata, test.file_path('test_glue.sqlite3'))
    dbf.ensure_db()
    glue_session = dbf.session()
    shard_dbf = Dbf(cake_shard.CakeShardBase.metadata, test.file_path('test_shard.sqlite3'))
    shard_dbf.ensure_db()
    shard_session = shard_dbf.session()
    joe = glue.User(id=Cake.new_portal(CakeRole.SYNAPSE),
                    email='joe@doe.com',
                    user_state=glue.UserState.invitation,
                    passwd=SaltedSha.from_secret('xyz'))
    cake = Cake.from_bytes(b'a' * 100)
    portal = cake_shard.Portal(id=Cake.new_portal(), latest=cake)
    shard_session.add(portal)
    perm1 = glue.Permission(
        user=joe, cake=portal.id,
        permission_type=glue.PermissionType.Read_,
    )
    perm2 = glue.Permission(
        user=joe, cake=cake,
        permission_type=glue.PermissionType.Read_,
    )
    glue_session.add(
        perm1,perm2
    )
    shard_session.commit()
    glue_session.commit()
    # ok_(False)

def test_models():
    from hashstore.ndb.models import MODELS
    for m in MODELS:
        name = m.__name__.split('.')[-1]
        if hasattr(m,'doctest') and m.doctest:
            doctest_it(m)
        dbf = Dbf(m.Base.metadata,test.file_path('test_models_%s.sqlite3' % name ))
        dbf.ensure_db()
