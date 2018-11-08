from nose.tools import eq_,ok_,with_setup
from hashstore.tests import TestSetup, assert_text
import hashstore.utils.fio as fio
from hashstore.utils import exception_message
from hashstore.utils.smattr import Mold

test = TestSetup(__name__,ensure_empty=True)
log = test.log
fio.ensure_directory(test.dir)

import hashstore.utils.event as e


def test_docs():
    import doctest
    r = doctest.testmod(e)
    ok_(r.attempted > 0, f'There is no doctests in module {e}')
    eq_(r.failed,0)


def test_wiring():
    try:
        class Abc(metaclass=e.ExecutibleMeta):
            pass
        ok_(False)
    except AttributeError :
        ok_(all( s in exception_message() for s in
                  ("Undefined:", "'in_mold'", "'out_mold'")))

    class AbcDef(metaclass=e.ExecutibleMeta):
        class Input:
            a:int
            b:str
            c:bool
        class Output:
            d:int
            e:float
            f:str

    eq_(AbcDef.in_mold.to_json(),
        ['a:Required[int]', 'b:Required[str]', 'c:Required[bool]'])

    eq_(AbcDef.out_mold.to_json(),
        ['d:Required[int]', 'e:Required[float]', 'f:Required[str]'])

    class AbcDef2(metaclass=e.ExecutibleMeta):
        in_mold = Mold(['a:Required[int]', 'b:Required[str]', 'c:Required[bool]'])
        out_mold = Mold(['d:Required[int]', 'e:Required[float]', 'f:Required[str]'])

    ok_(AbcDef.in_mold == AbcDef2.in_mold)
