import os
import six
import shutil
from hashstore.db import _session, Session, DbFile
import logging
from .. import content
from .. import utils
from nose.tools import eq_,ok_,with_setup

test_dir = os.path.join(os.path.abspath("test-out"),__name__)
if os.path.isdir(test_dir):
    shutil.rmtree(test_dir)

log = logging.getLogger(__name__)

class TestDB(DbFile):
    def datamodel(self):
        '''
        table:abc
          abc_id PK
          parent_id FK(abc) null
          name TEXT AK
        table:ubc
          ubc_id UUID1 PK
          parent_id FK(ubc) null
          name TEXT AK
        table:content
          content_id UUID1 PK
          parent_id FK(content) AK(content_ak) null
          key SORTED_DICT AK(content_ak)
          content_meta JSON null
          content BIG null
          update_dt UPDATE_DT
          create_dt INSERT_DT
        table:host
          host_id UUID1 PK
          host_name TEXT AK
          host_meta JSON BIG
        table:mount
          mount_id UUID4 PK
          content_id FK(content)
          host_id FK(host)
          mount_meta JSON
        '''
        return self.datamodel.__doc__

def test_db2():
    c = TestDB(os.path.join(test_dir,'abc.sqlite3'))
    eq_('TEXT',c.schema.tables['host'].columns['host_meta'].type)
    eq_('BLOB',c.schema.tables['content'].columns['content'].type)
    eq_(['host_id', 'host_name'],list(c.schema.tables['host'].all_column_names()))
    eq_(['host_meta'],list(c.schema.tables['host'].all_column_names(include_only_role='BIG')))
    eq_(['content_id', 'parent_id', 'key', 'content_meta', 'update_dt', 'create_dt'],list(c.schema.tables['content'].all_column_names()))
    eq_(['mount_id', 'content_id', 'host_id', 'mount_meta'],list(c.schema.tables['mount'].all_column_names()))
    eq_(['content_id', 'parent_id', 'key', 'content_meta', 'content', 'update_dt', 'create_dt'],list(c.schema.tables['content'].all_column_names(exclude_role=None)))
    eq_(['mount_id', 'content_id', 'host_id', 'mount_meta'],list(c.schema.tables['mount'].all_column_names(exclude_role=None)))
    c.ensure_db()
    c.compare_tables()
    c = TestDB(os.path.join(test_dir, 'abc.sqlite3')).ensure_db()
    eq_('TEXT',c.schema.tables['host'].columns['host_meta'].type)
    c2 = TestDB(os.path.join(test_dir, 'abc2.sqlite3')).ensure_db()
    c3 = TestDB(os.path.join(test_dir, 'abc3.sqlite3')).create_db(lambda dbf,session:None)
    csame = TestDB(os.path.join(test_dir, 'abc.sqlite3'))
    eq_({'name': 'a', '_abc_id': 1},c.insert('abc',{'name':'a'}))
    d=c.insert('ubc', {'name': 'a'})
    did = d['_ubc_id']
    del d['_ubc_id']
    import uuid
    eq_(type(did),uuid.UUID)
    eq_(d, {'name': 'a'})
    from_db = c.select_one('ubc', {'ubc_id': did})
    ok_(from_db is not None)
    eq_(type(from_db['ubc_id']),uuid.UUID)
    del from_db['ubc_id']
    eq_({'parent_id': None, 'name': u'a'},from_db)
    eq_(None,c.select_one('abc', {'abc_id': 2}))
    eq_(2, csame.resolve_ak('abc','b'))
    eq_({'parent_id': None, 'name': u'b', 'abc_id': 2}, c.select_one('abc', {'abc_id': 2}))
    eq_(2, c.resolve_ak('abc', 'b'))
    eq_(1, c.update('abc',{'abc_id':2,'_parent_id':1}))
    eq_(1, c.delete('abc', {'name': 'b'}))
    eq_(0, csame.delete('abc', {'name': 'b'}))
    eq_(2, c.store('abc',utils.quict(name='c',_parent_id=1)))
    eq_(2, c.store('abc', utils.quict(name='c', _parent_id=1)))
    try:
        c.store('abc', utils.quict(abc_id = 1, name='c', _parent_id=1))
        ok_(False)
    except ValueError as e:
        eq_("did not update any thing even pkey was provided. where: name=:name and abc_id=:abc_id: {'_parent_id': 1, 'name': 'c', 'abc_id': 1}",e.message)
    cont_id = c.store('content',{'key':{'b':5, 'a':3}, '_content_meta': ['x','a','z'] })
    eq_({'b':5, 'a':3},c.select_one('content',{'content_id':cont_id})['key'])
    eq_(cont_id, c.store('content',{'key':{'a':3, 'b':5}, '_content_meta': ['x','a','z'] }))
    v = {'a': 3, 'b': 5}
    mount_id = c.insert('mount', {'_mount_meta': v })['_mount_id']
    eq_(v , c.select_one('mount',{'mount_id' : mount_id})['mount_meta'])

    # ok_(False)
