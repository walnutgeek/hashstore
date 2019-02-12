import sys
import hashstore.kernel as kernel
import hashstore.kernel.docs as docs
from hs_build_tools.nose import assert_text
from logging import getLogger
from hs_build_tools.nose import eq_,ok_

log = getLogger(__name__)


def test_docs():
    import doctest
    import hashstore.kernel.time as time
    import hashstore.kernel.hashing as hashing
    import hashstore.kernel.typings as typings

    for t in (kernel, time, hashing, typings,
              docs):
        r = doctest.testmod(t)
        ok_(r.attempted > 0, f'There is no doctests in module {t}')
        eq_(r.failed,0)


def test_reraise():
    for e_type in range(2):
        for i in range(2):
            try:
                try:
                    if e_type == 0:
                        raise ValueError("EOF")
                    else:
                        eval('hello(')
                except:
                    if i == 0 :
                        kernel.reraise_with_msg('bye')
                    else:
                        kernel.reraise_with_msg('bye', sys.exc_info()[1])
            except:
                e = sys.exc_info()[1]
                msg = kernel.exception_message(e)
                ok_('EOF' in msg)
                ok_('bye' in msg)


def test_json_encoder_force_default_call():
    class q:
        pass
    try:
        kernel.json_encoder.encode(q())
        ok_(False)
    except:
        ok_('is not JSON serializable' in kernel.exception_message())





def test_mix_in():

    class B1(kernel.StrKeyAbcMixin):
        def __init__(self, k):
            self.k = k

        def __str__(self):
            return self.k

    class B2:
        def __init__(self, k):
            self.k = k

        def __str__(self):
            return self.k

    eq_(kernel.mix_in(kernel.StrKeyMixin, B2),
        ['_StrKeyMixin__cached_str', '__eq__', '__hash__', '__ne__'])

    class B3(kernel.StrKeyMixin):
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

    kernel.mix_in(B4, B5)
    kernel.mix_in(kernel.StrKeyMixin, B5)

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
        eq_(str(e), "Missleading indent=7? var_indent=8 "
                    "line='attribute contributed' ")

    dstNone = docs.DocStringTemplate(None, {})
    eq_(dstNone.doc(), "")
