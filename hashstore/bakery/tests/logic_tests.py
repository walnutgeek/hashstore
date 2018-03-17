import attr
from nose.tools import eq_,ok_,with_setup
from six import text_type

from hashstore.utils import to_json, from_json
from hashstore.tests import TestSetup
import hashstore.bakery.logic as logic
from hashstore.utils import (
    EnsureIt, Stringable, StrKeyMixin,
    type_optional as optional,
    type_required as required,
    type_list_of as list_of,
    type_dict_of as dict_of)


test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_docs():
    import doctest
    r = doctest.testmod(logic)
    ok_(r.attempted > 0, 'There is not doctests in module')
    eq_(r.failed,0)

def test_json():
    hl = logic.HashLogic("bakery")
    m1 = logic.Method('test')
    hl.methods.append(m1)
    json = to_json(hl)
    match = \
        '{"dags": [], "files": {}, ' \
        '"methods": [{"applies_on": null, "in_vars": [], ' \
        '"name": "test", "out_vars": []}], ' \
        '"name": "bakery", "types": []}'
    eq_(json, match)
    hl2 = from_json(logic.HashLogic, json)
    eq_(to_json(hl2), match)

@attr.s
class Abc(object):
    name = attr.ib(**required(text_type))
    val = attr.ib(**required(int))

def test_implementation():
    impl = logic.Implementation(logic.GlobalRef(Abc),{'name':'n', 'val': 555})
    eq_(impl.create(), Abc('n',555))
    eq_(to_json(impl),
        '{"classRef": "hashstore.bakery.tests.logic_tests:Abc", '
        '"config": {"name": "n", "val": 555}}')
    eq_(from_json(logic.Implementation, to_json(impl)).create(), Abc('n',555))