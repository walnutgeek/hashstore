from hs_build_tools.nose import doctest_it, eq_


def test_mymime():
    import hashstore.kernel.file_types as test_module
    doctest_it(test_module)


def test_dict():
    from hashstore.kernel.file_types import file_types
    html_ = file_types["HTML"]
    eq_(html_.mime,'text/html')
    eq_(html_.ext,['htm', 'html'])
