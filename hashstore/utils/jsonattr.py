import attr
import collections
from hashstore.utils import EnsureIt, quict, json_encode, json_decode


def create_converter(cls):
    '''
    >>> import attr
    >>> class X(EnsureIt):
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

    :return: converter for particular type
    '''
    if hasattr(cls, '__attrs_attrs__'):
        def val_converter(v):
            if isinstance(v, collections.Mapping):
                return cls(**v)
            elif isinstance(v, collections.Sequence):
                return [val_converter(e) for e in v]
            return v
        return val_converter
    elif issubclass(cls, EnsureIt):
        return cls.ensure_it
    elif cls is not None:
        return cls
    else:
        return lambda x: x


def type_list_of(cls):
    return quict(default=attr.Factory(list), converter=create_converter(cls))


def type_required(cls=None):
    return quict(type=cls, converter=create_converter(cls))


def type_optional(cls, default=None):
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

