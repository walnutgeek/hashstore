import inspect
from typing import Union, Callable, List, Optional
from hashstore.utils import GlobalRef
from hashstore.utils.auto_wire import AutoWire, wire_names, AutoWireRoot
from hashstore.utils.event import Function
from hashstore.utils.log_box import LogBox
from hashstore.utils.smattr import (SmAttr, AttrEntry)
from hashstore.utils.time import CronExp, TimeZone




class MoldVar(AutoWire):
    """
    MoldVar
    """
    def _initialize(self):
        self.link:Union['MoldVar',None] = None
        self.backlinks = []

    def set_input(self, link:'MoldVar'):
        self.link = link
        self.link.add_backlink(self)

    def add_backlink(self, back_link:'MoldVar'):
        self.backlinks.append(back_link)


class TaskVar(MoldVar):
    def _initialize(self):
        super(TaskVar, self)._initialize()
        self.attr_entry: Union[AttrEntry, None] = None


class EdgeMold(AutoWire):
    def __init__(self, _parent_=None, _name_=None, **in_vars)->None:
        AutoWire.__init__(self,
                          _parent_=_parent_,
                          _name_=_name_)
        self.in_vars = in_vars

    def _wiring_factory(self, path, name):
        if len(path) == 1 :
            return MoldVar
        raise AttributeError(f'path:{wire_names(path)} name:{name}')

    def _validate(self, lb:LogBox):
        for k, link in self.in_vars.items():
            task_var = getattr(self.input, k)
            task_var.set_input(link)


class Retry(SmAttr):
    times_left: int
    retry_interval: int
    interval_increment: int = 0
    interval_multiplier: int = 1

    def decrement_retry(self):
        if self.times_left > 0:
            self.times_left = self.times_left - 1
            self.retry_interval = self.retry_interval * \
                                  self.interval_multiplier + \
                                  self.interval_increment
            return True
        return False


class Task(AutoWire):

    def __init__(self,
                 _fn_: Union[Function,Callable],
                 **in_vars) -> None:
        AutoWire.__init__(self)
        self.fn = Function.ensure_it(_fn_)
        self.in_vars = in_vars
        self.retry:Optional[Retry] = None

    def _wiring_factory(self, path, name):
        if len(path) == 1 :
            if name in ('input', 'output'):
                return EdgeMold
        path_names = wire_names(path)
        if len(path) == 2 and path_names[-1] in ('input', 'output'):
            return TaskVar
        raise AttributeError(f'path:{wire_names(path)} name:{name}')

    def set_retry(self, retry:Retry) -> 'Task':
        self.retry = retry
        return self

    def _validate(self, lb:LogBox):
        ctx='.'.join(wire_names(self._path()))
        mold = self.fn.in_mold
        unknown_vars = set(self.in_vars.keys()) - set(mold.keys)
        if len(unknown_vars) > 0:
            lb.error(f'{ctx}: {self.fn} cannot accept: {unknown_vars}')
        for k,ae in mold.attrs.items():
            if ae.required():
                if k not in self.in_vars:
                    lb.error(f'{ctx}: {k} is required for {self.fn}')

        for k, ae in self.fn.in_mold.attrs.items():
            task_var = getattr(self.input, k)
            task_var.attr_entry =  ae
        for k, ae in self.fn.out_mold.attrs.items():
            task_var = getattr(self.output, k)
            task_var.attr_entry =  ae
        """
        make sure that in_vars points to valid variables. 
        in_vars can piont to: 
           * Task -> EdgeMold -> TaskVar, 
           * or EdgeMold -> MoldVar
        """
        for k, link in self.in_vars.items():
            task_var = getattr(self.input, k)
            task_var.set_input(link)


class DagMeta(AutoWireRoot):
    def __init__(cls, name, bases, dct):
        AutoWireRoot.__init__(cls,name,bool,dct)
        lb=LogBox()
        for k, v in cls._children.items():
            if hasattr(v, '_validate'):
                v._validate(lb)
        if lb.has_errors():
            raise AttributeError(str(lb))


class Trigger(SmAttr):
    cron: CronExp
    tz: TimeZone = TimeZone('UTC')


# class Dag(SmAttr):
#     depend_on_prev: bool
#     triggers: List[Trigger]
#     tasks: List[Task]
#     ctx: Optional[SmAttr]
#     # in_vars: List[ValueDescriptor]


class HashLogic(SmAttr):
    name: str
    methods: List[Function]

    @classmethod
    def from_module(cls, module):
        logic = cls({"name":module.__name__})
        for n in dir(module):
            if n[:1] != '_' :
                fn = getattr(module, n)
                if inspect.isfunction(fn):
                    logic.methods.append(Function.parse(fn))
        return logic



'''
  CauseEffectVector
    (CEV)=
    run:R?,
    ver:HL,
    method,
    this?,
    params*,
    results+
    
  db:CauseVector
  db:EffectVector
  db:TransformVector
    (LV)=
    CEV=srcH,
    HL+L,
    detected,
    outH
  Invocation
    (I)=
    HL+D
    params,
    results
  Run
    (R)=
    I,HL+D+T
    params,
    results
  Attempt
    (A) = R
'''

# class CodeBase:
#     '''
#     (C)
#     '''
#     pass
#
#
# class CodeEnv:
#     '''
#     (E)
#     '''
#     pass
#
#
# class CodeVersion:
#     '''
#     (V) - SHA256 for CodeEnv PORTAL
#     '''
#     pass
#
#
# class Lens:
#     '''
#     (L)=<HL+T>,transform():M,params*
#     '''
#     pass

