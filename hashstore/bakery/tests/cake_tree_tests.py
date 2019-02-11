import hashstore.bakery.cake_tree as cake_tree
from hashstore.tests import TestSetup
from hashstore.build_tools.nose import doctest_it


test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_docs():
    doctest_it(cake_tree)


def test_tree():
    pass









