import enum
import inspect
from datetime import datetime
from typing import Optional, Dict, Any, Generator
from .smattr import (SmAttr, combine_vars, Mold, ReferenceResolver,
                     extract_molds_from_function)
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
    >>> e = Event(executible=from_camel_case_to_underscores,
    ...    input_edge=EventEdge(
    ...        type=EdgeType.INPUT,
    ...        vars={"s":"CamelCase"},
    ...        dt=datetime(2018,9,28)))
    >>> e.to_json()
    {'state': 'NEW', 'executible': 'hashstore.utils:from_camel_case_to_underscores', 'input_edge': {'type': 'INPUT', 'vars': {'s': 'CamelCase'}, 'dt': '2018-09-28T00:00:00'}, 'output_edge': None, 'error_edge': None}
    >>> str(e)
    '{"error_edge": null, "executible": "hashstore.utils:from_camel_case_to_underscores", "input_edge": {"dt": "2018-09-28T00:00:00", "type": "INPUT", "vars": {"s": "CamelCase"}}, "output_edge": null, "state": "NEW"}'
    >>> q = Event(e.to_json())
    >>> q.state
    <EventState.NEW: 1>
    >>> str(q)
    '{"error_edge": null, "executible": "hashstore.utils:from_camel_case_to_underscores", "input_edge": {"dt": "2018-09-28T00:00:00", "type": "INPUT", "vars": {"s": "CamelCase"}}, "output_edge": null, "state": "NEW"}'
    >>> from hashstore.utils.smattr import NoResolver
    >>> events = list(Function.parse(from_camel_case_to_underscores)
    ...             .invoke({"s":"CamelCase"}, NoResolver()))
    >>> len(events)
    2
    >>> events[1].output_edge.vars['srv_']
    'camel_case'
    >>>

    '''
    state: EventState = EventState.NEW
    executible: GlobalRef
    input_edge: EventEdge
    output_edge: Optional[EventEdge]
    error_edge: Optional[EventEdge]


class ExecContext(SmAttr):
    error: bool = False
    resolver: ReferenceResolver
    input: Dict[str, Any]
    output: Dict[str, Any]
    traceback: Optional[str]


class Executible(SmAttr):
    ref: GlobalRef
    in_mold: Mold
    out_mold: Mold

    def run(self, ctx:ExecContext):
        raise AssertionError("unimplemented")

    def invoke(self,
               flatten_input_vars:Dict[str, Any],
               resolver: ReferenceResolver
               )->Generator[Event, None, None]:
        ctx = ExecContext(input=flatten_input_vars, resolver=resolver)
        input_edge = EventEdge.input(flatten_input_vars)
        yield Event(state=EventState.NEW,
                    executible=self.ref,
                    input_edge=input_edge)

        try:
            self.run(ctx)
        except:
            ctx.error = True
            ctx.traceback = traceback.format_exc()

        if ctx.error:
            yield Event(state=EventState.FAIL,
                        executible=self.ref,
                        input_edge=input_edge,
                        error_edge=EventEdge.error(
                            ctx.to_json()))
        else:
            yield Event(
                state=EventState.SUCCESS,
                executible=self.ref,
                input_edge=input_edge,
                output_edge=EventEdge.output(
                    self.out_mold.flatten(ctx.output, resolver)
                )
            )


class Function(Executible):

    @classmethod
    def factory(cls):
        def build_it(o):
            if inspect.isfunction(o):
                return Function.parse(o)
            else:
                return cls(o)
        return build_it

    @classmethod
    def parse(cls, fn):
        ref = GlobalRef(fn)
        in_mold, out_mold = extract_molds_from_function(fn)
        return cls(ref=ref, in_mold=in_mold, out_mold=out_mold)

    def run(self, ctx:ExecContext):
        inflated_objs = self.in_mold.inflate( ctx.input, ctx.resolver)
        wrapped = self.in_mold.wrap_input(inflated_objs)
        result = self.ref.get_instance()(**wrapped)
        ctx.output = self.out_mold.output_json(result)


EDGE_CLS_NAMES = {'Input', 'Output'}


def mold_name(cls_name):
    return f'{cls_name[:-3].lower()}_mold'


EDGE_MOLDS = set(mold_name(cls_name) for cls_name in EDGE_CLS_NAMES)


class ExecutibleMeta(type):
    def __init__(cls, name, bases, dct):
        defined_vars=set(dct)
        if not defined_vars.issuperset(EDGE_MOLDS):
            if defined_vars.issuperset(EDGE_CLS_NAMES):
                for cls_name in EDGE_CLS_NAMES:
                    item_cls = dct[cls_name]
                    setattr(cls, mold_name(cls_name), Mold(item_cls))
        if any(not(hasattr(cls, s)) for s in EDGE_MOLDS):
            raise AttributeError(f'Undefined: {EDGE_MOLDS}')


'''

class Dag(metaclass=DagMeta)
    task1 = Task[fn2]()

class Dag0(metaclass=DagMeta):
    pass

class Dag1(metaclass=DagMeta):
    input = EdgeMold()
    task1 = Task[fn2]()
    task0 = Task[Dag0]()
    task2 = Task[Container](
            n=task1.output.x, 
            i=input.z)
        .retry(times=3)
    

'''
