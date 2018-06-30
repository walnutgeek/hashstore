from nose.tools import eq_,ok_,with_setup

from hashstore.tests import TestSetup
import hashstore.bakery.logic as logic

import hashstore.bakery.tests.logic_test_module as plugin

test = TestSetup(__name__,ensure_empty=True)
log = test.log


# def test_docs():
#     import doctest
#     r = doctest.testmod(logic)
#     ok_(r.attempted > 0, 'There is not doctests in module')
#     eq_(r.failed,0)

# class Dag(logic.Task):
#     v:int
#     b = logic.Task(plugin.fn2)
#     a = logic.Task(plugin.fn, n=b.x, i=v)


def test_json():
    hl = logic.HashLogic.from_module(plugin)
    json = str(hl)
    match = \
        '{"methods": [{' \
        '"in_vars": [{"name": "n", "type": "hashstore.bakery:Cake"}, ' \
                    '{"name": "i", "type": "builtins:int"}], ' \
        '"out_vars": [{"name": "return", "type": "hashstore.bakery:Cake"}], ' \
        '"ref": "hashstore.bakery.tests.logic_test_module:fn"}, ' \
        '{"in_vars": [], ' \
        '"out_vars": [{"name": "name", "type": "builtins:str"}, ' \
                    '{"name": "id", "type": "builtins:int"}, ' \
                    '{"name": "x", "type": "hashstore.bakery:Cake"}], ' \
        '"ref": "hashstore.bakery.tests.logic_test_module:fn2"}], ' \
        '"name": "hashstore.bakery.tests.logic_test_module"}'

    eq_(json, match)
    hl2 = logic.HashLogic(hl.to_json())
    eq_(str(hl2), match)

