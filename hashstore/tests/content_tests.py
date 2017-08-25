from hashstore.tests import TestSetup, doctest_it

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_docs():
    import hashstore.bakery.content as test_subject
    doctest_it(test_subject)





