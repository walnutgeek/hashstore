import fnmatch, os, codecs
from hashstore.utils import path_split_all, ensure_unicode, quict,\
    json_encoder,reraise_with_msg, ensure_directory, read_in_chunks
from hashstore.db import DbFile
from hashstore.session import Session
from hashstore.udk import process_stream,\
    UDK,UDKBundle,UdkSet,quick_hash
import uuid
from hashstore.client import RemoteStorage
import logging
log = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s %(message)s')


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



ENTRY_DM= '''
    table:entry
      name TEXT PK
      file_type TEXT OPTIONS('DIR','FILE')
      udk UDK
      size INTEGER
      modtime INTEGER
'''



class DirScan(Scan):
    def __init__(self, path, addname=None, stats = None,
                 ignore_entries=[], on_each_dir=None, parent=None):
        self.parent = parent
        if stats is None:
            stats = ScanStats()
        Scan.__init__(self, path, addname, "DIR", stats)
        self.dbf = DbFile(os.path.join(self.path, '.shamo'), ENTRY_DM)

        child_entries = []

        def read_entries():
            if self.dbf.exists():
                try:
                    q = self.dbf.select('entry', {}, where='1=1')
                    return {r['name']: r for r in q}
                except:
                    pass
            return {}

        def store_entries(entries):
            try:
                with Session(self.dbf) as session:
                    if not session.has_table('entry'):
                        self.dbf.create_db(session=session)
                    self.dbf.delete('entry', {}, where='1=1',
                                    session=session)
                    for e in entries:
                        self.dbf.insert('entry', e, session=session)
            except:
                # from traceback import print_exc
                # print_exc()
                log.warning('cannot store: ' + self.dbf.file)

        old_db_entries = read_entries()

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

        store_entries(self.new_db_entries)

        log.debug(u'{self.path} -> {self.udk}'.format(**locals()))

        if on_each_dir:
            on_each_dir(self)

REMOTE_DM= '''
    table:remote
      remote_id PK
      url_uuid UUID4
      url_text TEXT
      mount_session TEXT
      created TIMESTAMP INSERT_DT
'''


class Remote:
    def __init__(self, directory):
        self.path = os.path.abspath(directory)
        self.dbf = DbFile(os.path.join(self.path, '.shamo'), REMOTE_DM)

    def register(self, url, invitation=None, session=None):
        url_uuid = uuid.uuid4()
        storage = RemoteStorage(url)
        server_uuid = storage.register(url_uuid,
                             invitation=invitation,
                             meta={'mount_path': self.path})
        if server_uuid is not None:
            self.dbf.ensure_db()
            self.dbf.store('remote', quict(
                remote_id=1,
                _url_uuid=url_uuid,
                _url_text=url,
                _mount_session=quick_hash(server_uuid)
            ), session=session)

    def storage(self):
        remote = self.dbf.select_one('remote', quict(remote_id=1))
        if remote is None:
            raise ValueError('cannot backup, need register mount first')
        storage = RemoteStorage(remote['url_text'])
        resp = storage.login(remote['url_uuid'])
        if remote['mount_session'] != quick_hash(resp['server_uuid']):
            raise AssertionError('cannot validate server')
        storage.set_auth_session(resp['auth_session'])
        return storage

    def backup(self):
        with self.storage() as storage:
            def ensure_files_on_remote(dir_scan):
                bundles = { dir_scan.udk: dir_scan.bundle}
                mount_hash = dir_scan.udk if dir_scan.parent is None else None
                _, hashes_to_push = storage.store_directories(bundles, mount_hash)
                for h in hashes_to_push:
                    h = UDK.ensure_it(h)
                    name = dir_scan.bundle.get_name_by_udk(h)
                    fp = open(os.path.join(dir_scan.path,name), 'rb')
                    k = storage.write_content(fp)
                    if k != h:
                        raise AssertionError('%s != %s' % (h,k))
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
