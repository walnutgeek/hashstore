import abc
from typing import (Any, Dict, List, Optional, get_type_hints, Union,
                    Set, Tuple, Callable)
from inspect import getfullargspec

from hashstore.utils.docs import DocStringTemplate
from . import (Jsonable, GlobalRef, Stringable, EnsureIt, json_decode,
               json_encode, not_zero_len, ensure_string,
               reraise_with_msg)
from .template import ClassRef, Conversion, Template
from .typings import is_optional, is_tuple, is_list, is_dict, get_args



class Typing(Stringable, EnsureIt):

    @classmethod
    def factory(cls):
        return typing_factory

    def __init__(self, val_cref, collection=False):
        self.val_cref = ClassRef.ensure_it(val_cref)
        self.collection=collection

    def is_required(self):
        return False

    def is_primitive(self)->bool:
        return not(self.collection) and self.val_cref.primitive

    def convert(self, v: Any, direction:Conversion)->Any:
        return self.val_cref.convert(v, direction)

    def default(self):
        if self.is_required():
            raise AttributeError(f'no default for {str(self)}')
        else:
            return None

    @classmethod
    def name(cls):
        return cls.__name__[:-6]

    def __str__(self):
        return f'{self.name()}[{self.val_cref}]'


class OptionalTyping(Typing):

    def validate(self, v):
        return v is None or self.val_cref.matches(v)

    def default(self):
        return None


class RequiredTyping(Typing):

    def validate(self, v):
        return self.val_cref.matches(v)

    def is_required(self):
        return self.val_cref.cls != Any


class DictTyping(Typing):

    def __init__(self, val_cref, key_cref):
        Typing.__init__(self, val_cref, collection=True)
        self.key_cref = ClassRef.ensure_it(key_cref)

    def convert(self, in_v:Any, direction:Conversion)->Dict[Any, Any]:
        return {self.key_cref.convert(k, direction):
                self.val_cref.convert(v, direction)
                for k, v in in_v.items()}

    def validate(self, v):
        return isinstance(v, dict)

    def __str__(self):
        return f'{self.name()}[{self.key_cref},{self.val_cref}]'

    def default(self):
        return {}


class ListTyping(Typing):
    def __init__(self, val_cref):
        Typing.__init__(self, val_cref, collection=True)

    def convert(self, in_v: Any, direction:Conversion)->List[Any]:
        return [self.val_cref.convert(v, direction) for v in in_v]

    def validate(self, v):
        return isinstance(v, list)

    def default(self):
        return []


class ReferenceResolver(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def flatten(self, v:Any) -> str:
        raise NotImplementedError('subclasses must override')

    @abc.abstractmethod
    def dereference(self, s:str) -> Any:
        raise NotImplementedError('subclasses must override')


class NoResolver(ReferenceResolver):

    def flatten(self, v:Any) -> str:
        return str(v)

    def dereference(self, s:str) -> Any:
        return s


class AttrEntry(EnsureIt, Stringable):
    """
    >>> AttrEntry('x:Required[hashstore.bakery:Cake]')
    AttrEntry('x:Required[hashstore.bakery:Cake]')
    >>> e = AttrEntry('x:Required[hashstore.bakery:Cake]="0"')
    >>> e.default
    Cake('0')
    >>> e
    AttrEntry('x:Required[hashstore.bakery:Cake]="0"')
    >>> AttrEntry(None)
    Traceback (most recent call last):
    ...
    AttributeError: 'NoneType' object has no attribute 'split'
    >>> AttrEntry('a')
    Traceback (most recent call last):
    ...
    ValueError: not enough values to unpack (expected 2, got 1)
    >>> AttrEntry('a:x')
    Traceback (most recent call last):
    ...
    AttributeError: Unrecognized typing: x
    >>> AttrEntry(5)
    Traceback (most recent call last):
    ...
    AttributeError: 'int' object has no attribute 'split'
    """
    def __init__(self, name, typing=None, default=None, ):
        self.default = default
        self._doc = None
        self.index = None
        default_s = None
        if typing is None:
            split = name.split('=', 1)
            if len(split) == 2:
                name, default_s = split
            name, typing = name.split(':', 1)
        self.name = name
        self.typing = typing_factory(typing)
        if default_s is not None:
            self.default = self.typing.convert(
                json_decode(default_s), Conversion.TO_OBJECT)

    def is_primitive(self)->bool:
        return self.typing.is_primitive()

    def inflate(self, v:Any, resover:ReferenceResolver)->Any:
        if self.is_primitive() or not(isinstance(v, str)):
            return v
        else:
            return resover.dereference(v)

    def flatten(self, v:Any, resover:ReferenceResolver)->Any:
        if self.is_primitive() or isinstance(v, str):
            return v
        else:
            return resover.flatten(v)

    def required(self):
        try:
            self.convert(None, Conversion.TO_OBJECT)
            return False
        except AttributeError:
            return True

    def convert(self, v: Any, direction: Conversion)->Any:
        try:
            if Conversion.TO_OBJECT == direction:
                if v is None:
                    if self.default is not None:
                        return self.default
                    else:
                        return self.typing.default()
                else:
                    return self.typing.convert(v, Conversion.TO_OBJECT)
            else:
                if v is None:
                    return None
                else:
                    return self.typing.convert(v, Conversion.TO_JSON)
        except:
            reraise_with_msg(f'error in {self}')

    def validate(self, v:Any)->bool:
        return self.typing.validate(v)

    def __str__(self):
        def_s = ''
        if self.default is not None:
            v = json_encode(self.typing.convert(self.default, Conversion.TO_JSON))
            def_s = f'={v}'
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
    >>> Typing.ensure_it('Dict[datetime:datetime,str]')
    DictTyping('Dict[datetime:datetime,str]')
    """

    if isinstance(o, Typing):
        return o
    if isinstance(o, str):
        if o[-1] == ']':
            typing_name, args_s = o[:-1].split('[', 1)
            args = args_s.split(',')
            typing_cls = globals()[typing_name + 'Typing']
            if issubclass(typing_cls, DictTyping):
                return typing_cls(args[1], args[0])
            elif len(args) != 1:
                raise AssertionError(f'len({args}) should be 1. input:{o}')
            else:
                return typing_cls(args[0])
        raise AttributeError(f'Unrecognized typing: {o}')
    else:
        args = get_args(o, [])
        if len(args) == 0:
            return RequiredTyping(o)
        elif is_optional(o,args):
            return OptionalTyping(args[0])
        elif is_list(o,args):
            return ListTyping(args[0])
        elif is_dict(o,args):
            return DictTyping(args[1], args[0])
        else:
            raise AssertionError(
                f'Unknown annotation: {o}')


class DictLike:
    def __init__(self, o):
        self.o = o

    def __contains__(self, item):
        return hasattr(self.o, item)

    def __getitem__(self, item):
        return getattr(self.o, item)


SINGLE_RETURN_VALUE = '_'


class Mold(Jsonable):

    def __init__(self, o=None):
        self.keys: List[str] = []
        self.cls: Optional[type] = None
        self.attrs: Dict[str, AttrEntry] = {}
        self._doc = '{Attributes}\n'
        if o is not None:
            if isinstance(o, list):
                for ae in map(AttrEntry.ensure_it, o):
                    self.add_entry(ae)
            elif isinstance(o, dict):
                self.add_hints(o)
            else:
                self.add_hints(get_type_hints(o))
                if isinstance(o, type):
                    self.cls = o
                    self.set_attr_docs(o.__doc__, "Attributes")

    def set_attr_docs(self, docstring, section_name):
        self._doc = DocStringTemplate(docstring, {section_name})
        groups = self._doc.var_groups
        if section_name in groups:
            attr_docs = groups[section_name]
            for k in attr_docs.keys():
                self.attrs[k]._doc = str(attr_docs[k].content)

    @classmethod
    def factory(cls):
        def make(o):
            for name in ('__mold__', 'mold'):
                if hasattr(o, name):
                    possible_mold = getattr(o, name)
                    if isinstance(possible_mold, cls):
                        return possible_mold
            return cls(o)
        return make

    def add_hints(self, hints):
        for var_name, var_cls in hints.items():
            self.add_entry(AttrEntry(var_name, var_cls))

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
        if entry.index is not None:
            raise AssertionError(f'Same entry reused: {entry}')
        entry.index = len(self.attrs)
        self.keys.append(entry.name)
        self.attrs[entry.name] = entry

    def inflate(self,
                flaten_vars: Dict[str,Any],
                resolver:ReferenceResolver) -> Dict[str,Any]:
        return {k: self.attrs[k].inflate(v, resolver)
                for k, v in flaten_vars.items()}

    def flatten(self,
                inflated_vars: Dict[str,Any],
                resolver: ReferenceResolver) -> Dict[str,Any]:
        return {
            k: self.attrs[k].flatten(v, resolver)
            for k, v in inflated_vars.items()}

    def to_json(self):
        return [str(ae) for ae in self.attrs.values()]

    def check_overlaps(self, values):
        missing = set(
            ae.name for ae in self.attrs.values()
            if ae.typing.is_required() and ae.default is None
        ) - values.keys()
        if len(missing) > 0:
            raise AttributeError(f'Required : {missing}')
        not_known = set(values.keys()) - set(self.attrs.keys())
        if len(not_known) > 0:
            raise AttributeError(f'Not known: {not_known}')

    def build_val_dict(self, json_values):
        self.check_overlaps(json_values)
        return self.mold_it(json_values, Conversion.TO_OBJECT)

    def mold_it(
            self,
            in_data: Union[List[Any],Dict[str,Any],DictLike],
            direction: Conversion
    ) -> Dict[str,Any]:
        return dict(zip(self.keys,
                        self.mold_to_list(in_data, direction)))

    def mold_to_list(self,
                     in_data: Union[List[Any],Dict[str,Any],DictLike],
                     direction: Conversion) -> List[Any]:
        if not (isinstance(in_data, list)):
            in_data = [in_data[k] if k in in_data else None
                       for k in (self.keys)]
        if len(self.keys) != len(in_data):
            raise AttributeError(f'arrays has to match in size:'
                                 f' {self.keys} {in_data}')
        return[
            self.attrs[self.keys[i]].convert(in_data[i], direction)
            for i in range(len(self.keys))
        ]

    def set_attrs(self, values, target):
        for k, v in self.build_val_dict(values).items():
            setattr(target, k, v)

    def pull_attrs(self, from_obj:Any)->Dict[str,Any]:
        return { k: getattr(from_obj, k)
                 for k in self.keys if hasattr(from_obj, k) }

    def wrap_input(self, v):
        v_dct = self.mold_it(v, Conversion.TO_OBJECT)
        if self.cls is not None:
            return self.cls(v_dct)
        return v_dct


    def output_json(self, v):
        if self.is_single_return():
            result = {SINGLE_RETURN_VALUE: v}
        else:
            result = DictLike(v)
        return self.mold_it(result, Conversion.TO_JSON)

    def is_single_return(self)->bool:
        return self.keys == [SINGLE_RETURN_VALUE]

    def is_empty(self)->bool:
        return len(self.keys) == 0


def extract_molds_from_function(fn:Callable[...,Any]
                                )->Tuple[Mold,Mold]:
    """
    Args:
        fn: function inspected

    Returns:
        in_mold: `Mold` of function input
        out_mold: `Mold` of function output

    >>> def a(i:int)->None:
    ...     pass
    ...
    >>> in_a, out_a = extract_molds_from_function(a)
    >>> out_a.is_empty()
    True
    >>> out_a.is_single_return()
    False
    >>>
    >>> def b(i:int)->str:
    ...     return f'i={i}'
    ...
    >>> in_b, out_b = extract_molds_from_function(b)
    >>> out_b.is_empty()
    False
    >>> out_b.is_single_return()
    True
    >>>
    """
    dst = DocStringTemplate(fn.__doc__, {"Args", "Returns"})

    annotations = dict(get_type_hints(fn))
    return_type = annotations['return']
    del annotations['return']
    in_mold = Mold(annotations)
    in_mold.set_defaults(in_mold.get_defaults_from_fn(fn))
    out_mold = Mold()

    if return_type != type(None):

        if is_tuple(return_type):
            args = get_args(return_type)
            keys = [f"v{i}" for i in range(len(args))]
            if "Returns" in dst.var_groups:
                for i,k in enumerate(dst.var_groups["Returns"].keys()):
                    keys[i] = k
            out_mold.add_hints(dict(zip(keys, args)))
        else:
            out_hints = get_type_hints(return_type)
            if len(out_hints) > 0:
                out_mold.add_hints(out_hints)
            else:
                ae = AttrEntry(SINGLE_RETURN_VALUE, return_type)
                out_mold.add_entry(ae)
    return in_mold, out_mold


class AnnotationsProcessor(type):
    def __init__(cls, name, bases, dct):
        mold = Mold(cls)
        mold.set_defaults(mold.get_defaults_from_cls(cls))
        cls.__mold__ = mold


def combine_vars(vars:Optional[Dict[str,Any]],
                 kwargs:Dict[str,Any]
                 )->Dict[str,Any]:
    if vars is None:
        vars = {}
    vars.update(kwargs)
    return vars

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
    >>> from datetime import date, datetime
    >>> class A(SmAttr):
    ...     x:int
    ...     z:bool
    ...
    >>> A.__mold__.attrs #doctest: +NORMALIZE_WHITESPACE
    {'x': AttrEntry('x:Required[int]'),
    'z': AttrEntry('z:Required[bool]')}
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
    {'x': AttrEntry('x:Required[int]'),
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
        _vals_ = combine_vars(_vals_, kwargs)
        values = {k: v for k, v in _vals_.items() if v is not None}
        type(self).__mold__.set_attrs(values, self)

    def to_json(self) -> Dict[str, Any]:
        cls = type(self)
        if hasattr(cls, '__to_json__'):
            mold = Mold.ensure_it(cls.__to_json__) #type: ignore
        else:
            mold = cls.__mold__
        return mold.mold_it(DictLike(self), Conversion.TO_JSON)



class Row:
    def _row_id(self)->int:
        raise AssertionError('need to be implemented')


def get_row_id(row_id:Union[int, Row])->int:
    if isinstance(row_id, int):
        return row_id
    return row_id._row_id()


class MoldedTable(metaclass=Template):
    """
    >>> from datetime import date, datetime
    >>> class A(SmAttr):
    ...     i:int
    ...     s:str = 'xyz'
    ...     d:Optional[datetime]
    ...     z:List[datetime]
    ...     y:Dict[str,str]
    ...
    >>> t = MoldedTable[A]()
    >>> str(t)
    '#{"columns": ["i", "s", "d", "z", "y"]}\\n'
    >>> t.add_row(A(i=5,s='abc'))
    0
    >>> str(t)
    '#{"columns": ["i", "s", "d", "z", "y"]}\\n[5, "abc", null, [], {}]\\n'
    >>> t.find_invalid_keys(t.add_row([7,None,'2018-08-10',None,None]))
    []
    >>> t.add_row([])
    Traceback (most recent call last):
    ...
    AttributeError: arrays has to match in size: ['i', 's', 'd', 'z', 'y'] []
    >>> t.add_row([None,None,None,None,None])
    Traceback (most recent call last):
    ...
    AttributeError: no default for Required[int]
    error in i:Required[int]
    >>> str(t)
    '#{"columns": ["i", "s", "d", "z", "y"]}\\n[5, "abc", null, [], {}]\\n[7, "xyz", "2018-08-10T00:00:00", [], {}]\\n'
    >>> t = MoldedTable(str(t),A)
    >>> str(t)
    '#{"columns": ["i", "s", "d", "z", "y"]}\\n[5, "abc", null, [], {}]\\n[7, "xyz", "2018-08-10T00:00:00", [], {}]\\n'
    >>> MoldedTable[A]('a')
    Traceback (most recent call last):
    ...
    AttributeError: header should start with "#": a
    >>> t.find_invalid_rows()
    []
    >>> r=t.new_row()
    >>> t.find_invalid_rows()
    [2]
    >>> t.find_invalid_keys(r)
    ['i', 's', 'z', 'y']
    >>> t.find_invalid_keys(2)
    ['i', 's', 'z', 'y']
    >>> r.i
    >>> r.i=77
    >>> r.i
    77
    >>> r[3]=[datetime(2018,8,1),]
    >>> t.find_invalid_keys(r)
    ['s', 'y']
    >>> r['y']={}
    >>> r['y']
    {}
    >>> r[4]
    {}
    >>> t.find_invalid_rows()
    [2]
    >>> str(t)
    '#{"columns": ["i", "s", "d", "z", "y"]}\\n[5, "abc", null, [], {}]\\n[7, "xyz", "2018-08-10T00:00:00", [], {}]\\n[77, null, null, ["2018-08-01T00:00:00"], {}]\\n'
    >>> len(t)
    3
    >>> str(MoldedTable[A](str(t)))
    '#{"columns": ["i", "s", "d", "z", "y"]}\\n[5, "abc", null, [], {}]\\n[7, "xyz", "2018-08-10T00:00:00", [], {}]\\n[77, "xyz", null, ["2018-08-01T00:00:00"], {}]\\n'
    >>> r['s']='zyx'
    >>> str(MoldedTable[A](str(t)))
    '#{"columns": ["i", "s", "d", "z", "y"]}\\n[5, "abc", null, [], {}]\\n[7, "xyz", "2018-08-10T00:00:00", [], {}]\\n[77, "zyx", null, ["2018-08-01T00:00:00"], {}]\\n'
    """

    def __init__(self, s:Union[str,bytes,None]=None, mold:Any = None)->None:
        if mold is not None:
            self.mold = Mold.ensure_it(mold)
        else:
            self.mold = Mold.ensure_it(type(self).__item_cref__.cls) #type: ignore
        self.data:List[List[Any]] = []
        if s is not None:
            s = ensure_string(s)
            lines=filter(not_zero_len, (
                s.strip() for s in s.split('\n')))
            header_line = next(lines)
            if header_line[0] != '#':
                raise AttributeError(f'header should start with "#":'
                                     f' {header_line}')
            header = json_decode(header_line[1:])
            cols = tuple(header["columns"])
            #TODO support: [ int, bool, str, float, date, datetime, object ]
            mold_cols = tuple(self.mold.keys)
            if mold_cols != cols:
                raise AttributeError(f' mismatch: {cols} {mold_cols}')
            for l in lines:
                self.add_row(json_decode(l))

    def add_row(self, row=None):
        if not(isinstance(row, (list,dict))):
            row = DictLike(row)
        row = self.mold.mold_to_list(row, Conversion.TO_OBJECT)
        row_id = len(self.data)
        self.data.append(row)
        return row_id

    def __len__(self):
        return len(self.data)

    def __getitem__(self, row_id:int) -> Row:
        mold=self.mold
        row = self.data[row_id]
        class _MoldedRow(Row):
            def _row_id(self):
                return row_id

            def __getattr__(self, key):
                return row[mold.attrs[key].index]

            def __setattr__(self, key, value):
                row[mold.attrs[key].index] = value

            def __getitem__(self, item):
                if isinstance(item, str):
                    return self.__getattr__(item)
                else:
                    return row[item]

            def __setitem__(self, key, value):
                if isinstance(key, str):
                    self.__setattr__(key, value)
                else:
                    row[key] = value

        return _MoldedRow()

    def find_invalid_keys(self, row_id:Union[int, Row])-> List[str]:
        row_id = get_row_id(row_id)
        invalid_keys = []
        for ae in self.mold.attrs.values():
            if not (ae.validate(self.data[row_id][ae.index])):
                invalid_keys.append(ae.name)
        return invalid_keys

    def find_invalid_rows(self) -> List[int]:
        return [row_id for row_id in range(len(self.data))
                if len(self.find_invalid_keys(row_id)) > 0]

    def new_row(self) -> Row:
        row_id = len(self.data)
        self.data.append([None for _ in self.mold.keys])
        return self[row_id]

    def __str__(self):
        def gen():
            yield '#' + json_encode({'columns': self.mold.keys})
            for row in self.data:
                yield json_encode(
                    self.mold.mold_to_list(row, Conversion.TO_JSON))
            yield ''
        return '\n'.join(gen())


class JsonWrap(SmAttr):
    classRef:GlobalRef
    json:Optional[Any]

    def unwrap(self):
        return self.classRef.get_instance()(self.json)

    @classmethod
    def wrap(cls, o):
        if isinstance(o, Jsonable):
            return cls({
                    "classRef": GlobalRef(type(o)),
                    "json": o.to_json()
            })
        raise AttributeError(f"Not jsonable: {o}")

