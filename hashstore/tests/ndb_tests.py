from nose.tools import eq_,ok_
import hashstore.ids as ids
import six
from hashstore.tests import TestSetup, doctest_it

from sqlalchemy import Table, MetaData, Column, types, \
    create_engine, select

from hashstore.ndb import Dbf

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_Alchemy():
    meta = MetaData()
    tbl = Table("mytable", meta,
                Column("guid", ids.Cake_TYPE(),
                       primary_key=True,
                       default=lambda: ids.Cake.new_guid()),
                Column('name', types.String()),
                Column("attachment", ids.Cake_TYPE(), nullable=True))

    #'sqlite:///:memory:'

    dbf = Dbf(meta,test.file_path('test.sqlite3'))
    ok_(not dbf.exists())
    dbf.ensure_db()
    with dbf.connect() as conn:
        r = conn.execute(tbl.insert().values(name='abc'))
        guid1 = r.last_inserted_params()['guid']
        log.debug( guid1 )
        r = conn.execute(tbl.insert().values(name='xyz',attachment=None))
        guid2 = r.last_inserted_params()['guid']
        log.debug( guid2 )
    dbf.execute(tbl.update().where(tbl.c.guid == guid1)
                .values(name='ed', attachment = ids.Cake.from_bytes(b'asdf')))
    fetch = dbf.execute(select([tbl])).fetchall()
    attach = {r.guid: r.attachment for r in fetch}
    eq_(attach[guid1], ids.Cake('01ME5Mi'))
    eq_(attach[guid2], None)


def test_models():
    from hashstore.ndb.models import MODELS
    for m in MODELS:
        name = m.__name__.split('.')[-1]
        dbf = Dbf(m.Base.metadata,test.file_path('%s_model.sqlite3' % name ))
        dbf.ensure_db()

