from datetime import datetime
from typing import Optional, List, Dict, Tuple

from nose.tools import eq_,ok_,with_setup
from hashstore.tests import TestSetup, assert_text
import hashstore.utils as u
from hashstore.utils.fio import ensure_directory

from hashstore.utils.smattr import (
    SmAttr, JsonWrap, MoldedTable, typing_factory,
    extract_molds_from_function)

test = TestSetup(__name__,ensure_empty=True)

log = test.log


ensure_directory(test.dir)


def test_docs():
    import doctest
    import hashstore.utils.smattr as smattr
    r = doctest.testmod(smattr)
    ok_(r.attempted > 0, f'There is not doctests in module')
    eq_(r.failed,0)


class A(SmAttr):
    """ An example of SmAttr usage

    Attributes:
       i: integer
       s: string with
          default
       d: optional datetime

       attribute contributed
    """
    i:int
    s:str = 'xyz'
    d:Optional[datetime]
    z:List[datetime]
    y:Dict[str,str]


def pack_wolves(i:int, s:str='xyz')-> Tuple[int,str]:
    """ Greeting protocol

    Args:
       s: string with
          default

    Returns:
        num_of_wolves: Pack size
        pack_name: Name of the pack
    """
    return i, s

def test_extract_molds_from_function():
    in_mold, out_mold, dst = extract_molds_from_function(pack_wolves)
    eq_(str(out_mold),'["num_of_wolves:Required[int]", "pack_name:Required[str]"]')
    assert_text(dst.doc(),""" Greeting protocol

    Args:
        s: Required[str] string with default. Default is: 'xyz'.
        i: Required[int]

    Returns:
        num_of_wolves: Required[int] Pack size
        pack_name: Required[str] Name of the pack
    
    """)

def test_docstring():
    assert_text(A.__doc__, """
     An example of SmAttr usage

    Attributes:
        i: Required[int] integer
        s: Required[str] string with default. Default is: 'xyz'.
        d: Optional[datetime:datetime] optional datetime
        z: List[datetime:datetime]
        y: Dict[str,str]

       attribute contributed
    """)

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
