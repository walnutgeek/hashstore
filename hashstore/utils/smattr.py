from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, NamedTuple

from hashstore.utils import quict, adjust_for_json, Jsonable, \
    _build_if_not_yet, GlobalRef
from dateutil.parser import parse as dt_parse


def get_args(cls, default=None):
    if hasattr(cls, '__args__'):
        return cls.__args__
    return default


def get_annotations(cls, default=None):
    if hasattr(cls, '__annotations__'):
        return cls.__annotations__
    return default


class Modifier(Enum):
    OPTIONAL=quict(detect=lambda cls,args: cls == Optional[args[0]],
                   new_v=lambda ae, in_v, direction: ae.val_type.json(
                       in_v,direction),
                   default=lambda: None, idx=[0,None])
    LIST=quict(detect=lambda cls,args: cls == List[args[0]],
               new_v=lambda ae, in_v, direction: [
                   ae.val_type.json(v,direction) for v in in_v],
               default=lambda:[], idx=[0,None])
    DICT=quict(detect=lambda cls,args: cls == Dict[args[0],args[1]],
               new_v=lambda ae, in_v, direction: {
                   ae.key_type.json(k,direction): ae.val_type.from_json(v)
                   for k, v in in_v.items()},
               default=lambda: {}, idx=[1,0])
    REQUIRED=quict(new_v=lambda ae, in_v, direction: ae.val_type.json(
                       in_v,direction))

    @classmethod
    def detect(cls, detect_it):
        """
        :param detect_it:
        :return: modifier, value_class, key_class
        """
        args = get_args(detect_it)
        if args is None or len(args) == 0:
            return (cls.REQUIRED , detect_it, None )
        for mod in cls: # pragma: no branch
            if mod.value['detect'](detect_it, args):
                val_cls, key_cls = [ None if i is None else args[i]
                                     for i in mod.value['idx']]
                return (mod, val_cls, key_cls)

    def __repr__(self):
        return f'{self.__class__.__name__}:{self.name}'


class AttrType:
    def __init__(self, cls:type)->None:
        self.cls = cls
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

    def __repr__(self):
        return f'AttrType(cls={self.cls})'


class AttrEntry(NamedTuple):
    name:str
    modifier:Modifier
    val_type:AttrType
    key_type:Optional[AttrType]

    @classmethod
    def build(cls, var_name, annotation_cls):
        modifier, val_cls, key_cls = Modifier.detect(annotation_cls)
        val_type = AttrType(val_cls)
        key_type = None if key_cls is None else AttrType(key_cls)
        return cls(var_name, modifier, val_type, key_type)

    def from_json(self, v):
        if v is None:
            return self.modifier.value['default']()
        else:
            return self.modifier.value['new_v'](self, v, True)

    def to_json(self, o):
        v = getattr(o, self.name)
        return None if v is None else self.modifier.value['new_v'](
            self, v, False)


class AnnotationsProcessor(type):
    def __init__(cls, name, bases, dct):
        cls.__smattr__ = {var_name: AttrEntry.build(var_name, var_cls)
                          for var_name, var_cls in
                          get_annotations(cls,{}).items()}


class SmAttr(Jsonable,metaclass=AnnotationsProcessor):
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
    >>> A.__smattr__ #doctest: +NORMALIZE_WHITESPACE
    {'x': AttrEntry(name='x', modifier=Modifier:REQUIRED,
          val_type=AttrType(cls=<class 'int'>),
          key_type=None),
     'z': AttrEntry(name='z', modifier=Modifier:REQUIRED,
          val_type=AttrType(cls=<class 'bool'>),
          key_type=None)}
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
    >>> class B(SmAttr):
    ...     x: Cake
    ...     aa: List[A2]
    ...     dt: Dict[datetime, A]
    ...

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

    """

    def __init__(self, values:Optional[Dict[str, Any]] = None)->None:
        if values is None:
            values = {}
        else:
            values = {k:v for k,v in values.items() if v is not None}
        # sort out error conditions
        missing = set(
            ae.name for ae in self.__smattr__.values()
            if ae.modifier == Modifier.REQUIRED
        ) - values.keys()
        if len(missing) > 0 :
            raise AttributeError(f'Required : {missing}')
        not_known = set(values.keys()) - set(self.__smattr__.keys())
        if len(not_known) > 0 :
            raise AttributeError(f'Not known: {not_known}')
        # populate attributes
        for attr_name, attr_entry in self.__smattr__.items():
            v = values.get(attr_name, None)
            setattr(self, attr_name, attr_entry.from_json(v))

    def to_json(self):
        return {
            attr_name: attr_entry.to_json(self)
            for attr_name, attr_entry in self.__smattr__.items()
        }




class Implementation(SmAttr):
    classRef:GlobalRef
    config:Optional[Any]

    def create(self):
        return self.classRef.get_instance()(self.config)
