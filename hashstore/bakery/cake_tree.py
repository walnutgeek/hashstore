from hashstore.bakery import HasHash, CakePath, NamedCAKes, Cake
from hashstore.utils import EnsureIt


class CakeWrapper(HasHash, EnsureIt):
    def __init__(self,cake):
        self._cake = Cake.ensure_it(cake)

    def cake(self):
        return self._cake

class CakeTree(HasHash):
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
    >>> "a/b" in x
    True
    >>> "" in x
    False
    >>> x['a/c'] = '0'
    >>> x.cake()
    Cake('3IRoNogXy7sW3pKtB66DCwNbqEvDgYZ7iDGLzimya2MV')
    >>> x["a"].bundle().content()
    '[["b", "c"], ["0", "0"]]'
    >>> len(x["a"])
    2
    >>> del x["a/c"]
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
    """

    def __init__(self):
        self.store = {}
        self._bundle = None

    def __setitem__(self, k, v):
        k = CakePath.ensure_it(k)
        nxt_path, reminder = k.next_in_relative_path()
        self._bundle = None
        if reminder is None:
            if nxt_path is not None:
                self.store[nxt_path] = CakeWrapper.ensure_it(v)
            else:
                raise AssertionError('Cannot set itself')
        else:
            if nxt_path not in self.store:
                self.store[nxt_path] = CakeTree()
            self.store[nxt_path][reminder] = v

    def __delitem__(self, k):
        k = CakePath.ensure_it(k)
        self._bundle = None
        nxt_path, reminder = k.next_in_relative_path()
        if reminder is None:
            if nxt_path is not None:
                del self.store[nxt_path]
            else:
                raise AssertionError('Cannot delete itself')
        else:
            del self.store[nxt_path][reminder]

    def __getitem__(self, k):
        k = CakePath.ensure_it(k)
        nxt_path, reminder = k.next_in_relative_path()
        if reminder is None:
            if nxt_path is not None:
                return self.store[nxt_path]
            else:
                return self
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

    def iterate_path_tree_pairs(self, path = None):
        """
        >>> x = CakeTree()
        >>> x['a/b'] = '0'
        >>> x['a/c/x'] = '0'
        >>> list(x.iterate_path_tree_pairs())
        [(CakePath('a/c'), '[["x"], ["0"]]'), (CakePath('a'), '[["b", "c"], ["0", "CrBXQSRVFGVy79pGnBH"]]'), (CakePath(''), '[["a"], ["3yhpQdubJ2Iq3AU0TQmDUArYt9RqJzXjoVaJs7agXJVs"]]')]
        >>> list(x.iterate_path_tree_pairs())
        [(CakePath('a/c'), '[["x"], ["0"]]'), (CakePath('a'), '[["b", "c"], ["0", "CrBXQSRVFGVy79pGnBH"]]'), (CakePath(''), '[["a"], ["3yhpQdubJ2Iq3AU0TQmDUArYt9RqJzXjoVaJs7agXJVs"]]')]
        """
        if path is None:
            path = CakePath("")
        for name in sorted(self.store):
            v = self.store[name]
            if isinstance(v, CakeTree):
                child_path = path.child(name)
                for pair in v.iterate_path_tree_pairs(child_path):
                    yield pair
        yield (path, self)

    def __repr__(self):
        return repr(self.bundle().content())

    def bundle(self):
        if self._bundle is None:
            self._bundle = NamedCAKes()
            for k in self.store:
                self._bundle[k]= self.store[k].cake()
        return self._bundle

    def cake(self):
        return self.bundle().cake()

