import re
from datetime import date, datetime
from typing import (Any, Dict, List, Optional, get_type_hints, Union)
from inspect import getfullargspec
from hashstore.utils import (adjust_for_json, Jsonable,
                             _build_if_not_yet, GlobalRef, Stringable,
                             StrKeyMixin, EnsureIt, json_decode,
                             json_encode)
from dateutil.parser import parse as dt_parse


def get_args(cls, default=None):
    if hasattr(cls, '__args__'):
        return cls.__args__
    return default


class ClassRef(Stringable,StrKeyMixin,EnsureIt):
    """
    >>> crint=ClassRef('builtins:int')
    >>> str(crint)
    'builtins:int'
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
        raise AssertionError(f'no default for {type(self)}')

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



class AttrEntry(EnsureIt,Stringable):
    """
    >>> AttrEntry('x:Required[hashstore.bakery:Cake]')
    AttrEntry('x:Required[hashstore.bakery:Cake]')
    >>> e = AttrEntry('x:Required[hashstore.bakery:Cake]="0"')
    >>> e.default
    Cake('0')
    >>> e
    AttrEntry('x:Required[hashstore.bakery:Cake]="0"')
    """
    def __init__(self, name, typing=None, default=None):
        self.default = None
        default_s = None
        if typing is None:
            split = name.split('=', 1)
            if len(split) == 2:
                name, default_s = split
            name, typing = name.split(':', 1)
        else:
            self.default = default
        self.name = name
        self.typing = typing_factory(typing)
        if default_s is not None:
            self.default = self.typing.convert(
                json_decode(default_s), True)

    def from_json(self, v):
        if v is None:
            if self.default is not None:
                return self.default
            else:
                return self.typing.default()
        else:
            return self.typing.convert(v, True)

    def to_json(self, o):
        v = getattr(o, self.name)
        return None if v is None else self.typing.convert(v, False)

    def __str__(self):
        def_s = ''
        if self.default is not None:
            v = json_encode(self.typing.convert(self.default, False))
            def_s =f'={v}'
        return f'{self.name}:{self.typing}{def_s}'


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
    if isinstance(o, AttrEntry):
        return o.typing
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


class Mold(Jsonable):

    def __init__(self, o=None):
        self.attrs: Dict[str, AttrEntry] = {}
        if o is not None:
            if isinstance(o, dict):
                if len(o) == 1 and '__attrs__' in o :
                    json_attrs = o['__attrs__']
                    if isinstance(json_attrs, list):
                        try:
                            self.attrs.update({
                                ae.name: ae
                                for ae in map(AttrEntry, json_attrs)
                            })
                            return
                        except:
                            pass
                self.add_hints(o)
            else:
                self.add_hints(get_type_hints(o))

    def add_hints(self, hints):
        self.attrs.update({
            var_name: AttrEntry(var_name, var_cls)
            for var_name, var_cls in hints.items()
        })

    def set_defaults(self, defaults):
        for k in self.attrs:
            if k in defaults:
                def_v = defaults[k]
                if def_v is not None:
                    self.attrs[k].default = def_v


    def get_defaults_from_cls(self, cls):
        return {
            attr_name: getattr(cls, attr_name)
            for attr_name in self.attrs if hasattr(cls, attr_name)}

    def get_defaults_from_fn(self, fn):
        names, _, _, defaults = getfullargspec(fn)[:4]
        if defaults is None:
            defaults = []
        def_offset = len(names) - len(defaults)
        return {k: v
                for k,v in zip(names[def_offset:],defaults)
                if k in self.attrs}

    def add_entry(self, entry:AttrEntry):
        self.attrs[entry.name] = entry

    def to_json(self):
        return {"__attrs__": [str(ae) for k, ae in self.attrs.items()]}

    # def augment_with_defaults(self, values):
    #     for k, ae in self.attrs.items():
    #         if ae.default is not None and k not in values:
    #             values[k] = ae.default

    def check_overlaps(self, values):
        # sort out error conditions
        missing = set(
            ae.name for ae in self.attrs.values()
            if isinstance(ae.typing, RequiredTyping)
            and ae.default is None
        ) - values.keys()
        if len(missing) > 0:
            raise AttributeError(f'Required : {missing}')
        not_known = set(values.keys()) - set(self.attrs.keys())
        if len(not_known) > 0:
            raise AttributeError(f'Not known: {not_known}')

    def populate_attrs(self, values, target):
        # populate attributes
        for attr_name, attr_entry in self.attrs.items():
            v = values.get(attr_name, None)
            setattr(target, attr_name, attr_entry.from_json(v))

    def mold_it(self, values, it):
        # self.augment_with_defaults(values)
        self.check_overlaps(values)
        self.populate_attrs(values, it)


class AnnotationsProcessor(type):
    def __init__(cls, name, bases, dct):
        mold = Mold(cls)
        mold.set_defaults(mold.get_defaults_from_cls(cls))
        cls.__mold__ = mold


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
    >>> a2m = A2(x=777)
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

    def __init__(self, _vals_:Optional[Dict[str, Any]] = None,
                 **kwargs) ->None:
        if _vals_ is None:
            _vals_ = dict(kwargs)
        values = {k: v for k, v in _vals_.items() if v is not None}
        type(self).__mold__.mold_it(values, self)

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
