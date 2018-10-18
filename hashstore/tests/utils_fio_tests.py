from nose.tools import eq_,ok_
from hashstore.tests import TestSetup
import hashstore.utils.fio as fio

test = TestSetup(__name__,ensure_empty=True)
log = test.log
fio.ensure_directory(test.dir)


def test_docs():
    import doctest
    r = doctest.testmod(fio)
    ok_(r.attempted > 0, 'There is no doctests in module')
    eq_(r.failed,0)


def test_split_all():
    eq_(fio.path_split_all('/a/b/c'), ['/', 'a', 'b', 'c'])
    eq_(fio.path_split_all('/a/b/c/'), ['/', 'a', 'b', 'c', ''])
    eq_(fio.path_split_all('/a/b/c', True), ['/', 'a', 'b', 'c', ''])
    eq_(fio.path_split_all('/a/b/c/', True), ['/', 'a', 'b', 'c', ''])
    eq_(fio.path_split_all('/a/b/c', False), ['/', 'a', 'b', 'c'])
    eq_(fio.path_split_all('/a/b/c/', False), ['/', 'a', 'b', 'c'])
    eq_(fio.path_split_all('a/b/c'), ['a', 'b', 'c'])
    eq_(fio.path_split_all('a/b/c/'), ['a', 'b', 'c', ''])
    eq_(fio.path_split_all('a/b/c', True), ['a', 'b', 'c', ''])
    eq_(fio.path_split_all('a/b/c/', True), ['a', 'b', 'c', ''])
    eq_(fio.path_split_all('a/b/c', False), ['a', 'b', 'c'])
    eq_(fio.path_split_all('a/b/c/', False), ['a', 'b', 'c'])


