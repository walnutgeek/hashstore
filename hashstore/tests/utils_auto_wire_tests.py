from typing import Any

from nose.tools import eq_,ok_,with_setup
import sys
from hashstore.tests import TestSetup, assert_text
import hashstore.utils.fio as fio
from hashstore.utils import exception_message
from hashstore.utils.auto_wire import AutoWire, AutoWireRoot, wire_names

test = TestSetup(__name__,ensure_empty=True)
log = test.log
fio.ensure_directory(test.dir)


# def test_docs():
#     import doctest
#     import hashstore.utils.auto_wire as aw
#     r = doctest.testmod(aw)
#     ok_(r.attempted > 0, f'There is no doctests in module {t}')
#     eq_(r.failed,0)


def test_wiring():
    class Dependencies(AutoWire):
        _dependencies = []

        def add(self, depend_on: AutoWire) -> 'Dependencies':
            self._dependencies.append(depend_on)
            return self

    x = Dependencies()

    z = x.y.z
    eq_(z._root(), None)
    eq_(wire_names(z._path()), ['', 'y','z'])

    class Dag(metaclass=AutoWireRoot):
        x=3
        input = Dependencies()
        task1 = Dependencies().add(input.a)
        task2 = Dependencies().add(task1.input.v)
        output= Dependencies().add(task2.output.x)

    eq_(wire_names(Dag.input.a._path()), ['input', 'a'])
    eq_(wire_names(Dag.task1.input.v._path()), ['task1', 'input', 'v'])

    eq_(Dag.input.a._root(), Dag)
    eq_(Dag.task1.input.v._root(), Dag)
    eq_(list(Dag._children.keys()),['input', 'task1', 'task2', 'output'])

    try:
        q=x._q
        ok_(False)
    except AttributeError:
        eq_(exception_message(), 'no privates: _q')