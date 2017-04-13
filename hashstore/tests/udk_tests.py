from nose.tools import eq_,ok_,with_setup
import base64
import hashstore.udk
import six
import logging
from hashstore.utils import ensure_bytes
from hashstore.tests import seed,random_small_caps

log = logging.getLogger(__name__)


def test_mime64_size():
    real_sizes = list(map(lambda i: len(base64.b64encode(b'a' * i)), range(50)))
    calc_sizes = list(map(hashstore.udk.mime64_size, range(50)))
    eq_(real_sizes, calc_sizes)


def test_biggest_size_that_smaller_then_hash():
    real_sizes = list(map(lambda i: len(base64.b64encode(b'a' * i)), range(50)))
    hash_size = len(hashstore.udk.EMPTY_HASH)
    eq_(hash_size,64)
    eq_(len(list(filter(lambda x: x < hash_size,real_sizes))),46)


def test_UDK():
    def do_test(c, s, d=None):
        u1 = hashstore.udk.UDK_from_string(c)
        eq_(s, str(u1))
        u1n = hashstore.udk.UDK(str(u1))
        eq_(u1.k, u1n.k)
        if d is None:
            ok_(not(u1.has_data()))
        else:
            ok_(u1.has_data())
            eq_(d,u1.hexdigest())
            u2 = hashstore.udk.UDK(u1.hexdigest())
            eq_(u1,u2)
            ok_(not(u2.has_data()))
            eq_(c,u1.data())


    do_test(b'', 'M', hashstore.udk.EMPTY_HASH)
    do_test(b'a' * 1, 'MYQ==',
            'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb')
    do_test(b'a' * 2, 'MYWE=',
            '961b6dd3ede3cb8ecbaacbd68de040cd78eb2ed5889130cceb4c49268ea4d506')
    do_test(b'a' * 3, 'MYWFh',
            '9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0')
    do_test(b'a' * 45, 'MYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFh',
            '52789e3423b72beeb898456a4f49662e46b0cbb960784c5ef4b1399d327e7c27')
    do_test(b'a' * 46, '6643110c5628fff59edf76d82d5bf573bf800f16a4d65dfb1e5d6f1a46296d0b')

    # ok_(False)

def test_Bundle():
    inline_udk = 'M2MJrQoJnyE16leiBSMGeQOj7z+ZPuuaveBlvnOn3et1CzowDuGbTqw=='
    b1 = hashstore.udk.NamedUDKs()
    u1, _, c = b1.udk_content()
    u0 = u1
    b2 = hashstore.udk.NamedUDKs().parse(c)
    u2, _, c = b2.udk_content()
    eq_(u1,u2)
    ok_(u1 == u2)
    b1['a'] = inline_udk
    udk_bundle_str = '[["a"], ["%s"]]' % inline_udk
    eq_(str(b1), udk_bundle_str)
    u1, _, c = b1.udk_content()
    ok_(u1 != u2)
    b2.parse(six.BytesIO(ensure_bytes(c)))
    eq_(str(b2), udk_bundle_str)
    u2, _, c = b2.udk_content()
    eq_(u1, u2)
    del b2['a']
    u2, _, c = b2.udk_content()
    eq_(u0,u2)
    eq_(b1['a'],hashstore.udk.UDK(inline_udk))
    eq_(b1.get_udks(),[hashstore.udk.UDK(inline_udk)])
    eq_([k for k in b1], ['a'])
    eq_([k for k in b2], [])
    eq_(b1.get_name_by_udk(inline_udk), 'a')
    eq_(b1.get_name_by_udk(hashstore.udk.UDK(inline_udk).hexdigest()), 'a')
    eq_(hashstore.udk.NamedUDKs(b1.to_json()),b1)
    eq_(hashstore.udk.NamedUDKs.ensure_it(b1.to_json()),b1)
    eq_(len(b1),1)
    eq_(str(b1),udk_bundle_str)
    eq_(hash(b1),hash(udk_bundle_str))

uuudk = lambda ch: ch * 64
zuudk = lambda ch: hashstore.udk.UDK(uuudk(ch))
u_or_z_uudk = lambda i, ch: (uuudk if i % 2 == 1 else zuudk)(ch)
ssset = lambda set: ''.join( k.k[:1] for k in set)


def test_Set():
    seed(0)
    cases = random_small_caps(100)
    set = hashstore.udk.UdkSet()
    a = ''
    for i,c in enumerate(cases):
        k = u_or_z_uudk(i,c)
        a += 'a' if set.add(k) else ' '
    eq_( cases, 'mpvaddhjtvsexgyymbghxoyrfnijutqtfppasdyrtttohabjakuxdlsxcaaevfgiurpejkybbhjdgxlosaodvmkulegepudmeuio')
    eq_(a,      'aaaaa aaa aaaaa  a   a aaaa a a                  a   a  a                                           ')
    eq_(ssset(set), 'abcdefghijklmnopqrstuvxy')
    ok_(uuudk('a') in set)
    ok_(zuudk('a') in set)
    ok_(uuudk('z') not in set)
    ok_(zuudk('z') not in set)
    eq_(hashstore.udk.UdkSet(set.to_json()), set)
    eq_(hashstore.udk.UdkSet(six.BytesIO(ensure_bytes(str(set)))), set)
    eq_(hashstore.udk.UdkSet(str(set)), set)
    eq_(hash(hashstore.udk.UdkSet(str(set))), hash(set))
    eq_(hash(hashstore.udk.UdkSet(str(set))), hash(set))
    eq_(hashstore.udk.UdkSet.ensure_it(set), set)
    eq_(hashstore.udk.UdkSet.ensure_it(str(set)), set)
    eq_(set[0].k[:1], 'a')
    i = len(set)
    del set[0]
    eq_(i-1, len(set))
    eq_(ssset(set), 'bcdefghijklmnopqrstuvxy')




