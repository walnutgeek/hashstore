from collections import Mapping
import functools
import six
import os
import json
import sys
import uuid
import abc


def quict(**kwargs):
    r = {}
    r.update(**kwargs)
    return r


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
    from hashstore.py2 import _raise_it
else:
    def _raise_it(etype, new_exception, traceback):
        raise new_exception.with_traceback(traceback)


def reraise_with_msg(msg, exception=None):
    if exception is None:
        exception = sys.exc_info()[1]
    etype = type(exception)
    new_exception = etype(exception_message(exception) + '\n'+ msg)
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
    ensure_bytes = lambda s: s if isinstance(s, bytes) else str(s)
    ensure_unicode = lambda s: s if isinstance(s, unicode) else unicode(s)
    ensure_string = ensure_bytes
else:  # python3
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
    serialize in json
    '''
    pass

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