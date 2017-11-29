from collections import Mapping
import functools
import six
import os
import json
import sys
import uuid
import abc
import enum


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


class LazyVars(Mapping):
    def __init__(self, **kw ):
        self.values = kw

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __getitem__(self, key):
        value = self.values[key]
        if callable(value):
            value = value()
            self.values[key] = value
        return value

    def __contains__(self, key):
        return key in self.values

    def __str__(self):
        return str(self.values)

    def __repr__(self):
        return "LazyVars({0})".format(repr(self.values))


def exception_message(e = None):
    if e is None:
        e = sys.exc_info()[1]
    return e.message if six.PY2 else str(e)


if six.PY2:
    from hashstore.utils.py2 import _raise_it
else:
    def _raise_it(etype, new_exception, traceback):
        raise new_exception.with_traceback(traceback)


def reraise_with_msg(msg, exception=None):
    if exception is None:
        exception = sys.exc_info()[1]
    etype = type(exception)
    try:
        new_exception = etype(exception_message(exception) + '\n'+ msg)
    except:
        new_exception = ValueError(exception_message(exception) + '\n'+ msg)
    traceback = sys.exc_info()[2]
    _raise_it(etype,new_exception,traceback)


def ensure_directory(directory):
    if not (os.path.isdir(directory)):
        os.makedirs(directory)


def none2str(s):
    return '' if s is None else s


def get_if_defined(o, k):
    return getattr(o, k) if hasattr(o, k) else None


def call_if_defined (o, k, *args):
    return getattr(o,k)(*args) if hasattr(o,k) else None


if bytes == str:  # python2
    is_str = lambda s: isinstance(s, (str, unicode))
    binary_type = str
    ensure_bytes = lambda s: s if isinstance(s, bytes) else str(s)
    ensure_unicode = lambda s: s if isinstance(s, unicode) else unicode(s,'utf-8')
    ensure_string = ensure_bytes
else:  # python3
    is_str = lambda s: isinstance(s, (str))
    binary_type = bytes
    ensure_bytes = lambda s: s if isinstance(s, bytes) else str(s).encode('utf-8')
    ensure_unicode = lambda s: s if isinstance(s, str) else str(s)
    ensure_string = lambda s: s.decode('utf-8') if isinstance(s, bytes) else s


def v2s(vars_dict, *var_keys):
    '''
    Selectively convert variable dictionary to string

    >>> v2s({'a':'b','c':'d'},'a')
    'a=b'
    >>> x=5
    >>> q=True
    >>> v2s(locals(),'x','q')
    'x=5 q=True'

    :param vars_dict:
    :param var_keys:
    :return:
    '''
    s = ' '.join(k + '={' + k + '}' for k in var_keys)
    return s.format(**vars_dict)


def create_path_resolver(substitutions = {}):
    substitutions = dict(substitutions)
    for k in os.environ:
        env_key = '{env.' + k + '}'
        if env_key not in substitutions:
            substitutions[env_key] = os.environ[k]

    def path_resolver(p):
        split =  path_split_all(p)
        updated = False
        if '~' == split[0] :
            split[0] = os.environ['HOME']
            updated = True
        for i,s in enumerate(split):
            if s in substitutions:
                split[i] = substitutions[s]
                updated = True
        return os.path.join(*split) if updated else p

    return path_resolver


def path_split_all(path, ensure_trailing_slash = None):
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
    def ensure_it(cls, o):
        if isinstance(o, cls):
            return o
        return cls(o)


@six.add_metaclass(abc.ABCMeta)
class Stringable(object):
    '''
    Marker to inform json_encoder to use `str(o)` to
    serialize in json. Also assumes that any implementing
    class has constructor that recreate same object from
    its string representation as single parameter.
    '''
    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, str(self))

Stringable.register(uuid.UUID)


class Jsonable(EnsureIt):
    '''
    Marker to inform json_encoder to use `o.to_json()` to
    serialize in json
    '''

    def __str__(self):
        return json_encoder.encode(self.to_json())

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)


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
    def __init__(self,s):
        self.json = json_decode(s)

    def to_json(self):
        return self.json


class StringableEncoder(json.JSONEncoder):
    def __init__(self):
        json.JSONEncoder.__init__(self, sort_keys=True)

    def default(self, o):
        if isinstance(o, Stringable):
            return str(o)
        if isinstance(o, Jsonable):
            return o.to_json()
        return json.JSONEncoder.default(self,o)


json_encoder = StringableEncoder()

def json_decode(text):
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


def _cacheable(fn):
    @functools.wraps(fn)
    def _(self):
        if fn.__name__ not in self.cache:
            self.cache[fn.__name__] = fn(self)
        return self.cache[fn.__name__]
    return _


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


def ensure_dict(in_dict, key_type, val_type):
    out_dict = {}
    for k in in_dict:
        val = in_dict[k]
        out_dict[key_type.ensure_it(k)] = val_type.ensure_it(val)
    return out_dict


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