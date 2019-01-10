from typing import Any

from nose.tools import eq_,ok_,with_setup
import sys
from hashstore.tests import TestSetup, assert_text
import hashstore.utils as u
import hashstore.utils.fio as fio
from hashstore.utils.args import CommandArgs


test = TestSetup(__name__,ensure_empty=True)
log = test.log
fio.ensure_directory(test.dir)

import hashstore.utils.docs as docs


def test_docs():
    import doctest
    import hashstore.utils as utils
    import hashstore.utils.ignore_file as ignore_file
    import hashstore.utils.time as time
    import hashstore.utils.template as template
    import hashstore.utils.hashing as hashing
    import hashstore.utils.typings as typings
    import hashstore.utils.log_box as log_box

    for t in (utils, ignore_file, time, template, hashing, typings,
              docs, log_box):
        r = doctest.testmod(t)
        ok_(r.attempted > 0, f'There is no doctests in module {t}')
        eq_(r.failed,0)


def test_reraise():
    for e_type in range(2):
        for i in range(2):
            try:
                try:
                    if e_type == 0 :
                        raise ValueError("EOF")
                    else:
                        eval('hello(')
                except:
                    if i == 0 :
                        u.reraise_with_msg('bye')
                    else:
                        u.reraise_with_msg('bye', sys.exc_info()[1])
            except:
                e = sys.exc_info()[1]
                msg = u.exception_message(e)
                ok_('EOF' in msg)
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


def test_mix_in():

    class B1(u.StrKeyAbcMixin):
        def __init__(self, k):
            self.k = k

        def __str__(self):
            return self.k

    class B2:
        def __init__(self, k):
            self.k = k

        def __str__(self):
            return self.k

    eq_(u.mix_in(u.StrKeyMixin, B2),
        ['_StrKeyMixin__cached_str', '__eq__', '__hash__', '__ne__'])

    class B3(u.StrKeyMixin):
        def __init__(self, k):
            self.k = k

        def __str__(self):
            return self.k

    class B4:
        def __init__(self, k):
            self.k = k

        def __str__(self):
            return self.k

    class B5:
        ...

    u.mix_in(B4, B5)
    u.mix_in(u.StrKeyMixin, B5)

    def retest(B, match = (False, True, True, False)):
        eq_(B('a') != B('a'), match[0])
        eq_(B('a') != B('b'), match[1])
        eq_(B('a') == B('a'), match[2])
        eq_(B('a') == B('b'), match[3])

    retest(B1)
    retest(B2)
    retest(B3)
    retest(B4, (True, True, False, False))
    retest(B5)

class A:
    """ An example of SmAttr usage

    Attributes:
        possible atributes of class
        i: integer
        s: string with
            default
        d: optional datetime

       attribute contributed
    """
    pass

class A_ValueError:
    """ An example of SmAttr usage

    Attributes:
        possible atributes of class
        i: integer
        s: string with
            default
        d: optional datetime
       attribute contributed
    """
    pass

def hello(i:int, s:str='xyz')-> int:
    """ Greeting protocol

    Args:
       s: string with
          default

    Returns:
        _: very important number
    """
    pass


def test_doc_str_template():
    dst = docs.DocStringTemplate(hello.__doc__, {"Args", "Returns"})
    eq_(dst.var_groups["Args"].keys(),{'s'})
    eq_(dst.var_groups["Returns"].keys(),{'_'})
    eq_(list(dst.var_groups["Returns"].format(4)),
        ['    Returns:', '        _: very important number'])
    assert_text(dst.doc(),hello.__doc__)

    dst = docs.DocStringTemplate(A.__doc__, {"Attributes"})
    attributes_ = dst.var_groups["Attributes"]
    eq_(attributes_.keys(), {'i', 's', 'd'})
    eq_(list(attributes_.format(4)),
        ['    Attributes:', '        possible atributes of class',
         '        i: integer', '        s: string with default',
         '        d: optional datetime'])
    eq_(str(attributes_['s'].content),"string with default")
    assert_text(dst.doc(),A.__doc__)

    attributes_.init_parse() # no harm to call it second time

    try:
        docs.DocStringTemplate(A_ValueError.__doc__, {"Attributes"})
        ok_(False)
    except ValueError as e:
        eq_(str(e),"Missleading indent=7? var_indent=8 "
                   "line='attribute contributed' ")

    dstNone = docs.DocStringTemplate(None, {})
    eq_(dstNone.doc(),"")
