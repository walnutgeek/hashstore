from hashstore.db import _session, DbFile
from hashstore.udk import process_stream,\
    UDK,UDKBundle,UdkSet,quick_hash
from hashstore.storage import RemoteStorage
from hashstore.utils import quict, path_split_all, reraise_with_msg, \
    read_in_chunks, ensure_directory
from collections import defaultdict
import os
import fnmatch
import uuid

import logging
log = logging.getLogger(__name__)


def pick_ignore_specs(n):
    return n in ['.gitignore', '.ignore']


class IgnoreEntry:
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
            for l in open(os.path.join(cur_dir,spec)).readlines():
                l = l.strip()
                if l != '' and l[0] != '#':
                    ignore_entries.append(IgnoreEntry(cur_dir, l))
        return ignore_entries
    else:
        return initial_ignore_entries


def check_if_path_should_be_ignored(ignore_entries, path, isdir):
    return any(entry.should_ignore_path(path,isdir)
               for entry in ignore_entries )


class MountDB(DbFile):
    def __init__(self, directory, file='.shamo',scan_now = False):
        self.dir = os.path.abspath(directory)
        DbFile.__init__(self, os.path.join(self.dir, file))
        self.last_hash = None
        self.last_id = None
        if scan_now:
            self.scan()

    def datamodel(self):
        '''
        table:remote
          remote_id PK
          url_uuid UUID4
          url_text TEXT
          mount_session TEXT
          created TIMESTAMP INSERT_DT
          last_push_id FK(push) NULL
        table:push
          push_id PK
          scan_id FK(scan)
          directory_synched INT NULL
          files_synched INT NULL
          started TIMESTAMP INSERT_DT
          complited TIMESTAMP UPDATE_DT NULL
          hash UDK NULL
        table:scan
          scan_id PK
          dir TEXT NOT NULL
          started TIMESTAMP INSERT_DT
          complited TIMESTAMP UPDATE_DT
          size INTEGER
          hash UDK
          root_file_id FK(file) NULL
        table:file
          file_id PK
          scan_id FK(scan) NOT NULL
          name TEXT AK(name_parent)
          parent_id AK(name_parent) FK(file) NULL
          file_type TEXT OPTIONS('DIR','FILE')
          hash UDK
          size INTEGER
          cumulative_size INTEGER
          time_hash TEXT
          mod_time TIMESTAMP
        '''
        return self.datamodel.__doc__


    @_session
    def scan(self, scanned_dir = None, session = None):
        if scanned_dir is None:
            scanned_dir = self.dir
        self.ensure_db()
        scan_rec = self.insert('scan', quict(
            dir=scanned_dir,
        ),session=session)
        scan_id = scan_rec['_scan_id']
        root_rec = self.insert('file', quict(
            name='/',
            scan_id=scan_id,
            parent_id=None,
            file_type='DIR'
        ),session=session)

        def read_dir(cur_dir, cur_rec, ignore_entries):

            def ignore_files(n):
                if n in ['.svn', '.git', '.DS_Store', '.vol',
                         '.hotfiles.btree', '.ssh' ]:
                    return False
                for t in ['.shamo', '.backup', '.Spotlight', '._', '.Trash']:
                    if n.startswith(t):
                        return False
                return True
            files = sorted(filter(ignore_files, os.listdir(cur_dir)))
            ignore_entries = parse_ignore_specs(cur_dir, files, ignore_entries)
            dir_content = UDKBundle()
            cur_id = cur_rec['_file_id']
            cumulative_size = 0
            for f in files:
                path_to_file = os.path.join(cur_dir, f)
                if os.path.islink(path_to_file):
                    continue
                isdir = os.path.isdir(path_to_file)
                if check_if_path_should_be_ignored(ignore_entries,
                                                   path_to_file, isdir):
                    continue
                if isdir:
                    dir_rec = self.insert('file', quict(
                        name=f,
                        parent_id=cur_id,
                        scan_id=scan_id,
                        file_type='DIR'
                    ),session=session)
                    k,size = read_dir(path_to_file, dir_rec, ignore_entries)
                else:
                    digest, size, inline_data = process_stream(open(path_to_file,'rb'))
                    k = UDK.from_digest_and_inline_data(digest, inline_data)
                    rec = self.insert('file', quict(
                        name=f,
                        parent_id=cur_id,
                        scan_id=scan_id,
                        file_type='FILE',
                        size=size,
                        cumulative_size=size,
                        hash=str(k),
                    ),session=session)
                cumulative_size += size
                dir_content[f] = k
            udk, size, content = dir_content.udk_content()
            cumulative_size += size
            self.update('file', quict(
                file_id=cur_id,
                _size=size,
                _cumulative_size=cumulative_size,
                _hash=str(udk)
            ), session=session)
            session.commit()
            return udk, cumulative_size
        scan_hash,size = read_dir(scanned_dir, root_rec, [])
        self.update('scan', quict(
            _hash=scan_hash,
            _size=size,
            scan_id=scan_id,
            _root_file_id=(root_rec['_file_id'])
        ), session=session)
        self.last_hash = scan_hash
        self.last_id = scan_id
        return scan_id, scan_hash

    def scan_select(self,scan_id = None):
        if scan_id is None:
            scan_id = self.last_id
        return self.select('file', {'scan_id':scan_id}, ' order by parent_id, name')

    @_session
    def register(self, url, invitation=None, session=None):
        url_uuid = uuid.uuid4()
        storage = RemoteStorage(url)
        server_uuid = storage.register(url_uuid,
                             invitation=invitation,
                             meta={'mount_path': self.dir})
        if server_uuid is not None:
            self.ensure_db()
            self.store('remote', quict(
                remote_id=1,
                _url_uuid=url_uuid,
                _url_text=url,
                _mount_session=quick_hash(server_uuid)
            ), session=session)

    def backup(self):
        def action(storage,session):
            self.push_files(storage, session=session)
        self._run_against_storage(action)
        return self.last_hash

    def restore(self, key, path):

        def action(storage,session):
            def restore_inner( k, p):
                k = UDK.ensure_it(k)
                if k.named_udk_bundle:
                    content = storage.get_content(k)
                    log.info('%r' % content)
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
        self._run_against_storage(action)


    @_session
    def _run_against_storage(self, activity, session=None):
        remote = self.select_one('remote', quict(remote_id=1),
                                 session=session)
        if remote is None:
            raise ValueError('cannot backup, need register mount first')
        storage = RemoteStorage(remote['url_text'])
        resp = storage.login(remote['url_uuid'])
        log.debug(
            (remote['mount_session'], quick_hash(resp['server_uuid'])))
        if remote['mount_session'] != quick_hash(resp['server_uuid']):
            raise AssertionError('cannot validate server')
        storage.set_auth_session(resp['auth_session'])
        result = activity(storage,session)
        storage.logout()
        return result

    @_session
    def push_files(self, storage, session=None):
        rescan_hash = None
        while True:
            self.scan(session=session)
            if rescan_hash == self.last_hash:
                break
            push_rec = self.insert('push', quict(
                scan_id=self.last_id,
                hash=self.last_hash,
            ), session=session)
            tree = ScanTree(self)
            count_synched_dirs, hashes_to_push = storage.store_directories(
                tree.directories)
            push_files = len(hashes_to_push) > 0
            if push_files:
                hashes_to_push = UdkSet.ensure_it(hashes_to_push)
                for h in hashes_to_push:
                    f = tree.file_path(h)
                    fp = open(os.path.join(self.dir, f), 'rb')
                    stored_as = storage.write_content(fp)
                    if stored_as != h:
                        log.warn('scaned: %s, but stored as: %s' % (f, stored_as))
            self.update('push', quict(
                push_id=push_rec['_push_id'],
                _directory_synched=count_synched_dirs,
                _files_synched=len(hashes_to_push)
            ), session=session)
            if not push_files:
                break
            rescan_hash = self.last_hash




class ScanTree:
    def __init__(self, mount, scan_id=None):
        self.directories = defaultdict(UDKBundle)
        self.file_to_dir_hashes = {}
        id_to_hash = {}
        for r in mount.scan_select(scan_id):
            file_id, parent_id, file_hash, file_name = map(r.get, (
                'file_id','parent_id','hash','name'))
            id_to_hash[file_id]= file_hash
            if parent_id is not None:
                parent_hash = id_to_hash[parent_id]
                self.directories[parent_hash][file_name] = file_hash
                self.file_to_dir_hashes[file_hash] = parent_hash
            else:
                self.k = UDK.ensure_it(file_hash)

    def file_path(self, h):
        try:
            def file_names(file_hash):
                while file_hash in self.file_to_dir_hashes:
                    dir_hash = self.file_to_dir_hashes[file_hash]
                    yield self.directories[dir_hash].get_name_by_udk(file_hash)
                    file_hash = dir_hash

            l = list(file_names(h))
            l.reverse()
            path = os.path.join(*l)
            # log.info('hash: %s path:%s ' % (h, path))
            return path
        except:
            reraise_with_msg('%s' % str(h) )




