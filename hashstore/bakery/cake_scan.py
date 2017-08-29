import six
          mm,,,,,,,, ,,,,,,,,,,,,,,,,,,  from hashstore.utils import ensure_unicode, failback, read_in_chunks, \
    reraise_with_msg, ensure_directory
from hashstore.utils.ignore_file import ignore_files, \
    parse_ignore_specs, check_if_path_should_be_ignored
from hashstore.bakery.ids import Cake, process_stream, NamedCAKes, DataType
from hashstore.ndb.models.scan import ScanBase, DirEntry, DirKey, \
    FileType
from hashstore.ndb.models.client_config import ClientConfigBase, \
    ClientKey, Server
from sqlalchemy import desc

from hashstore.ndb import Dbf

import os
import sys

import logging
log = logging.getLogger(__name__)


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
            name = os.path.basename(path)
        else:
            addname = ensure_unicode(addname)
            path = os.path.join(path, addname)
            name = addname
        self.path = os.path.abspath(path)
        self.entry = DirEntry(name=name, file_type=file_type)

    def __str__(self):
        return str(self.entry)


class FileScan(Scan):
    def __init__(self, path, addname, from_db, stats):
        Scan.__init__(self, path, addname, FileType.FILE, stats)
        stat = os.stat(self.path)
        self.entry.modtime = stat.st_mtime
        self.entry.size = stat.st_size
        if stats.force_rehash or from_db is None \
                or self.entry.modtime > from_db.modtime:
            self.stats.increment_count()
            digest, _, inline_data = process_stream(
                open(self.path, 'rb'),
                process_buffer=self.stats.count_bytes
            )
            self.entry.cake = Cake.from_digest_and_inline_data(digest, inline_data)
        else:
            self.entry.cake = from_db.cake

def build_bundle(entries):
    bundle = NamedCAKes()
    for e in entries:
        bundle[e.name] = e.cake
    return bundle


class CakeEntries:
    def __init__(self, path):
        self.dbf = Dbf(ScanBase.metadata, os.path.join(path, '.cake_entries'))
        self._dir_key = None
        if self.dbf.exists():
            with self.dbf.session_scope() as session:
                self.dir_key(session)

    def dir_key(self, session=None):
        if self._dir_key is None:
            self.dbf.ensure_db()
            self._dir_key = session.query(DirKey).one_or_none()
            if self._dir_key is None:
                self._dir_key = DirKey()
                session.merge(self._dir_key)
        return self._dir_key

    def total(self):
        return sum(f.size for f in self.directory_usage())

    def directory_usage(self):
        if not(self.dbf.exists()):
            raise ValueError('%r was not scanned' % self.path)
        with self.dbf.session_scope() as session:
            return session.query(DirEntry)\
                .order_by(desc(DirEntry.size), DirEntry.name).all()

    def bundle(self):
        return build_bundle(self.directory_usage())


    def store_entries(self, entries):
        try:
            with self.dbf.session_scope() as session:
                self.dir_key(session=session)
                new_names = { e.name for e in entries}
                for e in session.query(DirEntry).all():
                    if e.name not in new_names:
                        session.delete(e)
                for e in entries:
                    session.merge(e)
        except:
            from traceback import print_exc
            print_exc()
            log.warning('cannot store: ' + self.dbf.path)


class DirScan(CakeEntries, Scan):
    def __init__(self, path, addname=None, stats = None,
                 ignore_entries=[], on_each_dir=None, parent=None):
        self.parent = parent
        if stats is None:
            stats = ScanStats()
        Scan.__init__(self, path, addname, FileType.DIR, stats)
        CakeEntries.__init__(self,self.path)

        child_entries = []

        old_db_entries = {e.name: e for e in
                          failback(self.directory_usage, [])()}

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

        self.new_db_entries =[e.entry for e in child_entries]
        self.bundle = build_bundle(self.new_db_entries)
        self.entry.cake = self.bundle.cake()
        self.entry.size = sum(e.entry.size for e in child_entries) \
                    + self.bundle.size()

        stat = os.stat(self.path)

        self.entry.modtime = stat.st_mtime
        if len(child_entries) > 0:
            youngest_file = max(e.entry.modtime for e in child_entries)
            self.entry.modtime = max(self.entry.modtime, youngest_file)


        self.store_entries(self.new_db_entries)

        log.debug(u'{self.path} -> {self.entry.cake}'.format(**locals()))

        if on_each_dir:
            on_each_dir(self)


class Progress:
    def __init__(self,path):
        self.path = path
        try:
            self.total = CakeEntries(path).total()
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

def backup(path, storage):
    progress = Progress(path)

    def ensure_files_on_remote(dir_scan):
        bundles = { dir_scan.entry.cake : dir_scan.bundle}
        store_dir = True
        while store_dir:
            _, hashes_to_push = storage.store_directories(bundles)
            store_dir = False
            for h in hashes_to_push:
                h = Cake.ensure_it(h)
                name = dir_scan.bundle.get_name_by_cake(h)
                file = os.path.join(dir_scan.path, name)
                fp = open(file, 'rb')
                stored = storage.write_content(fp)
                if not stored.match(h):
                    log.info('path:%s, %s != %s' % (file, h, stored))
                    dir_scan.bundle[name] = Cake (stored.hash_bytes(),
                                                  h.key_structure,
                                                  h.data_type)
                    dir_scan.udk = dir_scan.bundle.cake()
                    store_dir = True
        progress.just_processed(sum(f.size for f in dir_scan.new_db_entries
                                    if f.file_type == FileType.FILE)
                                + dir_scan.bundle.size(), dir_scan.path)

    root_scan = DirScan(path,on_each_dir=ensure_files_on_remote)
    portal_id = root_scan.dir_key().id
    latest_cake = root_scan.entry.cake
    storage.create_portal(portal_id, latest_cake)
    return portal_id, latest_cake

def pull(store, key, path):
    def restore_inner( k, p):
        k = Cake.ensure_it(k)
        if k.data_type == DataType.BUNDLE:
            bundle = NamedCAKes(store.get_content(k))
            ensure_directory(p)
            for n in bundle:
                file_path = os.path.join(p, n)
                file_k = bundle[n]
                if file_k.data_type == DataType.BUNDLE:
                    restore_inner(file_k, file_path)
                else:
                    try:
                        out_fp = open(file_path, "wb")
                        in_fp = store.get_content(file_k)
                        for chunk in read_in_chunks(in_fp):
                            out_fp.write(chunk)
                        out_fp.close()
                    except:
                        reraise_with_msg(
                            "%s -> %s" % (file_k, file_path))
    restore_inner(key,path)

'''
class CakeClient:
    def __init__(self):
        home_config = os.path.join(os.environ['HOME'], '.cake_config')
        self.dbf = Dbf(ClientKey.metadata, home_config)



class Mount:
    def __init__(self, directory):
        self.path = os.path.abspath(directory)


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



'''

if __name__ == '__main__':
    import sys

    scan = DirScan(sys.argv[1])
    print('udk: %s\nhashed_counts: %s\nhashed_bytes: %s\n' %
          (scan.bundle.cake(), scan.stats.hashed_counts, scan.stats.hashed_bytes))
    # print(bundle.content())
