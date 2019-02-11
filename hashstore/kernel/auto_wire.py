from typing import Optional, Union, List, Iterable

from hashstore.kernel.smattr import SINGLE_RETURN_VALUE


class AutoWireRoot(type):
    def __init__(cls, name, bases, dct):
        for k, v in dct.items():
            if k[:1] == '_':
                continue
            if hasattr(v, '_attach_to_root'):
                v._attach_to_root(k, cls)


class AutoWire:
    def __init__(self,
                 _parent_:Optional['AutoWire'] = None,
                 _name_:Optional[str] = None
                 )->None:
        self._name = _name_
        self._parent:Union[AutoWire,AutoWireRoot,None] = _parent_
        self._maintain_link()

    def _maintain_link(self):
        if self._parent is not None and self._name is not None:
            try:
                self._parent._children[self._name] = self
            except AttributeError:
                self._parent._children = {self._name : self}

    def _attach_to_root(self, name:str, root:AutoWireRoot)->None:
        self._name = name
        self._parent = root
        self._maintain_link()

    def _wiring_factory(self, path, name):
        return AutoWire

    def _root(self)->Optional[AutoWireRoot]:
        if self._parent is None:
            return None
        elif isinstance(self._parent, AutoWireRoot):
            return self._parent
        else:
            return self._parent._root()

    def _path(self)->List['AutoWire']:
        if self._parent is None :
            return [self]
        elif isinstance(self._parent, AutoWireRoot):
            return [self]
        else:
            return [*self._parent._path(), self]

    def __getattr__(self, name):
        if name != SINGLE_RETURN_VALUE and name[:1] == '_':
            raise AttributeError(f'no privates: {name}')
        path = self._path()
        attr_cls = path[0]._wiring_factory(path, name)
        v = attr_cls(_parent_=self, _name_=name)
        if hasattr(v, '_initialize'):
            v._initialize()
        setattr(self, name, v)
        return v


def wire_names(path:Iterable[AutoWire])->List[str]:
    return ["" if p._name is None else p._name for p in path]
