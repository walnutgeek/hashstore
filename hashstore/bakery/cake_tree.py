from enum import IntEnum

from hashstore.bakery import CakePath, HasCake, Cake, CakeRack, CakeRole


class NodeState(IntEnum):
    """
    >>> list(NodeState) #doctest: +NORMALIZE_WHITESPACE
    [<NodeState.unknown: 0>, <NodeState.scanning: 1>,
    <NodeState.scanned: 2>, <NodeState.storing: 3>,
    <NodeState.stored: 4>, <NodeState.pruned: 5>]
    >>> [v.end_state() for v in NodeState]
    [False, False, True, False, True, True]
    """
    unknown = 0
    scanning = 1
    scanned = 2
    storing = 3
    stored = 4
    pruned = 5

    def end_state(self):
        return self.name[-1] == 'd'


class Node(HasCake):
    def __init__(self, parent, name, state=NodeState.unknown):
        self.name = name
        self.parent = parent
        self.state = state
        if isinstance(self.parent, Neuron):
            self.parent.add_child(self)
        elif self.parent is not None:
            raise AssertionError('has to be Neuron or None')

    def __str__(self):
        return '/'.join( g.name for g in self.ancestry())

    def __repr__(self):
        return str(self)

    def root(self):
        if self.parent is not None:
            return self.parent.root()
        else:
            return self

    def cake_path(self, relative=None):
        path = list(self.ancestry(include_root=True))
        if path[0].relative():
            relative = True
        elif relative is None:
            relative = False
        path_names = [p.name for p in path[1:]]
        if relative:
            return CakePath(None, _root=None, _path=path_names)
        else:
            return CakePath(None, _root=path[0].portal, _path=path_names)

    def ancestry(self, include_root=None):
        include_self = True
        if self.parent is not None:
            for grandpa in self.parent.ancestry(include_root):
                yield grandpa
        else: #CakeTree
            include_self = not(self.relative()) if include_root is None \
                else include_root
        if include_self:
            yield self

    def __iter__(self):
        return
        yield # pragma: no cover

    def role(self):
        return self.cake().role


class CakeNode(Node):
    def __init__(self, parent, name, cake, state=NodeState.unknown):
        Node.__init__(self,parent, name, state)
        self._cake = Cake.ensure_it(cake)

    def cake(self):
        return self._cake


class Neuron(Node):
    def __init__(self, parent, name, state=NodeState.unknown):
        Node.__init__(self, parent, name, state)
        self.store = {}
        self._bundle = None

    def prune(self):
        return CakeNode(self.parent, self.name, self.cake(),
                        NodeState.pruned)

    def role(self):
        return CakeRole.NEURON

    def clean(self):
        self._bundle = None
        if self.parent is not None:
            self.parent.clean()

    def add_child(self, child):
        self.store[child.name] = child
        self.clean()

    def __setitem__(self, k, cake):
        k = CakePath.ensure_it(k)
        nxt_path, reminder = k.next_in_relative_path()
        if reminder is None:
            if nxt_path is None:
                raise AssertionError('Cannot set itself')
            else:
                self.store[nxt_path] = CakeNode(self, nxt_path, cake)
                self.clean()
        else:
            if nxt_path not in self.store:
                self.store[nxt_path] = Neuron(self,nxt_path)
            self.store[nxt_path][reminder] = cake

    def __delitem__(self, k):
        k = CakePath.ensure_it(k)
        self._bundle = None
        nxt_path, reminder = k.next_in_relative_path()
        if reminder is None:
            if nxt_path is None:
                raise AssertionError('Cannot delete itself')
            else:
                del self.store[nxt_path]
                self.clean()
        else:
            del self.store[nxt_path][reminder]

    def __getitem__(self, k):
        k = CakePath.ensure_it(k)
        nxt_path, reminder = k.next_in_relative_path()
        if reminder is None:
            if nxt_path is None:
                return self
            else:
                return self.store[nxt_path]
        else:
            return self.store[nxt_path][reminder]

    def __len__(self):
        return len(self.store)

    def __contains__(self, k):
        k = CakePath.ensure_it(k)
        nxt_path, reminder = k.next_in_relative_path()
        if reminder is None:
            if nxt_path is not None:
                return nxt_path in self.store
            else:
                return False
        else:
            return reminder in self.store[nxt_path]

    def __iter__(self):
        for name in sorted(self.store):
            yield self.store[name]

    def visit_tree(self, depth=None):
        if depth is not None:
            if depth <= 0 :
               return
            depth -= 1
        if depth is None or depth > 0 :
            for v in self:
                if isinstance(v, Neuron):
                    for child in v.visit_tree(depth):
                        yield child
                else:
                    yield v
        yield self

    def bundle(self):
        if self._bundle is None:
            self._bundle = CakeRack()
            for k in self.store:
                self._bundle[k]= self.store[k].cake()
        return self._bundle

    def cake(self):
        return self.bundle().cake()



class CakeTree(Neuron):
    """
    >>> x = CakeTree()
    >>> x['a/b'] = '0'
    >>> x.cake()
    Cake('1kmRGqqGH36SWaMEp1EsTSLWbFKGN8VvMyd7M7uyzJQ9')
    >>> x.bundle().content()
    '[["a"], ["CrBXOJUepyW6bMd2Wgl"]]'
    >>> x["a"].bundle().content()
    '[["b"], ["0"]]'
    >>> "a" in x
    True
    >>> x["a"].cake()
    Cake('CrBXOJUepyW6bMd2Wgl')
    >>> x["a/b"].cake()
    Cake('0')
    >>> list(x['a/b'].ancestry())
    [a, a/b]
    >>> "a/b" in x
    True
    >>> "" in x
    False
    >>> x['a/c'] = '0'
    >>> x['a/c'].root() == x
    True
    >>> x['a/c'].cake_path()
    CakePath('a/c')
    >>> x['a/c'].cake_path(relative=False)
    CakePath('a/c')
    >>> list(x['a/b'])
    []
    >>> list(x['a'])
    [a/b, a/c]
    >>> list(x)
    [a]
    >>> x.cake()
    Cake('3IRoNogXy7sW3pKtB66DCwNbqEvDgYZ7iDGLzimya2MV')
    >>> x["a"].bundle().content()
    '[["b", "c"], ["0", "0"]]'
    >>> len(x["a"])
    2
    >>> del x["a/c"]
    >>> x.cake()
    Cake('1kmRGqqGH36SWaMEp1EsTSLWbFKGN8VvMyd7M7uyzJQ9')
    >>> x["a"].bundle().content()
    '[["b"], ["0"]]'
    >>> x["a"].cake()
    Cake('CrBXOJUepyW6bMd2Wgl')
    >>> x[""].cake()
    Cake('1kmRGqqGH36SWaMEp1EsTSLWbFKGN8VvMyd7M7uyzJQ9')
    >>> len(x)
    1
    >>> x[""]="0"
    Traceback (most recent call last):
    ...
    AssertionError: Cannot set itself
    >>> del x[""]
    Traceback (most recent call last):
    ...
    AssertionError: Cannot delete itself
    >>> x.bundle().content()
    '[["a"], ["CrBXOJUepyW6bMd2Wgl"]]'
    >>> from hashstore.bakery import Cake
    >>> g=Cake('4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T')
    >>> y=CakeTree(g)
    >>> y
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T
    >>> y['a/b/c']='0'
    >>> y['a/z']='0'
    >>> y['a/b/c']
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/b/c
    >>> list(y.visit_tree(3)) #doctest: +NORMALIZE_WHITESPACE
    [/4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/b,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/z,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T]
    >>> list(y.visit_tree(2)) #doctest: +NORMALIZE_WHITESPACE
    [/4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T]
    >>> list(y.visit_tree(1))
    [/4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T]
    >>> list(y.visit_tree(0))
    []
    >>> list(y.visit_tree(None)) #doctest: +NORMALIZE_WHITESPACE
    [/4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/b/c,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/b,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/z,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T]
    >>> [ v.role().value for v in y.visit_tree()]
    [0, 1, 0, 1, 1]
    >>> len(list(y.visit_tree(None))) == len(list(y.visit_tree(4)))
    True
    >>> y['a/b'].prune()
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/b
    >>> list(y.visit_tree(None)) #doctest: +NORMALIZE_WHITESPACE
    [/4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/b,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/z,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a,
    /4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T]
    >>> isinstance(y['a/b'],CakeNode)
    True
    >>> y['a']['b'].cake_path(relative=True)
    CakePath('a/b')
    >>> y['a']['b'].cake_path()
    CakePath('/4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/b')
    >>> y['a']['b'].cake_path(relative=False)
    CakePath('/4Fm5goWjjISStoovcZaowz0heUxOv4CXbUob0CBKi46T/a/b')

    """

    def __init__(self, portal = None, path =None):
        self.portal = portal
        self.path = path
        name = None if portal is None else '/' + str(self.portal)
        Neuron.__init__(self, None, name)

    def relative(self):
        return self.portal is None

    def __str__(self):
        return '' if self.name is None else self.name



