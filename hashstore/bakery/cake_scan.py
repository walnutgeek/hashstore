from hashstore.utils import ensure_string, failback, read_in_chunks, \
    reraise_with_msg, ensure_directory, utf8_reader
from hashstore.utils.ignore_file import ignore_files, \
    parse_ignore_specs, check_if_path_should_be_ignored
from hashstore.bakery import Cake, process_stream, CakeRack, \
    CakePath
from hashstore.ndb.models.scan import ScanBase, DirEntry, DirKey, \
    FileType
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


class CakeEntries:

    def __init__(self, path):
        self.path = path
        self.dbf = Dbf(ScanBase.metadata, os.path.join(path, '.cake_entries'))
        self._dir_key = None

    def dir_key(self, force_change_fn = None):
        if self._dir_key is None or force_change_fn is not None:
            self.dbf.ensure_db()
            with self.dbf.session_scope() as session:
                self._dir_key = session.query(DirKey).one_or_none()
                if self._dir_key is None:
                    self._dir_key = DirKey()
                    session.add(self._dir_key)
                if force_change_fn is not None:
                    force_change_fn(self._dir_key)
        return self._dir_key

    def set_backup_path(self, backup_path):
        def update_path(dir_key):
            dir_key.last_backup_path = CakePath.ensure_it(backup_path)
        self.dir_key(update_path)

    def total(self):
        return sum(f.size for f in self.directory_usage())

    def directory_usage(self):
        if not(self.dbf.exists()):
            raise ValueError(f'{self.path} was not scanned')
        with self.dbf.session_scope() as session:
            return session.query(DirEntry)\
                .order_by(desc(DirEntry.size), DirEntry.name).all()

    def bundle(self):
        return build_bundle(self.directory_usage())

    def store_entries(self, entries):
        try:
            self.dir_key()
            with self.dbf.session_scope() as session:
                new_names = { e.name for e in entries}
                for e in session.query(DirEntry).all():
                    if e.name not in new_names:
                        session.delete(e)
                for e in entries:
                    session.merge(e)
        except:
            from traceback import print_exc
            print_exc()
            log.warning(f'cannot store: {self.dbf.path}')


class ScanPath:
    def __init__(self, fs_path, addname=None , remote_path = None ):
        fs_path=ensure_string(fs_path)
        if addname is None:
            name = os.path.basename(fs_path)
        else:
            addname = ensure_string(addname)
            fs_path = os.path.join(fs_path, addname)
            name = addname
        self.fs_path = os.path.abspath(fs_path)
        self.name = name
        self._cake_entries = None
        self.remote_path = remote_path

    def child(self, f):
        remote_path = None if self.remote_path is None else \
            self.remote_path.child(f)
        return ScanPath(self.fs_path, f, remote_path=remote_path)

    def set_remote_path(self, remote_path):
        self.remote_path = remote_path

    def cake_entries(self):
        if self._cake_entries is None:
            self._cake_entries = CakeEntries(self.fs_path)
        return self._cake_entries

    def store_remote_path(self):
        if self.remote_path is not None:
            self.cake_entries().set_backup_path(self.remote_path)


class Scan:
    def __init__(self, path, file_type, stats):
        self.path = path
        self.file_type = file_type
        self.stats = stats
        self.entry = DirEntry(name=self.path.name, file_type=file_type)

    def __str__(self):
        return str(self.entry)


class FileScan(Scan):
    def __init__(self, path, from_db, stats):
        Scan.__init__(self, path, FileType.FILE, stats)
        stat = os.stat(self.path.fs_path)
        self.entry.modtime = stat.st_mtime
        self.entry.size = stat.st_size
        if stats.force_rehash or from_db is None \
                or self.entry.modtime > from_db.modtime:
            self.stats.increment_count()
            digest, inline_data = process_stream(
                open(self.path.fs_path, 'rb'),
                on_chunk=self.stats.count_bytes
            )
            self.entry.cake = Cake.from_digest_and_inline_data(
                digest, inline_data)
        else:
            self.entry.cake = from_db.cake


def build_bundle(entries):
    bundle = CakeRack()
    for e in entries:
        bundle[e.name] = e.cake
    return bundle


class DirScan(Scan):

    def __init__(self, path,  stats=None,
                 ignore_entries=[], on_each_dir=None, parent=None):
        self.parent = parent
        if stats is None:
            stats = ScanStats()
        Scan.__init__(self, path,  FileType.DIR, stats)
        child_entries = []

        old_db_entries = {e.name: e for e in failback(
            self.path.cake_entries().directory_usage, [])()}

        files = sorted(filter(ignore_files,
                              os.listdir(self.path.fs_path)))
        ignore_entries = parse_ignore_specs(self.path.fs_path, files,
                                            ignore_entries)

        for f in files:
            path_to_file = os.path.join(self.path.fs_path, f)
            if os.path.islink(path_to_file):
                continue
            isdir = os.path.isdir(path_to_file)
            if check_if_path_should_be_ignored(ignore_entries,
                                               path_to_file, isdir):
                continue

            try:
                path_child = self.path.child(f)
                if isdir:
                    entry = DirScan(path_child, self.stats,
                                    ignore_entries, on_each_dir,
                                    parent=self)
                else:
                    entry = FileScan(path_child,
                                     old_db_entries.get(f, None),
                                     self.stats)
            except (OSError,IOError):
                log.warning(f'cannot read: {self.path}/{f}')
            else:
                child_entries.append(entry)

        self.new_db_entries = [e.entry for e in child_entries]
        self.bundle = build_bundle(self.new_db_entries)
        self.entry.cake = self.bundle.cake()
        self.entry.size = sum(e.entry.size for e in child_entries) + \
                          self.bundle.size()

        stat = os.stat(self.path.fs_path)

        self.entry.modtime = stat.st_mtime
        if len(child_entries) > 0:
            youngest_file = max(e.entry.modtime for e in child_entries)
            self.entry.modtime = max(self.entry.modtime, youngest_file)

        self.path.cake_entries().store_entries(self.new_db_entries)

        log.debug(f'{self.path} -> {self.entry.cake}')

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
        output = f'{self.pct_value()} {directory}'
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
        if self.total is None or self.total == 0.:
            return '?'
        pct_format = '%3.2f%%' if self.terminal else '%3d%%'
        return pct_format % (100 * float(self.current)/self.total)


def backup(scan_path, access):
    progress = Progress(scan_path.fs_path)

    def ensure_files_in_store(dir_scan):
        bundles = [(
            str(dir_scan.path.remote_path),
            str(dir_scan.entry.cake),
            dir_scan.bundle
        ),]
        store_dir = True
        while store_dir:
            _, hashes_to_push = access.store_directories(directories=bundles)
            store_dir = False
            for h in hashes_to_push:
                h = Cake.ensure_it(h)
                name = dir_scan.bundle.get_name_by_cake(h)
                file = os.path.join(dir_scan.path.fs_path, name)
                fp = open(file, 'rb')
                stored = access.write_content(fp)
                if not stored.match(h):
                    log.info('path:%s, %s != %s' % (file, h, stored))
                    dir_scan.bundle[name] = Cake(stored.hash_bytes(),
                                                 h.type,
                                                 h.role)
                    dir_scan.udk = dir_scan.bundle.cake()
                    store_dir = True
        dir_scan.path.store_remote_path()
        progress.just_processed(sum(f.size for f in dir_scan.new_db_entries
                                    if f.file_type == FileType.FILE)
                                + dir_scan.bundle.size(),
                                dir_scan.path.fs_path)
    root_scan = DirScan(scan_path, on_each_dir=ensure_files_in_store)
    dir_id = root_scan.path.cake_entries().dir_key().id
    latest_cake = root_scan.entry.cake
    return dir_id, latest_cake


def pull(store, cakepath, path):
    def restore_inner(cakepath, path):
        content = store.get_content(cake_or_path=cakepath)
        try:
            bundle = CakeRack(utf8_reader(content.stream()))
        except:
            data = content.get_data()
            reraise_with_msg('Cake: {cakepath} {data}'.format(**locals()))
        ensure_directory(path)
        for child_name in bundle:
            file_path = os.path.join(path, child_name)
            child_path = cakepath.child(child_name)
            neuron = bundle.is_neuron(child_name)
            if neuron:
                restore_inner(child_path, file_path)
            else:
                file_cake = bundle[child_name]
                try:
                    out_fp = open(file_path, "wb")
                    in_fp = store.get_content(file_cake).stream()
                    for chunk in read_in_chunks(in_fp):
                        out_fp.write(chunk)
                    in_fp.close()
                    out_fp.close()
                except:
                    reraise_with_msg( "%s -> %s" % (file_cake, file_path))
        return bundle.cake() if bundle.is_defined() else None
    return restore_inner(cakepath, path)


