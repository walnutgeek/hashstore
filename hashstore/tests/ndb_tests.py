from nose.tools import eq_,ok_
import hashstore.bakery.ids as ids
from hashstore.tests import TestSetup, doctest_it

from sqlalchemy import Table, Integer, MetaData, Column, types, select

from hashstore.ndb import Dbf, IntCast, StringCast
import enum

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_int_enum():
    class X(enum.IntEnum):
        a = 1
        b = 2
        c = 3

    meta = MetaData()
    tbl = Table("mytable", meta,
                Column("id", Integer, primary_key=True,
                       autoincrement=True),
                Column('name', types.String()),
                Column("x", IntCast(X), nullable=True))

    #'sqlite:///:memory:'

    dbf = Dbf(meta,test.file_path('int_enum.sqlite3'))
    ok_(not dbf.exists())
    dbf.ensure_db()
    with dbf.connect() as conn:
        r = conn.execute(tbl.insert().values(name='abc'))

        id1 = r.inserted_primary_key[0]
        log.debug( id1 )
        r = conn.execute(tbl.insert().values(name='xyz',x=None))
        id2 = r.inserted_primary_key[0]
        log.debug( id2 )
    dbf.execute(tbl.update().where(tbl.c.id == id1)
                .values(name='ed', x = X.c))
    fetch = dbf.execute(select([tbl])).fetchall()
    attach = {r.id: r.x for r in fetch}
    eq_(attach[id1], X.c)
    eq_(attach[id2], None)


def test_cake_type():
    meta = MetaData()
    tbl = Table("mytable", meta,
                Column("guid", StringCast(ids.Cake),
                       primary_key=True,
                       default=lambda: ids.Cake.new_guid()),
                Column('name', types.String()),
                Column("attachment", StringCast(ids.Cake), nullable=True))

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



