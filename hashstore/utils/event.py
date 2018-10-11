import enum
import inspect
from datetime import datetime
from typing import Optional, Dict, Any, get_type_hints, Generator, \
    Callable

from hashstore.utils import jsonify
from hashstore.utils.template import Conversion
from .smattr import SmAttr, combine_vars, Mold, AttrEntry, DictLike
from . import GlobalRef, CodeEnum
import traceback


class EventState(CodeEnum):
    NEW = enum.auto()
    SUCCESS = enum.auto()
    FAIL = enum.auto()


class EdgeType(CodeEnum):
    INPUT = enum.auto()
    OUTPUT = enum.auto()
    ERROR = enum.auto()


class EventEdge(SmAttr):
    type: EdgeType
    vars: Dict[str, Any]
    dt: datetime

    @staticmethod
    def edge(type, in_vars:Dict[str,Any])->'EventEdge':
        return EventEdge(type=type,
                         vars=in_vars,
                         dt=datetime.utcnow())

    @staticmethod
    def input(_vars_:Optional[Dict[str,Any]],**kwargs:Any):
        return EventEdge.edge(EdgeType.INPUT,
                              combine_vars(_vars_,kwargs))

    @staticmethod
    def output(_vars_:Optional[Dict[str,Any]],**kwargs:Any):
        return EventEdge.edge(EdgeType.OUTPUT,
                              combine_vars(_vars_,kwargs))

    @staticmethod
    def error(_vars_:Optional[Dict[str,Any]],**kwargs:Any):
        return EventEdge.edge(EdgeType.ERROR,
                              combine_vars(_vars_,kwargs))


class Event(SmAttr):
    '''
    >>> EventState.NEW
    <EventState.NEW: 1>
    >>> EventState("NEW")
    <EventState.NEW: 1>
    >>> EventState(2)
    <EventState.SUCCESS: 2>
    >>> EventState("Q")
    Traceback (most recent call last):
    ...
    KeyError: 'Q'
    >>> from hashstore.utils import from_camel_case_to_underscores
    >>> e = Event(function=from_camel_case_to_underscores,
    ...    input_edge=EventEdge(
    ...        type=EdgeType.INPUT,
    ...        vars={"s":"CamelCase"},
    ...        dt=datetime(2018,9,28)))
    >>> e.to_json()
    {'state': 'NEW', 'function': 'hashstore.utils:from_camel_case_to_underscores', 'input_edge': {'type': 'INPUT', 'vars': {'s': 'CamelCase'}, 'dt': '2018-09-28T00:00:00'}, 'output_edge': None, 'error_edge': None}
    >>> str(e)
    '{"error_edge": null, "function": "hashstore.utils:from_camel_case_to_underscores", "input_edge": {"dt": "2018-09-28T00:00:00", "type": "INPUT", "vars": {"s": "CamelCase"}}, "output_edge": null, "state": "NEW"}'
    >>> q = Event(e.to_json())
    >>> q.state
    <EventState.NEW: 1>
    >>> str(q)
    '{"error_edge": null, "function": "hashstore.utils:from_camel_case_to_underscores", "input_edge": {"dt": "2018-09-28T00:00:00", "type": "INPUT", "vars": {"s": "CamelCase"}}, "output_edge": null, "state": "NEW"}'
    >>> events = list(Function.parse(from_camel_case_to_underscores)
    ...             .invoke({"s":"CamelCase"}, lambda a: "", lambda s: None))
    >>> len(events)
    2
    >>> events[1].output_edge.vars['return']
    'camel_case'
    >>>

    '''
    state: EventState = EventState.NEW
    function: GlobalRef
    input_edge: EventEdge
    output_edge: Optional[EventEdge]
    error_edge: Optional[EventEdge]

class InvocationError(SmAttr):
    inflated_input: Dict[str,Any]
    inflated_output: Dict[str,Any]
    traceback: Optional[str]


class Function(SmAttr):
    ref: GlobalRef
    in_mold: Mold
    out_mold: Mold

    @classmethod
    def factory(cls):
        def build_it(o):
            if inspect.isfunction(o):
                return Function.parse(o)
            else:
                return cls(o)
        return build_it

    @classmethod
    def parse(cls, fn, ref=None):
        if ref is None:
            ref = GlobalRef(fn)
        annotations=dict(get_type_hints(fn))
        return_type = annotations['return']
        del annotations['return']
        in_mold = Mold(annotations)
        in_mold.set_defaults(in_mold.get_defaults_from_fn(fn))
        out_mold = Mold()
        if return_type != type(None):
            out_hints = get_type_hints(return_type)
            if len(out_hints) > 0:
                out_mold.add_hints(out_hints)
            else:
                out_mold.add_entry(AttrEntry("return", return_type))
        return cls(ref=ref,
                   in_mold=in_mold,
                   out_mold=out_mold)

    def is_single_return(self)->bool:
        return len(self.out_mold.keys) == 1 \
               and self.out_mold.keys[0] == 'return'

    def invoke(self,
               flaten_in_vars:Dict[str, Any],
               flattener: Callable[[Any], str],
               dereferencer: Callable[[str], Any]
               )->Generator[Event, None, None]:
        err_info = InvocationError()
        input_edge = EventEdge.input(flaten_in_vars)
        try:
            err_info.inflated_input ={
                k: self.in_mold.attrs[k].inflate(v, dereferencer)
                for k, v in flaten_in_vars.items()}
            inflated_objs = self.in_mold.mold_it(
                err_info.inflated_input, Conversion.TO_OBJECT)
            yield Event( state=EventState.NEW,
                function=self.ref,
                input_edge=input_edge)
            result = self.ref.get_instance()(**inflated_objs)
            if self.is_single_return():
                result = {'return': result}
            else:
                result = DictLike(result)
            err_info.inflated_output = self.out_mold.mold_it(
                result, Conversion.TO_JSON)
            flatten_result ={
                k: self.out_mold.attrs[k].flatten(v, flattener)
                for k, v in err_info.inflated_output.items()}
            yield Event(
                state=EventState.SUCCESS,
                function=self.ref,
                input_edge=input_edge,
                output_edge=EventEdge.output(flatten_result)
            )
        except:
            err_info.traceback = traceback.format_exc()
            yield Event(state=EventState.FAIL,
                        function=self.ref,
                        input_edge=input_edge,
                        error_edge=EventEdge.error(
                            err_info.to_json()))



