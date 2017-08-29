from nose.tools import eq_,ok_
from hashstore.bakery.ids import Cake, SaltedSha
from hashstore.tests import TestSetup, doctest_it

from sqlalchemy import Table, MetaData, Column, types, select

from hashstore.ndb import Dbf
from hashstore.ndb.models import glue
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__,ensure_empty=True)
log = test.log



def test_server():
    #'sqlite:///:memory:'
    pass


def test_glue():
    import hashstore.ndb.models.glue as glue
    dbf = Dbf(glue.GlueBase.metadata, test.file_path('test_glue.sqlite3'))
    dbf.ensure_db()
    session = dbf.session()
    joe = glue.User(email='joe@doe.com',
                     user_state=glue.UserState.invitation,
                     passwd=SaltedSha.from_secret('xyz'))
    cake = Cake.from_bytes(b'a' * 100)
    portal = glue.Portal(latest=cake)
    perm1 = glue.Permission(
        user = joe, cake=portal.id,
        permission_type=glue.PermissionType.Read_,
    )
    perm2 = glue.Permission(
        user = joe, cake=cake,
        permission_type=glue.PermissionType.Read_,
    )
    session.add(
        perm1,perm2
    )
    session.commit()
    # ok_(False)

def test_models():
    from hashstore.ndb.models import MODELS
    for m in MODELS:
        name = m.__name__.split('.')[-1]
        if hasattr(m,'doctest') and m.doctest:
            doctest_it(m)
        dbf = Dbf(m.Base.metadata,test.file_path('test_models_%s.sqlite3' % name ))
        dbf.ensure_db()
