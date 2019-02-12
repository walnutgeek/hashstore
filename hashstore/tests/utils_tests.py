
from hs_build_tools.nose import eq_,ok_
from hashstore.kernel import exception_message
from hashstore.tests import TestSetup, assert_text
import hashstore.utils.fio as fio
from hashstore.utils.args import CommandArgs


test = TestSetup(__name__,ensure_empty=True)
log = test.log
fio.ensure_directory(test.dir)



def test_docs():
    import doctest
    import hashstore.utils as utils
    import hashstore.utils.ignore_file as ignore_file
    import hashstore.utils.log_box as log_box

    for t in (utils, ignore_file, log_box):
        r = doctest.testmod(t)
        ok_(r.attempted > 0, f'There is no doctests in module {t}')
        eq_(r.failed,0)


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
            exception_message())

    try:
        methods.run(a, 'returns_5', {'x':7})
        ok_(False)
    except TypeError:
        eq_("returns_5() does not have argument: 'x'",
            exception_message())

    eq_({'result': -5}, methods.run(a, 'returns_5', {'a': 7}))
    eq_({'error': '4'}, methods.run(a, 'error', {'x': 2}))
    eq_({'result': None}, methods.run(a, 'none', {}))


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
    usage: ... -m nose [-h] {do} ...
    
    test cli
    
    positional arguments:
      {do}
        do       do something
    
    optional arguments:
      -h, --help  show this help message and exit
    """)

    ca.run(ca.parse_args(('do', '--test1', 'abc')))
    eq_(v['do'], 'abc')




