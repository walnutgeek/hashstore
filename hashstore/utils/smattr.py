import re
from datetime import date, datetime
from typing import (Any, Dict, List, Optional, get_type_hints, Union)

from hashstore.utils import (adjust_for_json, Jsonable,
    _build_if_not_yet, GlobalRef, Stringable, StrKeyMixin, EnsureIt)
from dateutil.parser import parse as dt_parse


def get_args(cls, default=None):
    if hasattr(cls, '__args__'):
        return cls.__args__
    return default


class ClassRef(Stringable,StrKeyMixin,EnsureIt):
    """
    >>> crint=ClassRef('builtins:int')
    >>> crint.to_json(5)
    5
    >>> crint.from_json('3')
    3
    >>> crint = ClassRef(int)
    >>> crint.to_json(5)
    5
    >>> crint.from_json('3')
    3
    """
    def __init__(self, cls_or_str:Union[type,str])->None:
        if isinstance(cls_or_str,str):
            cls_or_str = GlobalRef(cls_or_str).get_instance()
        self.cls = cls_or_str
        if self.cls == Any:
            self._from_json = lambda v:v
        elif self.cls is date:
            self._from_json = _build_if_not_yet(self.cls, lambda v: dt_parse(v).date())
        elif self.cls is datetime:
            self._from_json = _build_if_not_yet(self.cls, lambda v: dt_parse(v))
        else:
            self._from_json = _build_if_not_yet(self.cls, self.cls)

    def json(self, v:Any, direction:bool) -> Any:
        return self.from_json(v) if direction else self.to_json(v)

    def from_json(self, v:Any)->Any:
        return self._from_json(v)

    def to_json(self, v:Any)->Any:
        return adjust_for_json(v, v)

    def __str__(self):
        return str(GlobalRef(self.cls))


class Typing(Stringable,EnsureIt):
    @classmethod
    def factory(self):
        return typing_factory

    def __init__(self, val_cref):
        self.val_cref = ClassRef.ensure_it(val_cref)

    def convert(self, v:Any, direction:bool)->Any:
        return self.val_cref.json(v, direction)

    def default(self):
        raise AssertionError(f'no default for {self.__class__}')

    @classmethod
    def name(cls):
        return cls.__name__[:-6]

    def __str__(self):
        return f'{self.name()}[{self.val_cref}]'


class OptionalTyping(Typing):
    def default(self):
        return None


class RequiredTyping(Typing):
    pass


class DictTyping(Typing):
    def __init__(self, val_cref, key_cref):
        Typing.__init__(self, val_cref)
        self.key_cref = ClassRef.ensure_it(key_cref)

    def convert(self, in_v: Any, direction: bool) ->Dict[Any,Any]:
        return {self.key_cref.json(k,direction):
                self.val_cref.json(v,direction)
            for k,v in in_v.items()}

    def __str__(self):
        return f'{self.name()}[{self.key_cref},{self.val_cref}]'

    def default(self):
        return {}


class ListTyping(Typing):
    def convert(self, in_v:Any, direction:bool)->List[Any]:
        return [self.val_cref.json(v,direction) for v in in_v]

    def default(self):
        return []

def typing_factory(o):
    """
    >>> req = typing_factory('Required[hashstore.bakery:Cake]')
    >>> req
    RequiredTyping('Required[hashstore.bakery:Cake]')
    >>> Typing.ensure_it(str(req))
    RequiredTyping('Required[hashstore.bakery:Cake]')
    >>> typing_factory(req)
    RequiredTyping('Required[hashstore.bakery:Cake]')
    >>> Typing.ensure_it('Dict[datetime:datetime,builtins:str]')
    DictTyping('Dict[datetime:datetime,builtins:str]')
    """

    if isinstance(o, Typing):
        return o
    if isinstance(o, str):
        m = re.match(r'^(\w+)\[([\w\.\:]+),?([\w\.\:]*)\]$', o)
        if m is None:
            raise AssertionError(f'Unregoinzed typing: {o}')
        typing_name, *args = m.groups()
        typing_cls = globals()[typing_name + 'Typing']
        if issubclass(typing_cls, DictTyping) :
            return typing_cls(args[1], args[0])
        elif args[1] != '':
            raise AssertionError(f'args[1] shold be empty for: {o}')
        else:
            return typing_cls(args[0])
    else:
        args = get_args(o, [])
        if len(args) == 0:
            return RequiredTyping(o)
        elif Optional[args[0]] == o:
            return OptionalTyping(args[0])
        elif List[args[0]] == o:
            return ListTyping(args[0])
        elif Dict[args[0], args[1]] == o:
            return DictTyping(args[1], args[0])
        else:
            raise AssertionError(
                f'Unknown annotation: {o}')


class AttrEntry(EnsureIt,Stringable):
    """
    >>> AttrEntry('x:Required[hashstore.bakery:Cake]')
    AttrEntry('x:Required[hashstore.bakery:Cake]')
    """
    def __init__(self, name, typing=None):
        if typing is None:
            name, typing = name.split(':', 1)
        self.name = name
        self.typing = typing_factory(typing)

    def from_json(self, v):
        if v is None:
            return self.typing.default()
        else:
            return self.typing.convert(v, True)

    def to_json(self, o):
        v = getattr(o, self.name)
        return None if v is None else self.typing.convert(v, False)

    def __str__(self):
        return f'{self.name}:{self.typing}'


class Mold(object):
    def __init__(self, cls):
        self.attrs: Dict[str,AttrEntry] = {
            var_name: AttrEntry(var_name, var_cls)
            for var_name, var_cls in get_type_hints(cls).items()
        }

class AnnotationsProcessor(type):
    def __init__(cls, name, bases, dct):
        cls.__mold__ = Mold(cls)




class SmAttr(Jsonable, metaclass=AnnotationsProcessor):
    """
    Mixin - supports annotations:
      a:X
      a:List[X]
      a:Dict[K,V]
      a:Optional[X]
      x:datetime
      x:date
    >>> from hashstore.bakery import Cake
    >>> class A(SmAttr):
    ...     x:int
    ...     z:bool
    ...
    >>> A.__mold__.attrs #doctest: +NORMALIZE_WHITESPACE
    {'x': AttrEntry('x:Required[builtins:int]'),
    'z': AttrEntry('z:Required[builtins:bool]')}
    >>> A({"x":3})
    Traceback (most recent call last):
    ...
    AttributeError: Required : {'z'}
    >>> A({"x":3, "z":False, "q":"asdf"})
    Traceback (most recent call last):
    ...
    AttributeError: Not known: {'q'}
    >>> a = A({"x":747, "z":False})
    >>> str(a)
    '{"x": 747, "z": false}'
    >>> class A2(SmAttr):
    ...     x:int
    ...     z:Optional[date]
    ...
    >>> A2.__mold__.attrs #doctest: +NORMALIZE_WHITESPACE
    {'x': AttrEntry('x:Required[builtins:int]'),
    'z': AttrEntry('z:Optional[datetime:date]')}
    >>> class B(SmAttr):
    ...     x: Cake
    ...     aa: List[A2]
    ...     dt: Dict[datetime, A]
    ...

    >>> B.__mold__.attrs #doctest: +NORMALIZE_WHITESPACE
    {'x': AttrEntry('x:Required[hashstore.bakery:Cake]'),
    'aa': AttrEntry('aa:List[hashstore.utils.smattr:A2]'),
    'dt': AttrEntry('dt:Dict[datetime:datetime,hashstore.utils.smattr:A]')}
    >>> b = B({"x":"3X8X3D7svYk0rD1ncTDRTnJ81538A6ZdSPcJVsptDNYt" })
    >>> str(b) #doctest: +NORMALIZE_WHITESPACE
    '{"aa": [], "dt": {}, "x": "3X8X3D7svYk0rD1ncTDRTnJ81538A6ZdSPcJVsptDNYt"}'
    >>> b = B({"x":"3X8X3D7svYk0rD1ncTDRTnJ81538A6ZdSPcJVsptDNYt", "aa":[{"x":5,"z":"2018-06-30"},{"x":3}] })
    >>> str(b) #doctest: +NORMALIZE_WHITESPACE
    '{"aa": [{"x": 5, "z": "2018-06-30"}, {"x": 3, "z": null}], "dt": {},
      "x": "3X8X3D7svYk0rD1ncTDRTnJ81538A6ZdSPcJVsptDNYt"}'
    >>> a2 = A2({"x":747, "z":date(2018,6,30)})
    >>> str(a2)
    '{"x": 747, "z": "2018-06-30"}'
    >>> a2m = A2({"x":777})
    >>> str(a2m)
    '{"x": 777, "z": null}'
    >>> A2()
    Traceback (most recent call last):
    ...
    AttributeError: Required : {'x'}
    >>> b=B({"x":Cake("3X8X3D7svYk0rD1ncTDRTnJ81538A6ZdSPcJVsptDNYt"),
    ...     "aa":[a2m,{"x":3}],
    ...     'dt':{datetime(2018,6,30,16,18,27,267515) :a}})
    ...
    >>> str(b) #doctest: +NORMALIZE_WHITESPACE
    '{"aa": [{"x": 777, "z": null}, {"x": 3, "z": null}],
    "dt": {"2018-06-30T16:18:27.267515": {"x": 747, "z": false}},
    "x": "3X8X3D7svYk0rD1ncTDRTnJ81538A6ZdSPcJVsptDNYt"}'
    >>> str(B(b.to_json())) #doctest: +NORMALIZE_WHITESPACE
    '{"aa": [{"x": 777, "z": null}, {"x": 3, "z": null}],
    "dt": {"2018-06-30T16:18:27.267515": {"x": 747, "z": false}},
    "x": "3X8X3D7svYk0rD1ncTDRTnJ81538A6ZdSPcJVsptDNYt"}'
    >>> class O(SmAttr):
    ...     x:int
    ...     z:bool = False
    ...
    >>> str(O({"x":5}))
    '{"x": 5, "z": false}'
    >>> str(O({"x":5, "z": True}))
    '{"x": 5, "z": true}'
    >>> class P(O):
    ...    a: float
    ...
    >>> str(P({'x':5,'a':1.03e-5}))
    '{"a": 1.03e-05, "x": 5, "z": false}'
    """

    def __init__(self, values:Optional[Dict[str, Any]] = None)->None:
        if values is None:
            values = {}
        else:
            values = {k:v for k,v in values.items() if v is not None}
        #add defaults
        cls = type(self) # type: ignore
        smattrs:Dict[str, AttrEntry] = cls.__mold__.attrs
        for attr_name in smattrs:
            if attr_name not in values and hasattr(cls, attr_name):
                values[attr_name]=getattr(cls, attr_name)
        # sort out error conditions
        missing = set(
            ae.name for ae in smattrs.values()
            if isinstance(ae.typing, RequiredTyping)
        ) - values.keys()
        if len(missing) > 0 :
            raise AttributeError(f'Required : {missing}')
        not_known = set(values.keys()) - set(smattrs.keys())
        if len(not_known) > 0 :
            raise AttributeError(f'Not known: {not_known}')
        # populate attributes
        for attr_name, attr_entry in smattrs.items():
            v = values.get(attr_name, None)
            setattr(self, attr_name, attr_entry.from_json(v))

    def to_json(self):
        return {
            attr_name: attr_entry.to_json(self)
            for attr_name, attr_entry
            in self.__mold__.attrs.items()
        }


class Implementation(SmAttr):
    classRef:GlobalRef
    config:Optional[Any]

    def create(self):
        return self.classRef.get_instance()(self.config)
