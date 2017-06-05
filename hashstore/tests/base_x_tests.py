import hashstore.base_x
from hashstore.tests import doctest_it
from nose.tools import eq_,ok_

b58 = hashstore.base_x.base_x(58)


def test_nulls():
    eq_(b58.decode('12'), b'\x00\x01')
    eq_(b58.decode(b'12'), b'\x00\x01')
    eq_(b58.encode(b'\0\1'),'12')
    eq_(b58.decode('1'), b'\x00')
    eq_(b58.encode(b'\0'),'1')
    eq_(b58.decode(''), b'')
    eq_(b58.encode(b''),'')
    try:
        b58.encode(u'')
        ok_(False)
    except TypeError:
        pass


def test_randomized():
    all_codecs = [hashstore.base_x.base_x(k) for k in hashstore.base_x.alphabets]

    import numpy.random as rand
    rand.seed(0)
    for sz in [1, 2, 0, 3, 1, 77, 513, 732]:
        b = rand.bytes(sz)

        for codec in all_codecs:
            s = codec.encode(b)
            eq_(codec.decode(s), b)
            s = codec.encode_check(b)
            eq_(codec.decode_check(s), b)


def test_docs():
    import hashstore.base_x as test_module
    doctest_it(test_module)
