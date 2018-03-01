from hashstore.bakery import Cake
from croniter import croniter
import pytz
import inspect
import abc
from six import text_type, add_metaclass
import attr
from hashstore.utils import EnsureIt, Stringable, StrKeyMixin
from hashstore.utils.jsonattr import \
    type_optional as optional, \
    type_required as required, \
    type_list_of as list_of


@add_metaclass(abc.ABCMeta)
class HashType(): # HashType ?
    '''
    (Y)=<HL>,detect:M
    '''
    def __repr__(self):
        return '{t.__module__}/{t.__name__}'.format(t=type(self))

    @abc.abstractmethod
    def detect(self, store, cake):
        raise NotImplementedError('subclasses must override')


@add_metaclass(abc.ABCMeta)
class HashMethod(object):
    '''
    (Y)=<HL>,detect:M
    '''
    def __repr__(self):
        return '{t.__module__}/{t.__name__}'.format(t=type(self))

    @abc.abstractmethod
    def invoke(self, store, values):
        raise NotImplementedError('subclasses must override')

class GlobalRef(Stringable,EnsureIt,StrKeyMixin):
    '''
    >>> ref = GlobalRef('hashstore.bakery.logic/GlobalRef')
    >>> ref
    GlobalRef('hashstore.bakery.logic/GlobalRef')
    >>> ref.get_instance().__name__
    'GlobalRef'
    >>> GlobalRef(GlobalRef)
    GlobalRef('hashstore.bakery.logic/GlobalRef')
    '''
    def __init__(self, s):
        if inspect.isclass(s) or inspect.isfunction(s):
            self.module, self.name = s.__module__, s.__name__
        else:
            self.module, self.name = s.split('/')

    def __str__(self):
        return '%s/%s' %(self.module, self.name)

    def get_instance(self):
        mod = __import__(self.module, fromlist=('',))
        return getattr(mod, self.name)


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

@attr.s
class Type(object):
    name=attr.ib(**required(text_type))
    ref=attr.ib(**optional(GlobalRef))

@attr.s
class ValueDescriptor(object):
    name = attr.ib(**required(text_type))
    type = attr.ib(**required(GlobalRef))
    #format = attr.ib(**type_optional())




@attr.s
class Method(object):
    name = attr.ib(**required(text_type))
    ref = attr.ib(**required(GlobalRef))
    applies_on = attr.ib(**optional(Type))
    in_vars=attr.ib(**list_of(ValueDescriptor))
    out_vars=attr.ib(**list_of(ValueDescriptor))


@attr.s
class Task(object):
    name = attr.ib(**required(text_type))
    method_name = attr.ib(**required(text_type))
    depend_on_tasks = attr.ib(**list_of(text_type))
    dag_vars = attr.ib(**list_of(ValueDescriptor))
    in_vars = attr.ib(**list_of(ValueDescriptor))



@attr.s
class Trigger(object):
    cron = attr.ib(**required(CronExp))
    tz = attr.ib(**optional(TimeZone, TimeZone('UTC')))

@attr.s
class Dag(object):
    name = attr.ib(**required(text_type))
    depend_on_prev = attr.ib(**required(bool))
    triggers = attr.ib(**list_of(Trigger))
    tasks = attr.ib(**list_of(Task))
    in_vars=attr.ib(**list_of(ValueDescriptor))


@attr.s
class HashLogic(object):
    name = attr.ib(**required(text_type))
    types = attr.ib(**list_of(Type))
    dags = attr.ib(**list_of(Dag))
    methods = attr.ib(**list_of(Method))



'''
  CauseEffectVector
    (CEV)=
    run:R?,
    ver:HL,
    method,
    this?,
    params*,
    results+
    
  db:CauseVector
  db:EffectVector
  db:TransformVector
    (LV)=
    CEV=srcH,
    HL+L,
    detected,
    outH
  Invocation
    (I)=
    HL+D
    params,
    results
  Run
    (R)=
    I,HL+D+T
    params,
    results
  Attempt
    (A) = R
'''

class CodeBase:
    '''
    (C)
    '''
    pass

class CodeEnv:
    '''
    (E)
    '''
    pass

class CodeVersion:
    '''
    (V) - SHA256 for CodeEnv PORTAL
    '''
    pass



class Lens:
    '''
    (L)=<HL+T>,transform():M,params*
    '''
    pass

