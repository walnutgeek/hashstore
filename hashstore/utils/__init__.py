import inspect
from types import ModuleType
import os
import json
import sys
import uuid
import abc
import enum
from typing import Any

import attr
from collections import Mapping
from datetime import date, datetime
from dateutil.parser import parse as dt_parse
import codecs

def quict(**kwargs):
    r = {}
    r.update(**kwargs)
    return r


def failback(fn, default):
    '''
    >>> divmod(3,2)
    (1, 1)
    >>> divmod(3,0)
    Traceback (most recent call last):
    ...
    ZeroDivisionError: integer division or modulo by zero
    >>> divmod_nofail = failback(divmod,(0,0))
    >>> divmod_nofail(3,2)
    (1, 1)
    >>> divmod_nofail(3,0)
    (0, 0)
    '''
    def failback_fn(*args, **kwargs):
        try:
            return fn(*args,**kwargs)
        except:
            return default
    return failback_fn


def exception_message(e = None):
    if e is None:
        e = sys.exc_info()[1]
    return str(e)


def reraise_with_msg(msg, exception=None):
    if exception is None:
        exception = sys.exc_info()[1]
    etype = type(exception)
    try:
        new_exception = etype(exception_message(exception) + '\n'+ msg)
    except:
        new_exception = ValueError(exception_message(exception) + '\n'+ msg)
    traceback = sys.exc_info()[2]
    raise new_exception.with_traceback(traceback)


def ensure_directory(directory: str):
    if not (os.path.isdir(directory)):
        os.makedirs(directory)


ensure_bytes = lambda s: s if isinstance(s, bytes)\
    else str(s).encode('utf-8')

ensure_string = lambda s: s if isinstance(s, str)\
    else s.decode('utf-8') if isinstance(s, bytes) else str(s)

utf8_reader = codecs.getreader("utf-8")


def path_split_all(path: str, ensure_trailing_slash: bool = None):
    '''
    >>> path_split_all('/a/b/c')
    ['/', 'a', 'b', 'c']
    >>> path_split_all('/a/b/c/' )
    ['/', 'a', 'b', 'c', '']
    >>> path_split_all('/a/b/c', ensure_trailing_slash=True)
    ['/', 'a', 'b', 'c', '']
    >>> path_split_all('/a/b/c/', ensure_trailing_slash=True)
    ['/', 'a', 'b', 'c', '']
    >>> path_split_all('/a/b/c/', ensure_trailing_slash=False)
    ['/', 'a', 'b', 'c']
    >>> path_split_all('/a/b/c', ensure_trailing_slash=False)
    ['/', 'a', 'b', 'c']
    '''
    def tails(head):
        while(True):
            head,tail = os.path.split(head)
            if head == '/' and tail == '':
                yield head
                break
            yield tail
            if head == '':
                break
    parts = list(tails(path))
    parts.reverse()
    if ensure_trailing_slash is not None:
        if ensure_trailing_slash :
            if parts[-1] != '':
                parts.append('')
        else:
            if parts[-1] == '':
                parts = parts[:-1]
    return parts


class EnsureIt:

    @classmethod
    def factory(cls):
        return cls

    @classmethod
    def ensure_it(cls, o):
        if isinstance(o, cls):
            return o
        return cls.factory()(o)

    @classmethod
    def ensure_it_or_none(cls, o):
        if o is None:
            return o
        return cls.ensure_it(o)


class Stringable(metaclass=abc.ABCMeta):
    '''
    Marker to inform json_encoder to use `str(o)` to
    serialize in json. Also assumes that any implementing
    class has constructor that recreate same object from
    it's string representation as single parameter.
    '''
    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, str(self))

Stringable.register(uuid.UUID)


class StrKeyMixin:
    '''
    mixin for immutable objects to implement
    `__hash__()`, `__eq__()`, `__ne__()`.

    Implementation of methods expect super calss to implement
    `__str__()` and object itself to be immutable (`str(obj)`
    expected to return same value thru the life of object)


    >>> class X(StrKeyMixin):
    ...     def __init__(self, x):
    ...         self.x = x
    ...
    ...     def __str__(self):
    ...         return self.x
    ...
    >>> a = X('A')
    >>> a != X('B')
    True
    >>> X('A') == X('B')
    False
    >>> a == X('A')
    True
    >>> a == 'A'
    False
    >>> a != X('A')
    False
    >>> hash(a) == hash(X('A'))
    True
    >>> hash(a) != hash(X('B'))
    True
    '''
    def __cached_str(self) -> str:
        if not(hasattr(self, '_str')):
            self._str = str(self)
        return self._str

    def __hash__(self):
        if not(hasattr(self, '_hash')):
            self._hash = hash(self.__cached_str())
        return self._hash

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return self.__cached_str() == other.__cached_str()

    def __ne__(self, other):
        return not self.__eq__(other)


class Jsonable(EnsureIt):
    '''
    Marker to inform json_encoder to use `o.to_json()` to
    serialize in json
    '''

    def __str__(self):
        return json_encode(self.to_json())

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not(self.__eq__(other))

class JsonWrap(Jsonable,Stringable):
    '''
    >>> jw = JsonWrap('{"b": 3, "a": 5}')
    >>> jw.json["a"]
    5
    >>> jw.json["b"]
    3
    >>> str(jw)
    '{"a": 5, "b": 3}'
    '''
    def __init__(self, s:str) -> None:
        self.json = json_decode(s)

    def to_json(self)->Any:
        return self.json


def adjust_for_json(v:Any, default:Any = None)->Any:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Stringable):
        return str(v)
    if isinstance(v, Jsonable):
        return v.to_json()
    return default


class StringableEncoder(json.JSONEncoder):
    def __init__(self):
        json.JSONEncoder.__init__(self, sort_keys=True)

    def default(self, o):
        adjusted = adjust_for_json(o)
        if adjusted is None:
            return json.JSONEncoder.default(self, o)
        else:
            return adjusted


json_encoder = StringableEncoder()

json_encode = json_encoder.encode


def load_json_file(file_path: str):
    return json.load(open(file_path))


def json_decode(text: str):
    try:
        return json.loads(text)
    except:
        reraise_with_msg('text={text}'
                         ''.format(**locals()))


def read_in_chunks(fp, chunk_size=65535):
    while True:
        data = fp.read(chunk_size)
        if not data:
            break
        yield data


class FileNotFound(Exception):
    def __init__(self, path):
        super(FileNotFound, self).__init__(path)


def print_pad(data, columns, get = None):
    if get is None:
        get = lambda r,c: r[c]
    sdata = []
    if len(data) > 0 :
        for c in columns:
            sdata.append(['' if get(r,c) is None else str(get(r,c)) for r in data])
        max_lens =[max(len(cell) for cell in scolumn) for scolumn in sdata]
        for irow in range(len(data)):
            pad = 2
            srow = ''
            for icol in range(len(columns)):
                srow += ' ' * pad
                s = sdata[icol][irow]
                srow += s
                pad = max_lens[icol]-len(s) + 2
            print(srow)


def is_file_in_directory(file, dir):
    '''
    >>> is_file_in_directory('/a/b/c.txt', '/a')
    True
    >>> is_file_in_directory('/a/b/c.txt', '/a/')
    True
    >>> is_file_in_directory('/a/b/', '/a/b/')
    True
    >>> is_file_in_directory('/a/b/', '/a/b')
    True
    >>> is_file_in_directory('/a/b', '/a/b/')
    True
    >>> is_file_in_directory('/a/b', '/a/b')
    True
    >>> is_file_in_directory('/a/b', '/a//b')
    True
    >>> is_file_in_directory('/a//b', '/a/b')
    True
    >>> is_file_in_directory('/a/b/c.txt', '/')
    True
    >>> is_file_in_directory('/a/b/c.txt', '/aa')
    False
    >>> is_file_in_directory('/a/b/c.txt', '/b')
    False
    '''
    realdir = os.path.realpath(dir)
    dir = os.path.join(realdir, '')
    file = os.path.realpath(file)
    return file == realdir or os.path.commonprefix([file, dir]) == dir


def _camel2var(c):
    return c if c.islower() else '_' + c.lower()


def from_camel_case_to_underscores(s):
    '''
    >>> from_camel_case_to_underscores('CamelCase')
    'camel_case'
    '''
    return ''.join(map(_camel2var, s)).strip('_')


class KeyMapper:
    '''
    Mapper that extracts keys out of sequence of values
    and create mapping from these keys to values from
    sequence.

    >>> class X(enum.IntEnum):
    ...     a = 1
    ...     b = 2
    ...     c = 3

    >>> m = KeyMapper(X)
    >>> list(m.keys())
    [1, 2, 3]
    >>> m.to_value(2)
    <X.b: 2>
    >>> m.to_key(X.c)
    3
    >>> m.to_value(None)
    >>> m.to_key(None)

    With custom `extract_key` lambda:
    >>> m2 = KeyMapper(X, extract_key=lambda v:v.value+1)
    >>> list(m2.keys())
    [2, 3, 4]
    >>> m2.to_value(3)
    <X.b: 2>
    >>> m2.to_key(X.c)
    4
    '''
    def __init__(self, values, extract_key = None):
        if extract_key is None:
            extract_key = lambda v: v.value
        self._extract_key = extract_key
        self._altkey_dict = {self._extract_key(v):v for v in values}

    def to_key(self, val):
        if val is None:
            return val
        else:
            return self._extract_key(val)

    def to_value(self, i):
        if i is None:
            return None
        else:
            return self._altkey_dict[i]

    def keys(self):
        return self._altkey_dict.keys()


def tuple_mapper(*mappers):
    l = len(mappers)
    def map_fn(i):
        if i < l and mappers[i] is not None:
            return mappers[i]
        else:
            return lambda x: x
    def _mapper(in_tuple):
        return tuple(map_fn(i)(v) for i, v in enumerate(in_tuple))
    return _mapper


def normalize_url(url):
    '''
    >>> normalize_url('http://abc')
    'http://abc/'
    >>> normalize_url('abc')
    'http://abc/'
    >>> normalize_url('abc:8976')
    'http://abc:8976/'
    >>> normalize_url('https://abc:8976')
    'https://abc:8976/'
    >>> normalize_url('https://abc:8976/')
    'https://abc:8976/'

    '''
    if url[-1:] != '/':
        url += '/'
    if not(url[:7] == 'http://' or url[:8] == 'https://'):
        url = 'http://' + url
    return url


def _build_if_not_yet(cls, factory):
    return lambda v: v if issubclass(type(v), cls) else factory(v)


def create_list_converter(cls):
    def converter(in_list):
        builder = _build_if_not_yet(cls, lambda v: cls(**v))
        return [builder(v) for v in in_list]
    return converter


def create_dict_converter(cls):
    def converter(in_dict):
        def build_v(v, k):
            v = _build_if_not_yet(cls, lambda v: cls(**v))(v)
            return v
        return {k: build_v(in_dict[k],k) for k in in_dict}
    return converter


def create_converter(cls):
    '''
    >>> import attr
    >>> class X:
    ...     def __init__(self,s):
    ...         self.x = int(s)
    ...
    ...     def __repr__(self):
    ...         return 'X(x=%d)' % self.x
    ...
    >>> c = create_converter(X)
    >>> c("5")
    X(x=5)
    >>> @attr.s
    ... class Y(object):
    ...    x = attr.ib(type=X,converter=create_converter(X))
    ...
    >>> create_converter(Y)({'x': '3'})
    Y(x=X(x=3))

    >>> @attr.s
    ... class Q(object):
    ...    d = attr.ib(converter=create_converter(date))
    ...

    >>> create_converter(Q)({'d': '2018-04-23'})
    Q(d=datetime.date(2018, 4, 23))

    >>> @attr.s
    ... class Q2(object):
    ...    d = attr.ib(converter=create_converter(datetime))
    ...

    >>> create_converter(Q2)({'d': '2018-04-23'})
    Q2(d=datetime.datetime(2018, 4, 23, 0, 0))

    :return: converter for particular type
    '''
    if hasattr(cls, '__attrs_attrs__'):
        def val_converter(v):
            if isinstance(v, Mapping):
                return cls(**v)
            return v
        return val_converter
    elif cls is None:
        return lambda v: v
    else:
        if cls is date:
            return _build_if_not_yet(cls, lambda v: dt_parse(v).date())
        elif cls is datetime:
            return _build_if_not_yet(cls, lambda v: dt_parse(v))
        else:
            return _build_if_not_yet(cls, cls)


def type_list_of(cls):
    return quict(default=attr.Factory(list),
                 converter=create_list_converter(cls))


def type_dict_of(cls):
    return quict(default=attr.Factory(dict),
                 converter=create_dict_converter(cls))


def type_required(cls=None):
    return quict(type=cls, converter=create_converter(cls))


def type_optional(cls=None, default=None):
    '''
    >>> import attr
    >>> @attr.s
    ... class Y(object):
    ...    i = attr.ib(type=int)
    ...
    >>> @attr.s
    ... class Z(object):
    ...    x = attr.ib(**type_required(float))
    ...    y = attr.ib(**type_optional(Y))
    ...
    >>> create_converter(Z)({'x': '3.5'})
    Z(x=3.5, y=None)
    >>> create_converter(Z)({'x': '3', 'y': { 'i': 5}})
    Z(x=3.0, y=Y(i=5))
    >>> create_converter(Z)({'x': '3', 'y': Y(5)})
    Z(x=3.0, y=Y(i=5))
    '''
    return quict(
        type=cls,
        default=attr.Factory(lambda : default),
        converter=attr.converters.optional(create_converter(cls))
    )


def to_json(o):
    return json_encode(attr.asdict(o))


def from_json(cls, s):
    return create_converter(cls)(json_decode(s))


class GlobalRef(Stringable, EnsureIt, StrKeyMixin):
    '''
    >>> ref = GlobalRef('hashstore.utils:GlobalRef')
    >>> ref
    GlobalRef('hashstore.utils:GlobalRef')
    >>> ref.get_instance().__name__
    'GlobalRef'
    >>> ref.module_only()
    False
    >>> ref.get_module().__name__
    'hashstore.utils'
    >>> GlobalRef(GlobalRef)
    GlobalRef('hashstore.utils:GlobalRef')
    >>> GlobalRef(GlobalRef).get_instance()
    <class 'hashstore.utils.GlobalRef'>
    >>> uref = GlobalRef('hashstore.utils:')
    >>> uref.module_only()
    True
    >>> uref.get_module().__name__
    'hashstore.utils'
    >>> uref = GlobalRef('hashstore.utils')
    >>> uref.module_only()
    True
    >>> uref.get_module().__name__
    'hashstore.utils'
    '''
    def __init__(self, s: Any)->None:
        if inspect.ismodule(s):
            self.module,self.name = s.__name__,''
        elif inspect.isclass(s) or inspect.isfunction(s):
            self.module, self.name = s.__module__, s.__name__
        else:
            split = s.split(':')
            if len(split) == 1:
                if not(split[0]):
                    raise AssertionError(f'is {repr(s)} empty?')
                split.append('')
            elif len(split) != 2:
                raise AssertionError(f"too many ':' in: {repr(s)}")
            self.module, self.name = split

    def __str__(self):
        return '%s:%s' %(self.module, self.name)

    def get_module(self)->ModuleType:
        return __import__(self.module, fromlist=['', ])

    def module_only(self)->bool:
        return not(self.name)

    def get_instance(self)->Any:
        if self.module_only():
            raise AssertionError(f'{repr(self)}.get_module() only')
        return getattr(self.get_module(), self.name)




