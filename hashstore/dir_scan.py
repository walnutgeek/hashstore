import fnmatch, os, codecs

import six

from hashstore.utils import path_split_all, ensure_unicode, quict,\
    json_encoder,reraise_with_msg, ensure_directory, read_in_chunks, \
    is_file_in_directory
from hashstore.db import DbFile
from hashstore.session import Session, _session
from hashstore.udk import process_stream,\
    UDK,UDKBundle,UdkSet,quick_hash
import uuid
from hashstore.client import RemoteStorage

import os
import sys
import hashstore.base_x as bx

import logging
log = logging.getLogger(__name__)

b58 = bx.base_x(58)


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
    >>> IgnoreEntry('a/b/c','*.txt').should_ignore_path('a/b/c/d.txt', isdir=False)
    True
    >>> IgnoreEntry('a/b','*.log').should_ignore_path('a/b/c/d.log', isdir=False)
    True
    >>> IgnoreEntry('a/b/','c/*.txt').should_ignore_path('a/b/c/d.txt', isdir=False)
    True
    >>> IgnoreEntry('a/b/','c/*.txt').should_ignore_path('a/b/c2/d.txt', isdir=False)
    False
    >>> IgnoreEntry('a/b/','c/*/').should_ignore_path('a/b/c/d', isdir=True)
    True
    >>> IgnoreEntry('a/b/','c/*/').should_ignore_path('a/b/c/d', isdir=False)
    False
    >>> IgnoreEntry('a/b/','c/*/').should_ignore_path('a/b/c/d', isdir=False)
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


class ScanStats:
    def __init__(self, force_rehash=False):
        self.hashed_counts = 0
        self.hashed_bytes = 0
        self.force_rehash = force_rehash

    def increment_count(self):
        self.hashed_counts += 1

    def count_bytes(self, buffer):
        self.hashed_bytes += len(buffer)


class Scan:
    def __init__(self, path, addname, file_type, stats):
        path = ensure_unicode(path)
        self.file_type = file_type
        self.stats = stats
        if addname is None:
            self.name = os.path.basename(path)
        else:
            addname = ensure_unicode(addname)
            path = os.path.join(path, addname)
            self.name = addname
        self.path = os.path.abspath(path)

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


class FileScan(Scan):
    def __init__(self, path, addname, from_db, stats):
        Scan.__init__(self, path, addname, 'FILE', stats)
        stat = os.stat(self.path)
        self.modtime = stat.st_mtime
        self.size = stat.st_size
        if stats.force_rehash or from_db is None \
                or self.modtime > from_db['modtime']:
            self.stats.increment_count()
            digest, _, inline_data = process_stream(
                open(self.path, 'rb'),
                process_buffer=self.stats.count_bytes
            )
            self.udk = UDK.from_digest_and_inline_data(digest, inline_data)
        else:
            self.udk = from_db['udk']

DIRKEY = 'dirkey'

ENTRY = 'entry'

ENTRY_DM= '''
    table:{ENTRY}
      name TEXT PK
      file_type TEXT OPTIONS('DIR','FILE')
      udk UDK
      size INTEGER
      modtime INTEGER
    table:{DIRKEY}
      singleton_id PK
      dir_id TEXT
'''.format(**locals())


class Shamo:

    def __init__(self, path):
        self.dbf = DbFile(os.path.join(path, '.shamo'), ENTRY_DM)
        self._dir_id = None

    def total(self):
        return sum(f['size'] for f in self.directory_usage())

    def directory_usage(self):
        return self.dbf.select(ENTRY,{},
                               where='1=1 order by size DESC, name')

    def read_entries(self):
        if self.dbf.exists():
            try:
                q = self.dbf.select(ENTRY, {}, where='1=1')
                return {r['name']: r for r in q}
            except:
                pass
        return {}

    def store_entries(self, entries):
        try:
            with Session(self.dbf) as session:
                self.dir_id(session=session)
                self.dbf.delete(ENTRY, {}, where='1=1',
                                session=session)
                for e in entries:
                    self.dbf.insert(ENTRY, e, session=session)
        except:
            # from traceback import print_exc
            # print_exc()
            log.warning('cannot store: ' + self.dbf.file)

    @_session
    def dir_id(self, session=None):
        if self._dir_id is None:
            r = None
            if not session.has_table(DIRKEY):
                self.dbf.create_db(session=session)
            else:
                r = self.dbf.select_one(DIRKEY,
                                        quict(singleton_id=1),
                                        session=session)
            if r is not None:
                self._dir_id = r['dir_id']
            else:
                self._dir_id = b58.encode(os.urandom(32))
                self.dbf.store(DIRKEY, {
                    'singleton_id': 1,
                    '_dir_id': self._dir_id},
                               session=session)
        return self._dir_id


class DirScan(Shamo, Scan):
    def __init__(self, path, addname=None, stats = None,
                 ignore_entries=[], on_each_dir=None, parent=None):
        self.parent = parent
        if stats is None:
            stats = ScanStats()
        Scan.__init__(self, path, addname, "DIR", stats)
        Shamo.__init__(self,self.path)

        child_entries = []

        old_db_entries = self.read_entries()

        files = sorted(filter(ignore_files, os.listdir(self.path)))
        ignore_entries = parse_ignore_specs(self.path, files, ignore_entries)

        for f in files:
            path_to_file = os.path.join(self.path, f)
            if os.path.islink(path_to_file):
                continue
            isdir = os.path.isdir(path_to_file)
            if check_if_path_should_be_ignored(ignore_entries, path_to_file, isdir):
                continue

            try:
                if isdir:
                    entry = DirScan(self.path, f, self.stats,
                                    ignore_entries, on_each_dir, parent=self)
                else:
                    entry = FileScan(self.path, f,
                                     old_db_entries.get(f, None),
                                     self.stats)
            except OSError:
                log.warning('cannot read: %s/%s' , self.path, f)
            except IOError:
                log.warning('cannot read: %s/%s' , self.path, f)
            else:
                child_entries.append(entry)

        self.bundle = UDKBundle()
        for e in child_entries:
            self.bundle[e.name] = e.udk

        self.udk = self.bundle.udk()
        self.size = sum(e.size for e in child_entries) \
                    + self.bundle.size()

        stat = os.stat(self.path)

        self.modtime = stat.st_mtime
        if len(child_entries) > 0:
            youngest_file = max(e.modtime for e in child_entries)
            self.modtime = max(self.modtime, youngest_file)

        self.new_db_entries =[ e.new_db_entry() for e in child_entries]

        self.store_entries(self.new_db_entries)

        log.debug(u'{self.path} -> {self.udk}'.format(**locals()))

        if on_each_dir:
            on_each_dir(self)

REMOTE = 'remote'

REMOTE_DM= '''
    table:{REMOTE}
      remote_id PK
      path TEXT AK
      url_uuid UUID4
      url_text TEXT
      mount_session TEXT
      created TIMESTAMP INSERT_DT
'''.format(**locals())

class Progress:
    def __init__(self,path):
        self.path = path
        try:
            self.total = Shamo(path).total()
        except:
            self.total = None
        self.current = 0
        self.terminal = sys.stdout.isatty()
        self.pad_to = 0
        self._value = ''


    def just_processed(self, towards_total, directory ):
        self.current += towards_total
        directory = directory[len(self.path)+1:]
        look = lambda start: directory.index(os.path.sep, start) + 1
        try:
            directory = directory[:look(look(look(0)))]
        except:
            pass
        if six.PY2:
            directory = directory.encode('utf-8')
        output = '%s %s ' % (self.pct_value(), directory)
        if self._value != output:
            self._value = output
            diff = self.pad_to - len(output)
            self.pad_to = len(output)
            if diff > 0 :
                output += ' ' * diff
            output += '\r' if self.terminal else '\n'
            sys.stdout.write(output)
            sys.stdout.flush()

    def pct_value(self):
        if self.total is None:
            return '?'
        pct_format = '%3.2f%%' if self.terminal  else  '%3d%%'
        return pct_format % (100 * float(self.current)/self.total)

class Remote:
    def __init__(self, directory):
        self.path = os.path.abspath(directory)
        home_config = os.path.join(os.environ['HOME'], '.shamo')
        self.dbf = DbFile(home_config, REMOTE_DM)


    def register(self, url, invitation=None, session=None):
        url_uuid = uuid.uuid4()
        storage = RemoteStorage(url)
        server_uuid = storage.register(url_uuid,
                             invitation=invitation,
                             meta={'mount_path': self.path})
        if server_uuid is not None:
            self.dbf.ensure_db()
            self.dbf.store('remote', quict(
                path=self.path,
                _url_uuid=url_uuid,
                _url_text=url,
                _mount_session=quick_hash(server_uuid)
                ), session=session)
            log.info('remote registered for {self.path} at {url}'.format(
                **locals()))
        else:
            log.error('cannot register on: {url}'.format(**locals()))

    def storage(self):
        for remote in self.dbf.select('remote', {}, '1=1 order by path DESC'):
            if is_file_in_directory(self.path, remote['path']) :
                storage = RemoteStorage(remote['url_text'])
                storage.login(remote['url_uuid'],remote['mount_session'])
                return storage
        raise ValueError('cannot backup, need register mount first')

    def backup(self):
        progress = Progress(self.path)
        with self.storage() as storage:
            def ensure_files_on_remote(dir_scan):
                bundles = { dir_scan.udk: dir_scan.bundle}
                mount_hash = dir_scan.udk if dir_scan.parent is None else None
                store_dir = True
                while store_dir:
                    _, hashes_to_push = storage.store_directories(bundles, mount_hash)
                    store_dir = False
                    for h in hashes_to_push:
                        h = UDK.ensure_it(h)
                        name = dir_scan.bundle.get_name_by_udk(h)
                        file = os.path.join(dir_scan.path, name)
                        fp = open(file, 'rb')
                        stored = storage.write_content(fp)
                        if stored != h:
                            log.info('path:%s, %s != %s' % (file, h, stored))
                            dir_scan.bundle[name] = stored
                            dir_scan.udk = dir_scan.bundle.udk()
                            store_dir = True
                progress.just_processed(sum(f['size'] for f in dir_scan.new_db_entries
                                            if f['file_type'] == 'FILE')
                                        + dir_scan.bundle.size(), dir_scan.path)

            dir = DirScan(self.path,on_each_dir=ensure_files_on_remote)
            return dir.udk

    def restore(self, key, path):
        with self.storage() as storage:
            def restore_inner( k, p):
                k = UDK.ensure_it(k)
                if k.named_udk_bundle:
                    content = storage.get_content(k)
                    bundle = UDKBundle(content)
                    ensure_directory(p)
                    for n in bundle:
                        file_path = os.path.join(p, n)
                        file_k = bundle[n]
                        if file_k.named_udk_bundle:
                            restore_inner(file_k, file_path)
                        else:
                            try:
                                out_fp = open(file_path, "wb")
                                in_fp = storage.get_content(file_k)
                                for chunk in read_in_chunks(in_fp):
                                    out_fp.write(chunk)
                                out_fp.close()
                            except:
                                reraise_with_msg(
                                    "%s -> %s" % (file_k, file_path))
            restore_inner(key,path)


if __name__ == '__main__':
    import sys

    scan = DirScan(sys.argv[1])
    print('udk: %s\nhashed_counts: %s\nhashed_bytes: %s\n' %
          (scan.bundle.udk(),scan.stats.hashed_counts,scan.stats.hashed_bytes))
    # print(bundle.content())
