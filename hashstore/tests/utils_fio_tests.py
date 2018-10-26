import os
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


CONF_DIR = ".conf_dlkfjdloeri_dir"

def test_config_dir():
    a=os.path.join(test.dir, "a")
    a_conf=os.path.join(a, CONF_DIR)
    b = os.path.join(test.dir, "b")
    b_x = os.path.join(b, "x")
    b_x_conf = os.path.join(b_x, CONF_DIR)
    b_x_y = os.path.join(b_x, "y")
    b_conf=os.path.join(b, CONF_DIR)
    c = os.path.join(test.dir, "c")
    for d in (a_conf, b_x_conf, b_x_y, b_x_conf, b_conf, c):
        fio.ensure_directory(d)
    # _not_created
    b_x_z = os.path.join(b_x, "z")
    b_x_x = os.path.join(b_x, "x")

    eq_(fio.ConfigDir.lookup_up(b_x_y, CONF_DIR).dir_path(), b_x_conf)
    eq_(fio.ConfigDir.lookup_up(b_x, CONF_DIR).dir_path(), b_x_conf)
    eq_(fio.ConfigDir.lookup_up(b_x_z, CONF_DIR).dir_path(), b_x_conf)

    class CD(fio.ConfigDir):
        __dir_name__ = CONF_DIR
        counter = 0

        def build(self):
            type(self).counter += 1

    b_x_z_cd = CD(b_x_z)
    b_x_z_cd.ensure()
    eq_(CD.counter, 1)
    eq_(CD.lookup_up(b_x_z).dir_path(),
        b_x_z_cd.dir_path())
    b_x_z_cd.ensure()
    eq_(CD.counter, 1)
    eq_(CD.lookup_up(b_x_z).dir_path(),
        b_x_z_cd.dir_path())

    b_x_x_cd = fio.ConfigDir(b_x_x, CONF_DIR)
    b_x_x_cd.ensure()
    eq_(fio.ConfigDir.lookup_up(b_x_x, CONF_DIR).dir_path(),
        b_x_x_cd.dir_path())
    b_x_x_cd.ensure()
    eq_(fio.ConfigDir.lookup_up(b_x_x, CONF_DIR).dir_path(),
        b_x_x_cd.dir_path())


    ok_(fio.ConfigDir.lookup_up(c, CONF_DIR) is None)
    ok_(fio.ConfigDir.lookup_up("c", CONF_DIR) is None)


