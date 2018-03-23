from nose.tools import eq_,ok_,with_setup
import sys
from hashstore.tests import TestSetup
import hashstore.utils as u
from os import environ
from hashstore.utils import type_required as required
import attr
from six import text_type

test = TestSetup(__name__,ensure_empty=True)
log = test.log


substitutions = {'{test_dir}': test.dir, '{q}': 'q'}

u.ensure_directory(test.dir)

def test_docs():
    import doctest
    import hashstore.utils as test1
    import hashstore.utils.ignore_file as test2
    for t in (test1,test2):
        r = doctest.testmod(t)
        ok_(r.attempted > 0, 'There is not doctests in module')
        eq_(r.failed,0)


def test_path_resolver():
    r = u.create_path_resolver(substitutions)
    eq_(r('{test_dir}/x/y/z'), test.dir + '/x/y/z')
    eq_(r('x/{q}/y/z'), 'x/q/y/z')
    eq_(r('/x/{q}/y/z'), '/x/q/y/z')
    eq_(r('/x/{q}/y/z/'), '/x/q/y/z/')
    eq_(r('{env.HOME}/y/z/'), environ.get('HOME') + '/y/z/')
    eq_(r('~/y/z/'), environ.get('HOME') + '/y/z/')

    #override environment variable
    r = u.create_path_resolver({'{env.HOME}' : 'other'})
    eq_(r('{env.HOME}/y/z/'), 'other/y/z/')
    eq_(r('~/y/z/'), environ.get('HOME') + '/y/z/')


def test_split_all():
    eq_(u.path_split_all('/a/b/c'), ['/', 'a', 'b', 'c'])
    eq_(u.path_split_all('/a/b/c/'), ['/', 'a', 'b', 'c', ''])
    eq_(u.path_split_all('/a/b/c', True), ['/', 'a', 'b', 'c', ''])
    eq_(u.path_split_all('/a/b/c/', True), ['/', 'a', 'b', 'c', ''])
    eq_(u.path_split_all('/a/b/c', False), ['/', 'a', 'b', 'c'])
    eq_(u.path_split_all('/a/b/c/', False), ['/', 'a', 'b', 'c'])
    eq_(u.path_split_all('a/b/c'), ['a', 'b', 'c'])
    eq_(u.path_split_all('a/b/c/'), ['a', 'b', 'c', ''])
    eq_(u.path_split_all('a/b/c', True), ['a', 'b', 'c', ''])
    eq_(u.path_split_all('a/b/c/', True), ['a', 'b', 'c', ''])
    eq_(u.path_split_all('a/b/c', False), ['a', 'b', 'c'])
    eq_(u.path_split_all('a/b/c/', False), ['a', 'b', 'c'])

read_count = 0

def test_reraise():
    for i in range(2):
        try:
            try:
                raise ValueError("hello")
            except:
                if i == 0 :
                    u.reraise_with_msg('bye')
                else:
                    u.reraise_with_msg('bye', sys.exc_info()[1])
        except:
            e = sys.exc_info()[1]
            msg = u.exception_message(e)
            ok_('hello' in msg)
            ok_('bye' in msg)


def test_LazyVars():
    def val_a():
        global read_count
        read_count += 1
        return 'v=a'
    lv = u.LazyVars( a = val_a, b = 'b')
    eq_(True, 'a' in lv)
    eq_(True, 'b' in lv)
    eq_(False, 'c' in lv)
    eq_(0, read_count)
    eq_('v=a', lv['a'])
    eq_(1, read_count)
    eq_('v=a', lv['a'])
    eq_(1, read_count)
    eq_('b', lv['b'])
    eq_(str(lv),"{'a': 'v=a', 'b': 'b'}")
    lv = u.LazyVars( a = val_a, b = 'b')
    eq_('{a} -- {b}'.format(**lv),'v=a -- b')

def test_json_encoder_force_default_call():
    class q:
        pass
    try:
        u.json_encoder.encode(q())
        ok_(False)
    except:
        ok_('is not JSON serializable' in u.exception_message())


def test_if_defined():
    class O:
        def __init__(self):
            self.x = 5

        def y(self):
            return -5
    o = O()
    eq_(u.get_if_defined( o, 'x'), 5)
    eq_(u.get_if_defined( o, 'z'), None)
    eq_(u.call_if_defined( o, 'y'), -5)
    eq_(u.call_if_defined( o, 'z'), None)


def test_api():

    from hashstore.utils.api import ApiCallRegistry
    methods = ApiCallRegistry()

    class A:

        @methods.call(coerce_return_fn=lambda r: -r)
        def returns_5(self, a, b=4):
            '''
            documentation
            '''
            return 5

        @methods.call()
        def none(self):
            pass

        @methods.call(x=lambda i: i*i)
        def error(self, x):
            raise ValueError('%d' % x)

    eq_(set('returns_5 error none'.split()),set(methods.calls.keys()))
    eq_(methods.calls['returns_5'].doc.strip(),'documentation')
    a = A()
    try:
        methods.run(a, 'returns_5', {})
        ok_(False)
    except TypeError:
        eq_("returns_5() is missing required arguments: ['a']",
            u.exception_message())

    try:
        methods.run(a, 'returns_5', {'x':7})
        ok_(False)
    except TypeError:
        eq_("returns_5() does not have argument: 'x'",
            u.exception_message())

    eq_({'result': -5}, methods.run(a, 'returns_5', {'a': 7}))
    eq_({'error': '4'}, methods.run(a, 'error', {'x': 2}))
    eq_({'result': None}, methods.run(a, 'none', {}))

@attr.s
class Abc(object):
    name = attr.ib(**required(text_type))
    val = attr.ib(**required(int))


def test_implementation():
    impl = u.Implementation(u.GlobalRef(Abc),{'name':'n', 'val': 555})
    eq_(impl.create(), Abc('n',555))
    eq_(u.to_json(impl),
        '{"classRef": "hashstore.tests.utils_tests:Abc", '
        '"config": {"name": "n", "val": 555}}')
    eq_(u.from_json(u.Implementation, u.to_json(impl)).create(), Abc('n',555))