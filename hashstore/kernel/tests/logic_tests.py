from hs_build_tools.nose import eq_,ok_

from hashstore.tests import TestSetup
import hashstore.kernel.logic as logic

import hashstore.kernel.tests.logic_test_module as plugin

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
            '{"in_mold": [' \
                '"n:Required[hashstore.kernel.bakery:Cake]", ' \
                '"i:Required[int]"], ' \
            '"out_mold": [' \
                '"_:Required[hashstore.kernel.bakery:Cake]"], ' \
            '"ref": "hashstore.kernel.tests.logic_test_module:fn"}, ' \
            '{"in_mold": [], ' \
            '"out_mold": [' \
                '"name:Required[str]", ' \
                '"id:Required[int]", ' \
                '"x:Required[hashstore.kernel.bakery:Cake]"], ' \
            '"ref": "hashstore.kernel.tests.logic_test_module:fn2"}, ' \
            '{"in_mold": [' \
                '"n:Required[hashstore.kernel.bakery:Cake]", ' \
                '"i:Required[int]=5"], ' \
            '"out_mold": [' \
                '"_:Required[hashstore.kernel.bakery:Cake]"], ' \
            '"ref": "hashstore.kernel.tests.logic_test_module:fn3"}], ' \
        '"name": "hashstore.kernel.tests.logic_test_module"}' \

    eq_(json, match)
    hl2 = logic.HashLogic(hl.to_json())
    eq_(str(hl2), match)

