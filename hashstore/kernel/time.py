import pytz
from croniter import croniter

from hashstore.kernel import Stringable, EnsureIt, StrKeyMixin


class CronExp(Stringable,EnsureIt,StrKeyMixin):
    '''
    >>> c = CronExp('* * 9 * *')
    >>> c
    CronExp('* * 9 * *')
    >>> str(c)
    '* * 9 * *'
    '''
    def __init__(self, s):
        self.exp = s
        self.croniter()

    def croniter(self, dt=None):
        return croniter(self.exp,dt)

    def __str__(self):
        return self.exp


class TimeZone(Stringable,EnsureIt,StrKeyMixin):
    '''
    >>> c = TimeZone('Asia/Tokyo')
    >>> c
    TimeZone('Asia/Tokyo')
    >>> str(c)
    'Asia/Tokyo'
    >>> TimeZone('Asia/Toky') # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ...
    UnknownTimeZoneError: 'Asia/Toky'
    '''
    def __init__(self, s):
        self.tzName = s
        self.tz()

    def tz(self):
        return pytz.timezone(self.tzName)

    def __str__(self):
        return self.tzName

