import hashstore.kernel.base_x as bx
from hashstore.tests import doctest_it, random_bytes, seed
from nose.tools import eq_,ok_

b58 = bx.base_x(58)


def test_nulls():
    eq_(b58.decode('12'), b'\x00\x01')
    eq_(b58.decode(b'12'), b'\x00\x01')
    eq_(b58.encode(b'\0\1'),'12')
    eq_(b58.decode('1'), b'\x00')
    eq_(b58.encode(b'\0'),'1')
    eq_(b58.decode(''), b'')
    eq_(b58.encode(b''),'')
    try:
        b58.encode('')
        ok_(False)
    except TypeError:
        pass


def test_randomized():
    all_codecs = [bx.base_x(k) for k in bx.alphabets]

    seed(0)
    for sz in [1, 2, 0, 3, 1, 77, 513, 732]:
        b = random_bytes(sz)

        for codec in all_codecs:
            s = codec.encode(b)
            eq_(codec.decode(s), b)
            s = codec.encode_check(b)
            eq_(codec.decode_check(s), b)


def test_docs():
    doctest_it(bx)
