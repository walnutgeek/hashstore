from nose.tools import eq_

from hashstore.tests import doctest_it


def test_mymime():
    import hashstore.utils.file_types as test_module
    doctest_it(test_module)


def test_dict():
    from hashstore.utils.file_types import file_types
    html_ = file_types["HTML"]
    eq_(html_._key_,"HTML")
    eq_(html_.mime,'text/html')
    eq_(html_.ext,['htm', 'html'])
