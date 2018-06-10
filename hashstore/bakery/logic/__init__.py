import abc
import attr
from hashstore.utils import (
    type_optional as optional,
    type_required as required,
    type_list_of as list_of,
    type_dict_of as dict_of, GlobalRef)
from hashstore.utils.file_types import FileType
from hashstore.utils.time import CronExp, TimeZone


class HashType(metaclass=abc.ABCMeta): # HashType ?
    '''
    To make doctests pass
    >>> 1
    1

    (Y)=<HL>,detect:M
    '''
    def __repr__(self):
        return '{t.__module__}/{t.__name__}'.format(t=type(self))

    @abc.abstractmethod
    def detect(self, store, cake):
        raise NotImplementedError('subclasses must override')


class HashMethod(metaclass=abc.ABCMeta):
    '''
    (Y)=<HL>,detect:M
    '''
    def __repr__(self):
        return '{t.__module__}/{t.__name__}'.format(t=type(self))

    @abc.abstractmethod
    def invoke(self, store, values):
        raise NotImplementedError('subclasses must override')


@attr.s
class Type(object):
    name=attr.ib(**required(str))
    file_type=attr.ib(**optional(FileType))
    ref=attr.ib(**optional(GlobalRef))


@attr.s
class ValueDescriptor(object):
    name = attr.ib(**required(str))
    type = attr.ib(**required(GlobalRef))
    #format = attr.ib(**type_optional())


@attr.s
class Method(object):
    name = attr.ib(**required(str))
    applies_on = attr.ib(**optional(Type))
    in_vars=attr.ib(**list_of(ValueDescriptor))
    out_vars=attr.ib(**list_of(ValueDescriptor))



@attr.s
class Task(object):
    name = attr.ib(**required(str))
    method_name = attr.ib(**required(str))
    depend_on_tasks = attr.ib(**list_of(str))
    dag_vars = attr.ib(**list_of(ValueDescriptor))
    in_vars = attr.ib(**list_of(ValueDescriptor))


@attr.s
class Trigger(object):
    cron = attr.ib(**required(CronExp))
    tz = attr.ib(**optional(TimeZone, TimeZone('UTC')))

@attr.s
class Dag(object):
    name = attr.ib(**required(str))
    depend_on_prev = attr.ib(**required(bool))
    triggers = attr.ib(**list_of(Trigger))
    tasks = attr.ib(**list_of(Task))
    in_vars=attr.ib(**list_of(ValueDescriptor))


@attr.s
class HashLogic(object):
    name = attr.ib(**required(str))
    types = attr.ib(**list_of(Type))
    files=attr.ib(**dict_of(FileType))
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

