from datetime import datetime
from typing import Optional, List, Dict

from nose.tools import eq_,ok_,with_setup
from hashstore.tests import TestSetup, assert_text
import hashstore.utils as u

from hashstore.utils.smattr import (
    SmAttr, JsonWrap, MoldedTable, typing_factory)

test = TestSetup(__name__,ensure_empty=True)

log = test.log


u.ensure_directory(test.dir)


def test_docs():
    import doctest
    import hashstore.utils.smattr as smattr
    r = doctest.testmod(smattr)
    ok_(r.attempted > 0, f'There is not doctests in module')
    eq_(r.failed,0)


class A(SmAttr):
    i:int
    s:str = 'xyz'
    d:Optional[datetime]
    z:List[datetime]
    y:Dict[str,str]

def test_gref_with_molded_table():
    ATable = MoldedTable[A]
    t = ATable()
    eq_(str(t), '#{"columns": ["i", "s", "d", "z", "y"]}\n')
    tn = 'hashstore.utils.smattr:MoldedTable'
    eq_(str(u.GlobalRef(MoldedTable)), tn)
    aref = str(u.GlobalRef(MoldedTable[A]))
    eq_(aref, f'{tn}[hashstore.tests.smattr_tests:A]')
    ok_(ATable is MoldedTable[A])
    a_table = u.GlobalRef(aref).get_instance()
    ok_(ATable is a_table)

def test_typing_with_template():
    s = f'List[{u.GlobalRef(MoldedTable[A])}]'
    tt = typing_factory(s)
    eq_(s, str(typing_factory(str(tt))))
    ok_(tt.val_cref.cls is MoldedTable[A])

class Abc(SmAttr):
    name:str
    val:int


def test_wrap():
    abc = Abc({'name': 'n', 'val': 555})
    s = str(abc)
    def do_check(w):
        eq_(str(w.unwrap()), s)
        eq_(str(w),
            '{"classRef": "hashstore.tests.smattr_tests:Abc", '
            '"json": {"name": "n", "val": 555}}')
        eq_(str(JsonWrap(w.to_json()).unwrap()), s)
    do_check(JsonWrap({"classRef": u.GlobalRef(Abc),
                       "json":{'name':'n', 'val': 555}}))
    do_check(JsonWrap.wrap(abc))
    try:
        JsonWrap.wrap(5)
    except AttributeError:
        eq_('Not jsonable: 5', u.exception_message())
