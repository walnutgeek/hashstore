from hashstore.tests import doctest_it


def test_mymime():
    import hashstore.mymime as test_module
    doctest_it(test_module)
