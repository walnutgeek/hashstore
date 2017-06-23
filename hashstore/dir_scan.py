import fnmatch, os, codecs
from hashstore.utils import path_split_all, quict,json_encoder,reraise_with_msg
from datetime import datetime
from hashstore.db import DbFile
from hashstore.session import Session
from hashstore.udk import process_stream,\
    UDK,UDKBundle,UdkSet,quick_hash
from six import itervalues

import logging
log = logging.getLogger(__name__)

def pick_ignore_specs(n):
    '''
    >>> pick_ignore_specs('abc.txt')
    False
    >>> pick_ignore_specs('.gitignore')
    True
    '''
    return n in ['.gitignore', '.ignore']


class IgnoreEntry:
    '''
    >>> IgnoreEntry('a/b/c','*.txt').should_ignore_path('a/b/c/d.txt', False)
    True
    >>> IgnoreEntry('a/b','*.log').should_ignore_path('a/b/c/d.log', False)
    True
    >>> IgnoreEntry('a/b/','c/*.txt').should_ignore_path('a/b/c/d.txt', False)
    True
    >>> IgnoreEntry('a/b/','c/*/').should_ignore_path('a/b/c/d', True)
    True
    >>> IgnoreEntry('a/b/','c/*/').should_ignore_path('a/b/c/d', False)
    False
    '''
    def __init__(self,cur_dir, entry):
        self.root = path_split_all(cur_dir, False)
        self.root_length = len(self.root)
        self.entry = entry

    def _match_root(self, split):
        return len(split) > self.root_length \
               and self.root == split[:self.root_length]

    def _match_entry(self, split):
        path = os.path.join(*split)
        m = fnmatch.fnmatch(path, self.entry)
        return m

    def should_ignore_path(self, path , isdir):
        path_split = path_split_all(path, isdir)
        if self._match_root(path_split) :
            rel_split = path_split[self.root_length:]
            if isdir and self._match_entry(rel_split[:-1]):
                return True
            if self._match_entry(rel_split):
                return True
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
                    if l != u'' and l[0] != u'#':
                        ignore_entries.append(IgnoreEntry(cur_dir, l))
        return ignore_entries
    else:
        return initial_ignore_entries


def check_if_path_should_be_ignored(ignore_entries, path, isdir):
    return any(entry.should_ignore_path(path,isdir)
               for entry in ignore_entries )

IGNORE_FILENAMES = [u'.svn', u'.git', u'.DS_Store', u'.vol',
                    u'.hotfiles.btree', u'.ssh']

IGNORE_IF_STARTS_WITH = [u'.shamo', u'.backup', u'.Spotlight',
                         u'._', u'.Trash']


def ignore_files(n):
    return not(n in IGNORE_FILENAMES or
               any(n.startswith(t) for t in IGNORE_IF_STARTS_WITH))


class Scan:
    def __init__(self, path, addname, db_entry):
        if addname is None:
            self.name = os.path.basename(path)
        else:
            path = os.path.join(path, addname)
            self.name = addname
        self.path = os.path.abspath(path)
        self.db_entry = db_entry
        self._modtime = None
        self._size = None
        self._udk = None

    @property
    def udk(self):
        if self._udk is None:
            if not self.db_entry_is_stale():
                self._udk = self.db_entry['udk']
            else:
                self._build_udk()
        return self._udk

    @property
    def modtime(self):
        if self._modtime is None:
            self._calc_stat()
        return self._modtime

    @property
    def size(self):
        if self._size is None:
            self._calc_stat()
        return self._size

    def new_db_entry(self):
        return {
            "_name": self.name,
            "file_type": self.file_type,
            "udk": self.udk,
            "size": self.size,
            "modtime": self.modtime,
        }

    def __str__(self):
        return json_encoder.encode(self.new_db_entry())

    def db_entry_is_stale(self):
        return self.db_entry is None or self.modtime >= self.db_entry['modtime']


class FileScan(Scan):
    def __init__(self, path, addname = None, db_entry=None):
        Scan.__init__(self,path,addname,db_entry)
        self.file_type = 'FILE'

    def _calc_stat(self):
        stat = os.stat(self.path)
        self._modtime = stat.st_mtime
        self._size = stat.st_size

    def _build_udk(self):
        digest, _, inline_data = process_stream( open(self.path, 'rb'))
        self._udk = UDK.from_digest_and_inline_data(digest, inline_data)

DIR_DATAMODEL='''
    table:entry
      name TEXT PK
      file_type TEXT OPTIONS('DIR','FILE')
      udk UDK
      size INTEGER
      modtime INTEGER
'''

class DirScan(Scan):
    def __init__(self, path, addname=None, db_entry=None,
                 ignore_entries=[], receiver_coroutine=None):
        Scan.__init__(self,path,addname,db_entry)
        self.dbf = DbFile(os.path.join(self.path, '.shamo'), DIR_DATAMODEL)
        self.file_type = "DIR"
        self._bundle = None
        db_entries = {}
        store_all_entries = False
        if self.dbf.exists():
            try:
                q = self.dbf.select('entry', {}, where='1=1')
                db_entries = {r['name']: r for r in q}
            except:
                store_all_entries = True
        else:
            store_all_entries = True
        self.entries = {}
        files = sorted(filter(ignore_files, os.listdir(self.path)))
        ignore_entries = parse_ignore_specs(self.path, files, ignore_entries)
        for f in files:
            path_to_file = os.path.join(self.path, f)
            if os.path.islink(path_to_file):
                continue
            isdir = os.path.isdir(path_to_file)
            if check_if_path_should_be_ignored(ignore_entries, path_to_file, isdir):
                continue
            f_entry = db_entries.get(f, None)
            if f_entry is None:
                store_all_entries = True
            else:
                del db_entries[f]

            if isdir:
                entry = DirScan(self.path, f, f_entry, ignore_entries, receiver_coroutine)
            else:
                entry = FileScan(self.path, f, f_entry)
            self.entries[f] = entry
        if len(db_entries) > 0 or any(e.db_entry_is_stale() for e
                                           in itervalues(self.entries)):
            store_all_entries = True
        if receiver_coroutine:
            receiver_coroutine.send((self,store_all_entries))
        if store_all_entries:
            self.store_state()
        log.debug('{self.path} -> {self.udk}'.format(**locals()))

    def store_state(self):
        try:
            self.dbf.ensure_db()
            with Session(self.dbf) as session:
                self.dbf.delete('entry',{},where='1=1',session=session)
                for k in self.entries:
                    self.dbf.insert('entry',self.entries[k].new_db_entry(),session=session)
        except :
            log.warning('cannot store: '+self.dbf.file)


    def _build_udk(self):
        self._calc_stat()

    @property
    def bundle(self):
        if self._bundle is None:
            self._calc_stat()
        return self._bundle

    def _calc_stat(self):
        self._bundle = UDKBundle()
        for k in self.entries:
            self._bundle[k] = self.entries[k].udk
        self._udk = self._bundle.udk()
        self._content = self._bundle.content()
        self._size = sum(e.size for e in itervalues(self.entries)) \
                     + self._bundle.size()
        if len(self.entries) > 0:
            self._modtime =  max(e.modtime for e in itervalues(self.entries))
        else:
            stat = os.stat(self.path)
            self._modtime = stat.st_mtime

if __name__ == '__main__':
    import sys
    bundle = DirScan(sys.argv[1]).bundle
    print(bundle.udk())
    print(bundle.content())
