import fnmatch
import codecs
import os
from pathlib import Path
import logging

log = logging.getLogger(__name__)


IGNORE_SPECS = ('.gitignore', '.ignore')


IGNORE_FILENAMES = ('.svn', '.git', '.DS_Store', '.vol',
                    '.hotfiles.btree', '.ssh')

IGNORE_IF_STARTS_WITH = ('.shamo',  '.cake', '.backup',
                         '.Spotlight', '._', '.Trash')


def pick_ignore_specs(n):
    '''
    >>> pick_ignore_specs('abc.txt')
    False
    >>> pick_ignore_specs('.gitignore')
    True
    '''
    return n in IGNORE_SPECS


def ignore_files(n):
    return not(n in IGNORE_FILENAMES or
               any(n.startswith(t) for t in IGNORE_IF_STARTS_WITH))


class IgnoreEntry:
    '''
    >>> IgnoreEntry('a/b/c','*.txt').should_ignore_path('a/b/c/d.txt')
    True
    >>> IgnoreEntry('a/b','*.log').should_ignore_path('a/b/c/d.log')
    True
    >>> IgnoreEntry('a/b/','c/*.txt').should_ignore_path('a/b/c/d.txt')
    True
    >>> IgnoreEntry('a/b/','c/*.txt').should_ignore_path('a/b/c2/d.txt')
    False
    >>> IgnoreEntry('a/b/','c/*/').should_ignore_path('a/b/c/d')
    True
    '''
    def __init__(self,cur_dir, entry):
        self.root = Path(cur_dir)
        self.entry = entry

    def should_ignore_path(self, path):
        if not isinstance(path, Path):
            path = Path(path)
        if self.root in path.parents :
            rel_path = path.relative_to(self.root)
            return rel_path.match(self.entry)
        return False


def parse_ignore_specs(cur_dir, files, initial_ignore_entries):
    ignore_specs = list(filter(pick_ignore_specs, files))
    if len(ignore_specs) > 0:
        ignore_entries = list(initial_ignore_entries)
        for spec in ignore_specs:
            spec_path = os.path.join(cur_dir, spec)
            with codecs.open(spec_path, 'r', 'utf-8') as fh:
                for l in fh.readlines():
                    l = l.strip()
                    if l != '' and l[0] != '#':
                        ignore_entries.append(IgnoreEntry(cur_dir, l))
        return ignore_entries
    else:
        return initial_ignore_entries


def check_if_path_should_be_ignored(ignore_entries, path, isdir):
    return any(entry.should_ignore_path(path)
               for entry in ignore_entries )

