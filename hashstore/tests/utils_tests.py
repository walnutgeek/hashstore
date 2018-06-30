import json

from nose.tools import eq_,ok_,with_setup
import sys
from hashstore.tests import TestSetup, assert_text
import hashstore.utils as u

from hashstore.utils.args import CommandArgs
from hashstore.utils.smattr import SmAttr, Implementation

test = TestSetup(__name__,ensure_empty=True)
log = test.log


substitutions = {'{test_dir}': test.dir, '{q}': 'q'}

u.ensure_directory(test.dir)


def test_docs():
    import doctest
    import hashstore.utils as utils
    import hashstore.utils.ignore_file as ignore_file
    import hashstore.utils.time as time
    import hashstore.utils.smattr as smattr
    for t in (utils, ignore_file, time, smattr):
        r = doctest.testmod(t)
        ok_(r.attempted > 0, f'There is not doctests in module {t}')
        eq_(r.failed,0)



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


def test_json_encoder_force_default_call():
    class q:
        pass
    try:
        u.json_encoder.encode(q())
        ok_(False)
    except:
        ok_('is not JSON serializable' in u.exception_message())


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


class Abc(SmAttr):
    name:str
    val:str


def test_implementation():
    impl = Implementation({"classRef": u.GlobalRef(Abc),
                           "config":{'name':'n', 'val': 555}})
    s = str(Abc({'name': 'n', 'val': 555}))
    eq_(str(impl.create()), s)
    eq_(str(impl),
        '{"classRef": "hashstore.tests.utils_tests:Abc", '
        '"config": {"name": "n", "val": 555}}')
    eq_(str(Implementation(impl.to_json()).create()), s)


def test_args():
    ca = CommandArgs()
    v = {}
    @ca.app('test cli')
    class ClientApp:
        @ca.command('do something')
        def do(self, test1):
            v['do']=test1

    format_help = ca.get_parser().format_help()
    assert_text(format_help, """
    usage: python -m nose [-h] {do} ...
    
    test cli
    
    positional arguments:
      {do}
        do       do something
    
    optional arguments:
      -h, --help  show this help message and exit
    """)

    ca.run(ca.parse_args(('do', '--test1', 'abc')))
    eq_(v['do'], 'abc')
