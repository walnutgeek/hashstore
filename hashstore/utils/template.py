from . import (adjust_for_json, lazy_factory, GlobalRef, Stringable,
               StrKeyMixin, EnsureIt, identity, _GLOBAL_REF,
               reraise_with_msg)
from datetime import date, datetime
from typing import (Any, Union, Optional)
from dateutil.parser import parse as dt_parse
from enum import IntEnum


class Conversion(IntEnum):
    TO_JSON = -1
    TO_OBJECT = 1

class ClassRef(Stringable, StrKeyMixin, EnsureIt):
    """
    >>> crint=ClassRef('int')
    >>> str(crint)
    'int'
    >>> crint.convert(5, Conversion.TO_JSON)
    5
    >>> crint.convert('3', Conversion.TO_OBJECT)
    3
    >>> crint = ClassRef(int)
    >>> crint.convert(5, Conversion.TO_JSON)
    5
    >>> crint.convert('3', Conversion.TO_OBJECT)
    3
    >>> crint.matches(3)
    True
    >>> crint.matches('3')
    False
    >>>
    """

    def __init__(self,
                 cls_or_str: Union[type, str])->None:
        if isinstance(cls_or_str, str):
            if ':' not in cls_or_str:
                cls_or_str = 'builtins:'+cls_or_str
            cls_or_str = GlobalRef(cls_or_str).get_instance()

        self.cls = cls_or_str
        self.primitive = self.cls.__module__ == 'builtins'
        if self.cls == Any:
            self._from_json = identity
        elif self.cls is date:
            self.primitive = True
            self._from_json = lazy_factory(
                self.cls, lambda v: dt_parse(v).date())
        elif self.cls is datetime:
            self.primitive = True
            self._from_json = lazy_factory(
                self.cls, lambda v: dt_parse(v))
        elif hasattr(self.cls, '__args__'):
            self._from_json = identity
        elif isinstance(self.cls, type):
            self._from_json = lazy_factory(self.cls, self.cls)
        else:
            self._from_json = identity

    def matches(self, v):
        return self.cls == Any or isinstance(v, self.cls)

    def convert(self, v: Any, direction: Conversion)->Any:
        try:
            if direction == Conversion.TO_OBJECT:
                return self._from_json(v)
            else:
                return adjust_for_json(v, v)
        except:
            reraise_with_msg(f'{self.cls} {v}')

    def __str__(self):
        if self.cls.__module__ == 'builtins':
            return self.cls.__name__
        elif self.cls == Any:
            return 'typing:Any'
        return str(GlobalRef(self.cls))

class Template(type):
    def __init__(cls, name, bases, dct):
        if _GLOBAL_REF not in dct:
            cls.__cache__ = {}

    def __build_klass__(cls, item_cref, global_ref):
        class Klass(cls):
            __item_cref__ = item_cref
            __global_ref__ = global_ref
        return Klass

    def __getitem__(cls, item):
        item_cref = ClassRef.ensure_it(item)
        k = str(item_cref)
        if k in cls.__cache__:
            return cls.__cache__[k]
        global_ref = GlobalRef(cls, str(item_cref))
        cls.__cache__[k]=cls.__build_klass__(item_cref, global_ref)
        return cls.__cache__[k]

