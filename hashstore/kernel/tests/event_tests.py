from typing import Any
import hashstore.kernel.event as e
from logging import getLogger
from hashstore.build_tools.nose import eq_,ok_
from hashstore.kernel import exception_message, quict
from hashstore.kernel.smattr import Mold, SmAttr, ReferenceResolver

log = getLogger(__name__)


def test_docs():
    import doctest
    r = doctest.testmod(e)
    ok_(r.attempted > 0, f'There is no doctests in module {e}')
    eq_(r.failed,0)


def test_wiring():
    try:
        class Abc(metaclass=e.ExecutibleFactory):
            pass
        ok_(False)
    except AttributeError :
        ok_(all( s in exception_message() for s in
                  ("Undefined:", "'in_mold'", "'out_mold'")))


    class AbcDef(metaclass=e.ExecutibleFactory):
        class Input:
            a:int
            b:str
            c:bool
        class Output:
            d:int
            e:float
            f:str
    ok_(isinstance(AbcDef, e.ExecutibleFactory))

    eq_(AbcDef.in_mold.to_json(),
        ['a:Required[int]', 'b:Required[str]', 'c:Required[bool]'])

    eq_(AbcDef.out_mold.to_json(),
        ['d:Required[int]', 'e:Required[float]', 'f:Required[str]'])

    class AbcDef2(metaclass=e.ExecutibleFactory):
        in_mold = Mold(['a:Required[int]', 'b:Required[str]', 'c:Required[bool]'])
        out_mold = Mold(['d:Required[int]', 'e:Required[float]', 'f:Required[str]'])

    ok_(AbcDef.in_mold == AbcDef2.in_mold)


class ComplexInput(SmAttr):
    q: int
    a: str


class ComplexOut(SmAttr):
    z: str
    v: ComplexInput


def fn1(z:int, x:bytes, y:ComplexInput)->ComplexOut:
    return ComplexOut(z=f'z={z} y.a={y.a}', v=y)


def fn2(z:int, x:bytes, y:ComplexInput)->ComplexOut:
    raise AttributeError(f'z={z} y.a={y.a}')


def fn3(z:int, x:bytes, y:ComplexInput)->None:
    pass


class InOut(metaclass=e.ExecutibleFactory):
    Input = ComplexInput
    out_mold = Mold(ComplexOut)


class Fn1Match(metaclass=e.ExecutibleFactory):

    class Input(SmAttr):
        z: int
        x: bytes
        y: ComplexInput

    out_mold = Mold(ComplexOut)


class Fn1Match2(metaclass=e.ExecutibleFactory):
    in_mold = Mold(Fn1Match.Input)
    Output = ComplexOut



class CacheResover(ReferenceResolver):
    def __init__(self):
        self.index=0
        self.cache={}

    def flatten(self, v:Any) -> str:
        k=str(self.index)
        self.cache[k]=v
        self.index += 1
        return k

    def dereference(self, s:str) -> Any:
        return self.cache[s]


BCFDLJLDFK = 'bcfdljldfk'


def test_events():

    ffn1 = e.Function.parse(fn1)
    eq_(ffn1.in_mold, Fn1Match.in_mold)
    eq_(ffn1.out_mold, Fn1Match.out_mold)
    eq_(ffn1.in_mold, Fn1Match2.in_mold)
    eq_(ffn1.out_mold, Fn1Match2.out_mold)

    ffn2 = e.Function.parse(fn2)
    ffn3 = e.Function.parse(fn3)
    eq_(str(ffn3),
        '{"in_mold": ["z:Required[int]", "x:Required[bytes]", '
        '"y:Required[hashstore.kernel.tests.event_tests:ComplexInput]"], '
        '"out_mold": [], "ref": "hashstore.kernel.tests.event_tests:fn3"}')
    resolver = CacheResover()

    e1,e2 = do_run_events(ffn1, ffn2, resolver)
    ok_(BCFDLJLDFK in e1[1].output_edge.vars['z'])
    ok_(BCFDLJLDFK in e2[1].error_edge.vars['traceback'])

    do_run_events(ffn3, ffn2, resolver)
    do_run_events(e.Function.ensure_it(ffn1.to_json()),
                  e.Function.ensure_it(ffn2.to_json()), resolver)


def do_run_events(ffn1, ffn2, resolver):
    complex_input = ComplexInput(q=7, a=BCFDLJLDFK)
    ref = resolver.flatten(complex_input)
    ok_(isinstance(ref,str))
    e1 = list(ffn1.invoke(
        quict(z=5, x=b'0123456789ABCDFG', y=ref),
        resolver))
    eq_(e1[1].state, e.EventState.SUCCESS)
    e2 = list(ffn2.invoke(
        quict(z=5, x=b'0123456789ABCDFG', y=ref),
        resolver))
    eq_(e2[1].state, e.EventState.FAIL)
    return e1, e2
