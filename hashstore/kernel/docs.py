from keyword import iskeyword
from typing import Optional, Set, Dict, List, Union

from hashstore.kernel import Stringable

CUTOFF_WIDTH = 65


def valid_variable_name(name:str) -> bool:
    """
    >>> valid_variable_name('X')
    True
    >>> valid_variable_name('_')
    True
    >>> valid_variable_name('X123')
    True
    >>> valid_variable_name('2')
    False
    >>> valid_variable_name('while')
    False
    >>> valid_variable_name('lorem ipsum')
    False
    """
    return name.isidentifier() and not(iskeyword(name))


class Content(Stringable):
    """
    >>> c = Content()
    >>> c.append("loer ipsum kot lakrose manta")
    >>> list(c.format(5,15))
    ['     loer ipsum kot', '     lakrose manta']
    >>> c = Content('loer')
    >>> c.append(" ipsum kot lakrose   manta  ")
    >>> list(c.format(5,15))
    ['     loer ipsum kot', '     lakrose manta']
    >>> list(c.format(5,3))
    ['     loer', '     ipsum', '     kot', '     lakrose', '     manta']
    >>> list(c.format(5,3, "  aa:"))
    ['  aa:', '     loer', '     ipsum', '     kot', '     lakrose', '     manta']
    >>> str(c)
    'loer ipsum kot lakrose manta'
    >>> repr(c)
    "Content('loer ipsum kot lakrose manta')"
    >>> c.insert("abc xyz: ")
    >>> str(c)
    'abc xyz: loer ipsum kot lakrose manta'
    >>> c.end_of_sentence()
    >>> str(c)
    'abc xyz: loer ipsum kot lakrose manta.'
    """
    def __init__(self, s=None):
        self.words = []
        self.append(s)

    def __len__(self):
        return len(self.words)

    def insert(self, s):
        if s is not None:
            s = s.strip()
            if len(s) > 0:
                for w in s.split()[::-1]:
                    self.words.insert(0, w)

    def end_of_sentence(self):
        if len(self.words) > 0:
            if self.words[-1][-1:] != '.':
                self.words[-1] = self.words[-1]+'.'

    def append(self, s):
        if s is not None:
            s = s.strip()
            if len(s) > 0:
                self.words.extend(s.split())

    def __str__(self):
        return ' '.join(self.words)

    def format(self, indent, cutoff_width, first_prefix = None):
        prefix = ' ' * indent
        next_line = None
        if first_prefix is not None:
            if len(first_prefix) > cutoff_width:
                yield first_prefix
            else:
                next_line = first_prefix
        for w in self.words:
            if next_line is None:
                next_line = prefix
            else:
                next_line += ' '
            next_line += w
            if len(next_line) > cutoff_width:
                yield next_line
                next_line = None
        if next_line is not None:
            yield next_line


class AbstractDocEntry:

    def __init__(self, name, indent, content):
        self.name = name
        self.indent = indent
        self.content = Content(content)
        self.unparsed_lines = []

    @classmethod
    def empty(cls, name):
        inst = cls(name, 0, "")
        inst.init_parse()
        return inst

    @classmethod
    def detect_entry(cls, indent, striped, allowed_keys=None):
        def check_if_key_allowed(key):
            return ((allowed_keys is None or key in allowed_keys)
                    and valid_variable_name(key))
        split = [s.strip() for s in striped.split(':', 1)]
        key = split[0]
        if len(split)==2 and check_if_key_allowed(key):
            return cls(key, indent, split[1])

    def init_parse(self):
        if self.unparsed_lines is not None:
            self._init_parse()
            self.unparsed_lines = None

    def collect_content(self, curr_indent, striped):
        empty_line = len(striped) == 0
        if empty_line or curr_indent <= self.indent:
            self.init_parse()
            return False
        else:
            self.unparsed_lines.append((curr_indent, striped))
            return True

    @staticmethod
    def ensure_parse(doc_entry):
        if doc_entry is not None:
            doc_entry.init_parse()


class VariableDocEntry(AbstractDocEntry):

    def _init_parse(self):
        for prefix, striped in self.unparsed_lines:
            self.content.append(striped)

    def format(self, indent):
        yield from self.content.format(
            indent + 4, CUTOFF_WIDTH, ' ' * indent + self.name + ':')


class Placeholder:
    def __init__(self, indent, key):
        self.indent = indent
        self.key = key

    def format(self, var_groups):
        vg = var_groups[self.key]
        yield from vg.format(self.indent)


class GroupOfVariables(AbstractDocEntry):

    def placeholder(self):
        return Placeholder(self.indent, self.name)

    def _init_parse(self):
        curr_var = None
        self.variables = {}
        var_indent = None
        for indent, striped in self.unparsed_lines:
            new_var = None
            if var_indent in (None, indent):
                new_var = VariableDocEntry.detect_entry(indent,striped)
            if new_var is None:
                if curr_var is None:
                    self.content.append(striped)
                else:
                    if not curr_var.collect_content(indent, striped):
                        raise ValueError(
                            f"Missleading indent={indent}? "
                            f"var_indent={var_indent} "
                            f"line={striped!r} ")
            else:
                AbstractDocEntry.ensure_parse(curr_var)
                self.variables[new_var.name] = curr_var = new_var
                var_indent = indent
        AbstractDocEntry.ensure_parse(curr_var)

    def keys(self):
        return self.variables.keys()

    def format(self, indent):
        yield ' ' * indent + self.name + ':'
        indent += 4
        if len(self.content) > 0:
            yield from self.content.format(indent, CUTOFF_WIDTH)
        for _,v in self.variables.items():
            yield from v.format(indent)


    def __getitem__(self, k):
        return self.variables[k]


class DocStringTemplate:
    def __init__(self, doc: Optional[str], keys_expected: Set[str]
                 )->None:
        self.keys_expected = keys_expected
        self.var_groups: Dict[str,GroupOfVariables] = {}
        self.template: List[Union[Placeholder,str]] = []
        if doc is None:
            for k in keys_expected:
                self.template.append(Placeholder(0,k))
                self.template.append("")
        else:
            curr_group = None
            for l in doc.split('\n'):
                striped = l.strip()
                indent = l.index(striped)
                if curr_group is not None:
                    if curr_group.collect_content(indent,striped):
                        continue
                curr_group = GroupOfVariables.detect_entry(
                    indent, striped, keys_expected)
                if curr_group is not None:
                    self.var_groups[curr_group.name] = curr_group
                    self.template.append(curr_group.placeholder())
                else:
                    self.template.append(l)
            self.template.append('')

    def format(self):
        for l in self.template:
            if isinstance(l, Placeholder):
                for p in l.format(self.var_groups):
                    yield p
            else:
                yield l
        yield ""

    def doc(self):
        return "\n".join(self.format())


