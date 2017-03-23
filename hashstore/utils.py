
from collections import Mapping
import six
import os
import json
import sys


def quict(**kwargs):
    r = {}
    r.update(**kwargs)
    return r

to_binary = lambda s: s if type(s) == six.binary_type else s.encode('utf8')

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


def reraise_with_msg(msg, exception=None):
    if exception is None:
        exception = sys.exc_info()[1]
    etype = type(exception)
    new_exception = etype(exception_message(exception) + '\n'+ msg)
    traceback = sys.exc_info()[2]
    if six.PY2:
        raise etype, new_exception, traceback
    else:
        raise new_exception.with_traceback(traceback)

def ensure_directory(directory):
    if not (os.path.isdir(directory)):
        os.makedirs(directory)

none2str = lambda s: '' if s is None else s

get_if_defined = lambda o, k: getattr(o, k) if hasattr(o, k) else None

call_if_defined = lambda o, k, *args: getattr(o,k)(*args) if hasattr(o,k) else None

def create_path_resover(substitutions = {}):
    substitutions = dict(substitutions)
    for k in os.environ:
        env_key = '{env.' + k + '}'
        if env_key not in substitutions:
            substitutions[env_key] = os.environ[k]
    def path_resover(p):
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
    return path_resover

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

class Stringable:
    '''
    Marker to inform json_encoder to use `str(o)` to
    serialize in json
    '''
    pass

class Jsonable:
    '''
    Marker to inform json_encoder to use `o.to_json()` to
    serialize in json
    '''
    pass

class StringableEncoder(json.JSONEncoder):
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

