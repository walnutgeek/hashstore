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
        '{"methods": [' \
            '{"in_mold": {"__attrs__": [' \
                '"n:Required[hashstore.bakery:Cake]", ' \
                '"i:Required[builtins:int]"]}, ' \
            '"out_mold": {"__attrs__": [' \
                '"return:Required[hashstore.bakery:Cake]"]}, ' \
            '"ref": "hashstore.bakery.tests.logic_test_module:fn"}, ' \
            '{"in_mold": {"__attrs__": []}, ' \
            '"out_mold": {"__attrs__": [' \
                '"name:Required[builtins:str]", ' \
                '"id:Required[builtins:int]", ' \
                '"x:Required[hashstore.bakery:Cake]"]}, ' \
            '"ref": "hashstore.bakery.tests.logic_test_module:fn2"}, ' \
            '{"in_mold": {"__attrs__": [' \
                '"n:Required[hashstore.bakery:Cake]", ' \
                '"i:Required[builtins:int]=5"]}, ' \
            '"out_mold": {"__attrs__": [' \
                '"return:Required[hashstore.bakery:Cake]"]}, ' \
            '"ref": "hashstore.bakery.tests.logic_test_module:fn3"}], ' \
        '"name": "hashstore.bakery.tests.logic_test_module"}' \

    eq_(json, match)
    hl2 = logic.HashLogic(hl.to_json())
    eq_(str(hl2), match)

