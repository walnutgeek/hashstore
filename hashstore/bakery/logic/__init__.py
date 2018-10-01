import inspect
from typing import Union, Callable, List, Optional, \
    get_type_hints, Any, Dict

from hashstore.utils import GlobalRef
from hashstore.utils.smattr import (SmAttr, Mold, AttrEntry,
    typing_factory)
from hashstore.utils.time import CronExp, TimeZone


class Function(SmAttr):
    ref: GlobalRef
    in_mold: Mold
    out_mold: Mold

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
        if return_type is not None:
            out_hints = get_type_hints(return_type)
            if len(out_hints) > 0:
                out_mold.add_hints(out_hints)
            else:
                out_mold.add_entry(AttrEntry("return", return_type))
        return cls(ref=ref,
                   in_mold=in_mold,
                   out_mold=out_mold)

    def invoke(self, in_edge:Dict[str,Any])->Dict[str,Any]:
        pass


class TaskVar(object):
    def __init__(self, typing,
                 _path_:Optional[List[str]]=None,
                 _wired_:Optional['TaskVar']=None
                 )->None:
        self.typing = typing_factory(typing)
        self.path = _path_
        self.wired = _wired_


class EdgeMold:
    def __init__(self,
                 mold: Mold,
                 path: List[str],
                 variables: List[TaskVar]
                 )->None:
        for k,attr in mold.attrs.items():
            variable = TaskVar(attr, [*path, k])
            variables.append(variable)
            setattr(self, k, variable)

    def __getattr__(self, k:str)->TaskVar: ...


class Task:
    def __init__(self,
                 _fn_: Union[Function,Callable],
                 _name_: Optional[str] = None,
                 **in_vars_values) -> None:
        self.name = _name_
        self.fn = _fn_ if isinstance(_fn_, Function) else Function.parse(_fn_)
        self.variables:List[TaskVar] = []
        self.output = EdgeMold(
            self.fn.out_mold, ['output'], self.variables)
        self.input = EdgeMold(
            self.fn.in_mold, ['input'], self.variables)
        for k ,v in in_vars_values.items():
            if v is None:
                raise AssertionError(f'{k}={v}')
            else:
                getattr(self.input, k).wired = v

    def validate(self, unresolved_variables):
        for var in self.variables:
            var.path.insert(0,self.name)
            if var.path[1] == 'input':
                if var.wired is None:
                    unresolved_variables.append(var)


class DagMeta(type):
    def __init__(cls, name, bases, dct):
        tasks = []
        variables = []
        for k, v in dct.items():
            if isinstance(v, Task):
                v.name = k
                tasks.append(v)
            elif isinstance(v, TaskVar):
                v.name = k
                variables.append(v)
            else:
                print(f'What else: {v}')

        if '_tasks_' in dct:
            for task in dct['_tasks_']:
                if task.name is None:
                    raise AssertionError(
                        f'task.name undefined: {task}')
                dict[task.name] = task
                tasks.append(task)
        unresolved_variables = []
        for task in tasks:
            task.validate(unresolved_variables)
            variables.extend(task.variables)
        if len(unresolved_variables):
            raise AssertionError(f'{unresolved_variables}')
        dct['_tasks_'] = tasks
        dct['_variables_'] = variables


class Dag(metaclass=DagMeta):
    pass


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

