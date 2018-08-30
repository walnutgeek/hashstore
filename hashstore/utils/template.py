from . import (adjust_for_json, lazy_factory, GlobalRef, Stringable,
                             StrKeyMixin, EnsureIt, identity, _GLOBAL_REF)
from datetime import date, datetime
from typing import (Any, Union, Optional)
from dateutil.parser import parse as dt_parse
from enum import IntEnum
import re


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
        if self.cls == Any:
            self._from_json = identity
        elif self.cls is date:
            self._from_json = lazy_factory(
                self.cls, lambda v: dt_parse(v).date())
        elif self.cls is datetime:
            self._from_json = lazy_factory(
                self.cls, lambda v: dt_parse(v))
        else:
            self._from_json = lazy_factory(self.cls, self.cls)

    def matches(self, v):
        return self.cls == Any or isinstance(v, self.cls)

    def convert(self, v: Any, direction: Conversion)->Any:
        if direction == Conversion.TO_OBJECT:
            return self._from_json(v)
        else:
            return adjust_for_json(v, v)

    def __str__(self):
        if self.cls.__module__ == 'builtins':
            return self.cls.__name__
        elif self.cls == Any:
            return 'typing:Any'
        return str(GlobalRef(self.cls))

class Template(type):
    """
    Todos:
      [x] test POC
      [ ] make CRef to parse and display template classes properly
      [ ] control __name__ and __qualname__

    >>>
    """
    def __init__(cls, name, bases, dct):
        if _GLOBAL_REF not in dct:
            cls.__cache__ = {}


    def __getitem__(self, item):
        item_cref = ClassRef.ensure_it(item)
        k = str(item_cref)
        if k in self.__cache__:
            return self.__cache__[k]
        class Klass(self):
            __item_cref__ = item_cref
            __global_ref__ = GlobalRef(self, str(item_cref))
        self.__cache__[k] = Klass
        return Klass

