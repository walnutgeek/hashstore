#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nose.tools import eq_,ok_
import hashstore.bakery as bakery
from io import BytesIO

from hashstore.kernel import utf8_reader
from hashstore.tests import TestSetup, doctest_it

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_docs():
    doctest_it(bakery)

def test_PatchAction():
    eq_(bakery.PatchAction.update, bakery.PatchAction['update'])
    eq_(bakery.PatchAction.delete, bakery.PatchAction['delete'])
    eq_(bakery.PatchAction.delete, bakery.PatchAction.ensure_it('delete'))
    eq_(bakery.PatchAction.update, bakery.PatchAction.ensure_it_or_none('update'))
    ok_(bakery.PatchAction.ensure_it_or_none(None) is None)
    eq_(str(bakery.PatchAction.update), 'update')


def test_CAKe():
    def do_test(c, s, d=None):
        u1 = bakery.Cake.from_bytes(c)
        eq_(s, str(u1))
        u1n = bakery.Cake(str(u1))
        eq_(u1.digest(), u1n.digest())
        eq_(u1, u1n)
        if d is None:
            ok_(not(u1.has_data()))
        else:
            ok_(u1.has_data())
            eq_(c,u1.data())

    do_test(b'', '0', True)
    do_test(b'a' * 1, '01z', True)
    do_test(b'a' * 2, '06u5', True)
    do_test(b'a' * 3, '0qMed', True)
    do_test(b'a' * 32, '0n5He1k77fjNxZNzBxGpha2giODrkmwQfOg6WorIJ4m5',
            True)
    do_test(b'a' * 33, '2sZ85uTW6KyDdVWxpDMRsnsHvDQD9kPdLy1FvVWyWK9Q')
    do_test(b'a' * 46, '2lEWHXV2XeYyZnKNyQyGPt4poJhV7VeYCfeszHnLyFtx')

    b = bakery
    d = b.Cake.new_portal(role=b.CakeRole.NEURON,
                          type=b.CakeType.DMOUNT)
    x = b.Cake.new_portal(role=b.CakeRole.NEURON,
                          type=b.CakeType.DMOUNT)
    z = b.Cake(str(d))
    ok_(z == d)
    eq_(z != d, False)
    ok_(z != x)
    ok_(d != x)
    ok_(z.header.type == d.header.type)
    ok_(str(z) == str(d))


def test_Bundle():
    inline_udk = '01aMUQDApalaaYbXFjBVMMvyCAMfSPcTojI0745igi'
    b1 = bakery.CakeRack()
    eq_(b1.content(),'[[], []]')
    u1 = b1.cake()
    u0 = u1
    file_path = test.file_path('content.json')
    with open(file_path, 'w') as w:
        w.write(b1.content())
    b2 = bakery.CakeRack().parse(b1.content())
    u_f = bakery.Cake.from_file(file_path, role=bakery.CakeRole.NEURON)
    u2 = b2.cake()
    eq_(u_f, u2)
    eq_(u1,u2)
    ok_(u1 == u2)
    b1['a'] = inline_udk
    udk_bundle_str = '[["a"], ["%s"]]' % inline_udk
    eq_(str(b1), udk_bundle_str)
    u1 = b1.cake()
    ok_(u1 != u2)
    b2.parse(utf8_reader(BytesIO(bytes(b1))))
    eq_(str(b2), udk_bundle_str)
    eq_(b2.size(),55)
    u2 = b2.cake()
    eq_(u1, u2)
    del b2['a']
    u2= b2.cake()
    eq_(u0,u2)
    eq_(b1['a'], bakery.Cake(inline_udk))
    eq_(b1.get_cakes(), [bakery.Cake(inline_udk)])
    eq_([k for k in b1], ['a'])
    eq_([k for k in b2], [])
    eq_(b1.get_name_by_cake(inline_udk), 'a')
    eq_(b1.get_name_by_cake(str(bakery.Cake(inline_udk))), 'a')
    eq_(bakery.CakeRack(b1.to_json()), b1)
    eq_(bakery.CakeRack.ensure_it(b1.to_json()), b1)
    eq_(len(b1),1)
    eq_(str(b1),udk_bundle_str)
    eq_(hash(b1),hash(udk_bundle_str))
    eq_(u1 == str(u1), False)






