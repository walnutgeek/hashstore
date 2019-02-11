from doctest import testmod
from nose.tools import ok_, eq_


def doctest_it(m):
    results = testmod(m)
    ok_(results.attempted > 0, 'There is not doctests in module')
    eq_(results.failed, 0)


def assert_text(src, expect, save_words=None):
    '''
    matches texts ignoring spaces.

    Some fragment of the `src` could be ignored if it is maked
    inside `expect` with placeholders:

    ... - ignore word
    .... - ignore any number of words until next word match

    TODO: it works but it is inconsistent with ellipsis syntax in
    doctest. I guess you could see bit of irony bellow.

    >>> assert_text('abc   xyz', ' abc xyz ')
    >>> assert_text('abc asdf  xyz', ' abc ... xyz ')
    >>> assert_text('abc asdf iklmn xyz', ' abc ... xyz ')
    Traceback (most recent call last):
    ...
    AssertionError: 'iklmn' != 'xyz'
    >>> assert_text('abc asdf iklmn xyz', ' abc .... xyz ')
    >>> save_vars = []
    >>> pattern = ' abc ... rrr ... xyz '
    >>> assert_text('abc asdf rrr qqq xyz', pattern, save_vars)
    >>> save_vars
    ['asdf', 'qqq']

    '''
    src_it = iter(src.split())
    expect_it = iter(expect.split())
    look_until_match = False
    s1, s2 = None, None
    while True:
        try:
            s1 = next(src_it)
        except StopIteration:
            try:
                s2 = next(expect_it)
            except StopIteration:
                break
            print(src)
            ok_(False,'expecting longer text %r %r' % (s1,s2))
        if look_until_match:
            if s2 == s1:
                look_until_match = False
            continue
        try:
            s2 = next(expect_it)
        except StopIteration:
            print(src)
            ok_(False,'expecting shorter text')
        if s2 == '....':
            look_until_match = True
            s2 = None
            try:
                s2 = next(expect_it)
            except StopIteration:
                pass
        elif s2 == '...':
            if save_words is not None:
                save_words.append(s1)
        else:
            if s1 != s2:
                print(src)
                eq_(s1,s2)
