from nose.tools import eq_,ok_,with_setup
import sys
from hashstore.tests import TestSetup
import hashstore.utils.jsonattr as jsonattr
from os import environ

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_docs():
    import doctest
    r = doctest.testmod(jsonattr)
    ok_(r.attempted > 0, 'There is not doctests in module')
    eq_(r.failed,0)



