from nose.tools import eq_,ok_,with_setup
import hashstore.ids as ids
import logging
from hashstore.utils import ensure_bytes
from hashstore.tests import seed,random_small_caps, doctest_it


log = logging.getLogger(__name__)


def test_docs():
    import hashstore.ids as test_subject
    doctest_it(test_subject)


def test_CAKe():
    def do_test(c, s, d=None):
        u1 = ids.CAKe.from_string(c)
        eq_(s, str(u1))
        u1n = ids.CAKe(str(u1))
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

    # ok_(False)
#
# def test_Bundle():
#     inline_udk = 'M2MJrQoJnyE16leiBSMGeQOj7z+ZPuuaveBlvnOn3et1CzowDuGbTqw=='
#     b1 = ids.UDKBundle()
#     u1, _, c = b1.udk_content()
#     u0 = u1
#     b2 = ids.UDKBundle().parse(c)
#     u2, _, c = b2.udk_content()
#     eq_(u1,u2)
#     ok_(u1 == u2)
#     b1['a'] = inline_udk
#     udk_bundle_str = '[["a"], ["%s"]]' % inline_udk
#     eq_(str(b1), udk_bundle_str)
#     u1, _, c = b1.udk_content()
#     ok_(u1 != u2)
#     b2.parse(six.BytesIO(ensure_bytes(c)))
#     eq_(str(b2), udk_bundle_str)
#     u2, _, c = b2.udk_content()
#     eq_(u1, u2)
#     del b2['a']
#     u2, _, c = b2.udk_content()
#     eq_(u0,u2)
#     eq_(b1['a'],ids.UDK(inline_udk))
#     eq_(b1.get_udks(),[ids.UDK(inline_udk)])
#     eq_([k for k in b1], ['a'])
#     eq_([k for k in b2], [])
#     eq_(b1.get_name_by_udk(inline_udk), 'a')
#     eq_(b1.get_name_by_udk(ids.UDK(inline_udk).hexdigest()), 'a')
#     eq_(ids.UDKBundle(b1.to_json()), b1)
#     eq_(ids.UDKBundle.ensure_it(b1.to_json()), b1)
#     eq_(len(b1),1)
#     eq_(str(b1),udk_bundle_str)
#     eq_(hash(b1),hash(udk_bundle_str))
#
# uuudk = lambda ch: ch * 64
# zuudk = lambda ch: ids.UDK(uuudk(ch))
# u_or_z_uudk = lambda i, ch: (uuudk if i % 2 == 1 else zuudk)(ch)
# ssset = lambda set: ''.join( k.k[:1] for k in set)
#
#


