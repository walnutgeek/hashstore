import inspect
from typing import Union, Callable, Dict, Any, List, Optional

from hashstore.utils import (GlobalRef)
from hashstore.utils.smattr import SmAttr
from hashstore.utils.time import CronExp, TimeZone




class ValueDescriptor(SmAttr):
    name: str
    type:GlobalRef
    #format:Optional


class Function(SmAttr):
    ref: GlobalRef
    in_vars: List[ValueDescriptor]
    out_vars: List[ValueDescriptor]

    @classmethod
    def parse(cls, fn, ref=None):
        if ref is None:
            ref = GlobalRef(fn)
        inst = cls({"ref":ref})
        return_type = fn.__annotations__['return']
        in_keys = list(fn.__annotations__.keys())[:-1]

        def append_only(val_descs, annotations, keys):
            for k in keys:
                val_descs.append(ValueDescriptor({
                    "name": k,
                    "type": GlobalRef(annotations[k])
                }))

        def append_all(val_descs, annotations):
            append_only(val_descs, annotations, annotations.keys())

        append_only(inst.in_vars, fn.__annotations__, in_keys)
        if return_type is not None:
            try:
                append_all(inst.out_vars, return_type.__annotations__)
            except AttributeError:
                inst.out_vars.append(ValueDescriptor({
                    "name": 'return',
                    "type": GlobalRef(return_type)
                }))
        return inst


class Task:
    def __init__(self,
                 fn: Union[Function,Callable],
                 **in_vars_values: Dict[str,Any]) -> None:
        self.fn = fn if isinstance(fn, Function) else Function.parse(fn)
        self.out_taskvars = {
            vd.name: TaskVar(self,vd)
            for vd in self.fn.out_vars
        }
        self.in_taskvars = {
            vd.name: TaskVar(self, vd, in_vars_values[vd.name])
            for vd in self.fn.in_vars
        }

    def __getattr__(self, item):
        if item in self.out_taskvars:
            return self.out_taskvars[item]
        else:
            raise AttributeError(f'Unknown attr: {item}')


class ValueRef(SmAttr):
    name:Optional[str]


class TaskVar(ValueRef):
    task: Task
    vd: ValueDescriptor
    # value_ref = attr.ib(**required(default=None))




# @attr.s
# class Task(object):
#     name = attr.ib(**required(str))
#     method_name = attr.ib(**required(str))
#     depend_on_tasks = attr.ib(**list_of(str))
#     dag_vars = attr.ib(**list_of(ValueDescriptor))
#     in_vars = attr.ib(**list_of(ValueDescriptor))


class Trigger(SmAttr):
    cron: CronExp
    tz: Optional[TimeZone] = TimeZone('UTC')


class Dag(SmAttr):
    name: str
    depend_on_prev: bool
    triggers: List[Trigger]
    tasks: List[Task]
    in_vars: List[ValueDescriptor]


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
                    logic.methods.append(
                        Function.parse(fn,GlobalRef(
                            f'{logic.name}:{n}')))
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

