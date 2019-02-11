import enum


def failback(fn, default):
    '''
    >>> divmod(3,2)
    (1, 1)
    >>> divmod(3,0)
    Traceback (most recent call last):
    ...
    ZeroDivisionError: integer division or modulo by zero
    >>> divmod_nofail = failback(divmod,(0, 0))
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


def _camel2var(c):
    return c if c.islower() else '_' + c.lower()


def from_camel_case_to_underscores(s:str)->str:
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
    >>> normalize_url('http://example.com')
    'http://example.com/'
    >>> normalize_url('example.com')
    'http://example.com/'
    >>> normalize_url('example.com:8976')
    'http://example.com:8976/'
    >>> normalize_url('https://example.com:8976')
    'https://example.com:8976/'
    >>> normalize_url('https://example.com:8976/')
    'https://example.com:8976/'

    '''
    if url[-1:] != '/':
        url += '/'
    if not(url[:7] == 'http://' or url[:8] == 'https://'):
        url = 'http://' + url
    return url





