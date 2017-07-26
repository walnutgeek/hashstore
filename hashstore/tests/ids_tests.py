from nose.tools import eq_,ok_
import hashstore.ids as ids
import six
from hashstore.utils import ensure_bytes
from hashstore.tests import TestSetup, doctest_it

from sqlalchemy import Table, MetaData, Column, types, \
    create_engine, select

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_docs():
    import hashstore.ids as test_subject
    doctest_it(test_subject)


def test_CAKe():
    def do_test(c, s, d=None):
        u1 = ids.Cake.from_string(c)
        eq_(s, str(u1))
        u1n = ids.Cake(str(u1))
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
    do_test(b'a' * 33, '1uhocJXiWEa4cLBvQRvkSQGzaiAvRB1jznYWq4xCOckO')
    do_test(b'a' * 46, '1mXcPcYpN8zZYdpM04hafWih3o1NQbr4q5bJtPYPq7Ev')


def test_Bundle():
    inline_udk = '01aMUQDApalaaYbXFjBVMMvyCAMfSPcTojI0745igi'
    b1 = ids.NamedCAKes()
    eq_(b1.content(),'[[], []]')
    u1 = b1.cake()
    u0 = u1
    file_path = test.file_path('content.json')
    with open(file_path, 'w') as w:
        w.write(b1.content())
    b2 = ids.NamedCAKes().parse(b1.content())
    u_f = ids.Cake.from_file(file_path, ids.DataType.BUNDLE)
    u2 = b2.cake()
    eq_(u_f, u2)
    eq_(u1,u2)
    ok_(u1 == u2)
    b1['a'] = inline_udk
    udk_bundle_str = '[["a"], ["%s"]]' % inline_udk
    eq_(str(b1), udk_bundle_str)
    u1 = b1.cake()
    ok_(u1 != u2)
    b2.parse(six.BytesIO(ensure_bytes(b1.content())))
    eq_(str(b2), udk_bundle_str)
    eq_(b2.size(),55)
    u2 = b2.cake()
    eq_(u1, u2)
    del b2['a']
    u2= b2.cake()
    eq_(u0,u2)
    eq_(b1['a'], ids.Cake(inline_udk))
    eq_(b1.get_udks(), [ids.Cake(inline_udk)])
    eq_([k for k in b1], ['a'])
    eq_([k for k in b2], [])
    eq_(b1.get_name_by_udk(inline_udk), 'a')
    eq_(b1.get_name_by_udk(str(ids.Cake(inline_udk))), 'a')
    eq_(ids.NamedCAKes(b1.to_json()), b1)
    eq_(ids.NamedCAKes.ensure_it(b1.to_json()), b1)
    eq_(len(b1),1)
    eq_(str(b1),udk_bundle_str)
    eq_(hash(b1),hash(udk_bundle_str))
    eq_(u1 == str(u1), False)








