from hs_build_tools.nose import eq_,ok_
import hashstore.kernel.bakery as ids
from hashstore.tests import TestSetup

from sqlalchemy import Table, Integer, MetaData, Column, types, select

from hashstore.utils.db import Dbf, IntCast, StringCast
import enum

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__, ensure_empty=True)
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
                       default=lambda: ids.Cake.new_portal()),
                Column('name', types.String()),
                Column("attachment", StringCast(ids.Cake), nullable=True))
    tbl2 = Table("mytable2", meta,
                Column("guid", StringCast(ids.Cake),
                       primary_key=True,
                       default=lambda: ids.Cake.new_portal()),
                Column('name', types.String()),
                Column("attachment", StringCast(ids.Cake), nullable=True))

    #'sqlite:///:memory:'

    dbf = Dbf(meta,test.file_path('test.sqlite3'))

    def run_scenario(dbf, tbl):
        with dbf.connect() as conn:
            r = conn.execute(tbl.insert().values(name='abc'))
            guid1 = r.last_inserted_params()['guid']
            log.debug(guid1)
            r = conn.execute(
                tbl.insert().values(name='xyz', attachment=None))
            guid2 = r.last_inserted_params()['guid']
            log.debug(guid2)
        dbf.execute(tbl.update().where(tbl.c.guid == guid1)
                    .values(name='ed',
                            attachment=ids.Cake.from_bytes(b'asdf')))
        fetch = dbf.execute(select([tbl])).fetchall()
        attach = {r.guid: r.attachment for r in fetch}
        return attach, guid1, guid2

    ok_(not dbf.exists())
    dbf.ensure_db()
    attach, guid1, guid2 = run_scenario(dbf, tbl)
    eq_(attach[guid1], ids.Cake('01ME5Mi'))
    eq_(attach[guid2], None)
    attach, guid1, guid2 = run_scenario(dbf, tbl2)
    eq_(attach[guid1], ids.Cake('01ME5Mi'))
    eq_(attach[guid2], None)
    tbl.drop(dbf.engine())
    eq_(dbf.engine().table_names(), ['mytable2'])
    dbf = Dbf(meta,test.file_path('test.sqlite3'))
    eq_(dbf.engine().table_names(), ['mytable2'])
    dbf.ensure_db()
    eq_(dbf.engine().table_names(), ['mytable', 'mytable2'])





