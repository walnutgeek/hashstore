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
    # NOT_AUTHORIZED = enum.auto()


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
    def input(_vars_:Optional[Dict[str,Any]]=None, **kwargs:Any):
        return EventEdge.edge(
            EdgeType.INPUT, combine_vars(_vars_,kwargs))

    @staticmethod
    def output(_vars_:Optional[Dict[str,Any]]=None, **kwargs:Any):
        return EventEdge.edge(
            EdgeType.OUTPUT, combine_vars(_vars_,kwargs))

    @staticmethod
    def error(_vars_:Optional[Dict[str,Any]]=None, **kwargs:Any):
        return EventEdge.edge(
            EdgeType.ERROR, combine_vars(_vars_,kwargs))


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
    >>> e = Event(exec_ref=from_camel_case_to_underscores,
    ...    input_edge=EventEdge(
    ...        type=EdgeType.INPUT,
    ...        vars={"s":"CamelCase"},
    ...        dt=datetime(2018,9,28)))
    >>> e.to_json()
    {'state': 'NEW', 'exec_ref': 'hashstore.utils:from_camel_case_to_underscores', 'input_edge': {'type': 'INPUT', 'vars': {'s': 'CamelCase'}, 'dt': '2018-09-28T00:00:00'}, 'output_edge': None, 'error_edge': None}
    >>> str(e)
    '{"error_edge": null, "exec_ref": "hashstore.utils:from_camel_case_to_underscores", "input_edge": {"dt": "2018-09-28T00:00:00", "type": "INPUT", "vars": {"s": "CamelCase"}}, "output_edge": null, "state": "NEW"}'
    >>> q = Event(e.to_json())
    >>> q.state
    <EventState.NEW: 1>
    >>> str(q)
    '{"error_edge": null, "exec_ref": "hashstore.utils:from_camel_case_to_underscores", "input_edge": {"dt": "2018-09-28T00:00:00", "type": "INPUT", "vars": {"s": "CamelCase"}}, "output_edge": null, "state": "NEW"}'
    >>> from hashstore.utils.smattr import NoResolver
    >>> events = list(Function.parse(from_camel_case_to_underscores)
    ...             .invoke({"s":"CamelCase"}, NoResolver()))
    >>> len(events)
    2
    >>> events[1].output_edge.vars['_']
    'camel_case'
    >>>

    '''
    state: EventState = EventState.NEW
    exec_ref: GlobalRef
    input_edge: EventEdge
    output_edge: Optional[EventEdge]
    error_edge: Optional[EventEdge]


EDGE_CLS_NAMES = {'Input', 'Output'}
IN_OUT = 'in_out'
mold_name = lambda cls_name: f'{cls_name[:-3].lower()}_mold'
EDGE_MOLDS = set(mold_name(cls_name) for cls_name in EDGE_CLS_NAMES)
EXECUTIBLE_TYPE = 'executible_type'


class ExecutibleFactory(type):
    def __init__(cls, name, bases, dct):
        defined_vars=set(dct)
        if not defined_vars.issuperset(EDGE_MOLDS):
            if IN_OUT in dct:
                InOut = dct[IN_OUT]
                for cls_name in EDGE_CLS_NAMES:
                    if cls_name in dct:
                        raise AssertionError(
                            f'Ambiguous {cls_name} and {IN_OUT}')
                    mold_n = mold_name(cls_name)
                    if mold_n in dct:
                        raise AssertionError(
                            f'Ambiguous {mold_n} and {IN_OUT}')
                    setattr(cls, mold_n, getattr(InOut, mold_n))
            else:
                for cls_name in EDGE_CLS_NAMES:
                    if cls_name in dct:
                        item_cls = dct[cls_name]
                        mold_n = mold_name(cls_name)
                        if mold_n in dct:
                            raise AssertionError(
                                f'Ambiguous {mold_n} and {cls_name}')
                        setattr(cls, mold_n, Mold(item_cls))
        if any(not(hasattr(cls, s)) for s in EDGE_MOLDS):
            raise AttributeError(f'Undefined: {EDGE_MOLDS}')

    def exec_factory(cls)->'Executible':
        if not hasattr(cls, EXECUTIBLE_TYPE):
            raise AttributeError(f'{EXECUTIBLE_TYPE} has to be defined')
        exec_cls = getattr(cls, EXECUTIBLE_TYPE)
        mold = Mold.ensure_it(exec_cls)
        return exec_cls(mold.pull_attrs(cls), ref=GlobalRef(cls))


class Executible(SmAttr):
    ref: GlobalRef
    in_mold: Mold
    out_mold: Mold

    @staticmethod
    def factory():
        def build_it(o):
            if inspect.isfunction(o):
                return Function.parse(o)
            else:
                ref = GlobalRef.ensure_it(o['ref'])
                inst = ref.get_instance()
                if inspect.isfunction(inst):
                    return Function.parse(inst)
                if inspect.isclass(inst) and issubclass(inst, ExecutibleFactory):
                    return inst.exec_factory()
                raise AttributeError(
                    f'Cannot build `Executible` out: {o}')
        return build_it

    def run(self, ctx:'ExecContext'):
        raise AssertionError("unimplemented")

    def invoke(self,
               flatten_input_vars:Dict[str, Any],
               resolver: ReferenceResolver
               )->Generator[Event, None, None]:
        ctx = ExecContext(
            executible=self,
            input_edge=EventEdge.input(flatten_input_vars),
            resolver=resolver)
        yield ctx.input_event()
        try:
            self.run(ctx)
        except:
            ctx.error = True
            ctx.traceback = traceback.format_exc()
        yield ctx.output_event()


class ExecContext(SmAttr):
    error: bool = False
    executible: Executible
    resolver: ReferenceResolver
    input_edge: EventEdge
    raw_input: Any
    raw_output: Any
    output_edge: Optional[EventEdge]
    traceback: Optional[str]

    def input_event(self):
        return Event(state=EventState.NEW,
                        exec_ref=self.executible.ref,
                        input_edge=self.input_edge)

    def get_raw_input(self):
        if self.raw_input is None :
            inflated_objs = self.executible.in_mold.inflate(
                self.input_edge.vars,
                self.resolver)
            self.raw_input = self.executible.in_mold.wrap_input(
                inflated_objs)
        return self.raw_input

    def output_event(self):
        if self.error:
            return Event(
                state=EventState.FAIL,
                exec_ref=self.executible.ref,
                input_edge=self.input_edge,
                error_edge=EventEdge.error(traceback=self.traceback))
        else:
            if self.output_edge is None:
                self.output_edge = EventEdge.output(
                    self.executible.out_mold.output_json(self.raw_output))
            return Event(
                state=EventState.SUCCESS,
                exec_ref=self.executible.ref,
                input_edge=self.input_edge,
                output_edge=self.output_edge
            )


class Function(Executible):

    @classmethod
    def parse(cls, fn):
        ref = GlobalRef(fn)
        in_mold, out_mold = extract_molds_from_function(fn)
        return cls(ref=ref, in_mold=in_mold, out_mold=out_mold)

    def __call__(self, *args, **kwargs):
        return self.ref.get_instance()(*args, **kwargs)

    def run(self, ctx:ExecContext):
        ctx.raw_output = self.ref.get_instance()(**ctx.get_raw_input())




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
