import hashlib
import os
import shutil
import datetime
import six
import hashstore.db as db
import logging
from hashstore.utils import quict,ensure_directory,ensure_bytes,read_in_chunks
import hashstore.udk as udk

SHARD_SIZE = 3
SQLITE_EXT = '.sqlite3'

log = logging.getLogger(__name__)

def ensure_udk(k):
    return udk.UDK.ensure_it(k).strip_bundle()


class Lookup:
    def __init__(self, store, sha):
        self.size = None
        self.created_dt = None
        self.sha = sha
        self.store = store

    def found(self):
        return self.size is not None and self.size >= 0

    def stream(self):
        return None

    def delete(self):
        return False

NULL_LOOKUP = Lookup(None, None)

class InlineLookup(Lookup):
    def __init__(self, store, sha):
        Lookup.__init__(self,store,sha)
        if self.sha.has_data():
            self.size = len(self.sha.data())

    def stream(self):
        return six.BytesIO(self.sha.data())


def _blob_dbf_instance(file):
    '''
    table:blob
      blob_id PK
      sha UDK AK
      content BIG
      created_dt INSERT_DT
    '''
    return db.DbFile(file, _blob_dbf_instance.__doc__)

def _blob_db_filename(directory):
    return os.path.join(directory, 'blob' + SQLITE_EXT)

def _blob_dbf(store, sha):
    directory = os.path.join(store.root, sha.k[:SHARD_SIZE])
    filename = _blob_db_filename(directory)
    dbf = _blob_dbf_instance(filename)
    return dbf


class DbLookup(Lookup):
    def __init__(self, store, sha):
        Lookup.__init__(self,store,sha)
        self.dbf = _blob_dbf(store,sha)
        if self.dbf.exists():
            d = self.dbf.select_one(
                'blob', quict(sha=self.sha.k),
                selectors='length(content) size, created_dt')
            if d is not None:
                for k in d:
                    setattr(self,k,d[k])

    def save_content(self, content):
        if not self.found():
            self.dbf.ensure_db(compare=False)
            self.dbf.insert( 'blob',
                quict(sha=self.sha, content=db.to_blob(content)) )

    def stream(self):
        if not self.found():
            return None
        row = self.dbf.select_one(
                'blob', quict(sha=self.sha.k), select='BIG')
        return six.BytesIO(row['content'])

    def delete(self):
        if self.found():
            self.dbf.delete( 'blob', quict(sha=self.sha) )
            return True
        return False


class FileLookup(Lookup):
    def __init__(self, store, sha):
        Lookup.__init__(self,store,sha)
        self.dir = os.path.join(store.root, sha.k[:SHARD_SIZE] )
        self.file = os.path.join(self.dir, sha.k[SHARD_SIZE:])
        try:
            (self.size, _, _, ctime) = os.stat(self.file)[6:]
            self.created_dt=datetime.datetime.utcfromtimestamp(ctime)
        except OSError as e:
            if e.errno != 2:  # No such file
                 raise

    def stream(self):
        return open(self.file,'rb')

    def delete(self):
        if self.found():
            os.remove( self.file )
            return True
        return False


class IncommingFile:
    def __init__(self, store):
        self.store = store
        self.incoming_id = self.store.dbf.insert('incoming', {})['_incoming_id']
        self.file = os.path.join(self.store.incoming, '%d.tmp' % self.incoming_id)
        self.fd = open(self.file, 'wb')

    def save_as(self, k):
        self.fd.close()
        self.fd = None
        dest = FileLookup(self.store,ensure_udk(k))
        new = not dest.found()
        if new:
            ensure_directory(dest.dir)
            log.debug('mv %s %s' % (self.file, dest.file))
            shutil.move(self.file, dest.file)
        else:
            log.debug('rm %s' % self.file)
            os.remove(self.file)
        self.store.dbf.update( 'incoming',
            quict(incoming_id=self.incoming_id,
                  _new=new, _sha=dest.sha))
        return dest.sha


class HashStore:
    def __init__(self, root, inline_data_in_udk=True):
        self.root = root
        self.inline_data_in_udk = inline_data_in_udk
        self.incoming = os.path.join(root,'incoming')
        ensure_directory(self.incoming)
        model = '''
        table:incoming
            incoming_id PK
            sha UDK
            new BOOL
            created_dt INSERT_DT
            updated_dt UPDATE_DT
        table:mount
            mount_id UUID4 PK
            mount_session TEXT AK
            created_dt INSERT_DT
        table:invitation
            invitation_id UUID4 PK
            invitation_body TEXT
            used BOOL
            created_dt INSERT_DT
            update_dt UPDATE_DT NULL
        table:push_session
            push_session_id UUID4 PK
            mount_id FK(mount)
            active BOOL
            created_dt INSERT_DT
            update_dt UPDATE_DT NULL
        table:push
            push_id PK
            push_session_id FK(push_session)
            mount_hash UDK
            created_dt INSERT_DT
        '''
        self.dbf = db.DbFile(self.incoming + SQLITE_EXT,
                             model).ensure_db()

    def iterate_udks(self):
        for f in os.listdir(self.root):
            shard_path = os.path.join(self.root,f)
            if os.path.isdir(shard_path) and len(f) == SHARD_SIZE:
                for e in os.listdir(shard_path):
                    if len(e) == 64 - SHARD_SIZE:
                        yield udk.UDK(f+e)
                dbf_file = _blob_db_filename(shard_path)
                if os.path.isfile(dbf_file):
                    dbf = _blob_dbf_instance(dbf_file)
                    session = db.Session(dbf)
                    for row in session.query('select sha from blob'):
                        yield udk.UDK(row[0])
                    session.close()

    def create_invitation(self, body=None):
        return self.dbf.insert("invitation", quict(
            used = False,
            invitation_body=body
        ))['_invitation_id']

    def register(self, remote_uuid, invitation, mount_meta=None):
        rc = self.dbf.update('invitation', quict(
            invitation_id = invitation,
            used=False,
            _used=True,
        ))
        if rc == 1:
            mount_session = udk.quick_hash(remote_uuid)
            return self.dbf.resolve_ak('mount', mount_session)
        return None

    def login(self, remote_uuid):
        mount_session = udk.quick_hash(remote_uuid)
        mount = self.dbf.select_one('mount', quict(mount_session=mount_session))
        if mount is not None:
            mount_id = mount['mount_id']
            push_session = self.dbf.insert('push_session', quict(mount_id=mount_id, active=True))
            return push_session

    def logout(self, push_session_id):
        return self.dbf.update('push_session', quict(
            push_session_id = push_session_id, _active = False))

    def check_push_session(self, push_session_id):
        n = self.dbf.select_one('push_session', quict(
            push_session_id = push_session_id, active = True))
        if n is not None:
            raise ValueError("authetification error")

    def log_push(self,push_session_id, mount_hash):
        self.dbf.insert('push', quict(push_session_id=push_session_id,
                                      mount_hash=mount_hash))

    def write_content(self, fp):
        w = self.writer()
        for buffer in read_in_chunks(fp):
            w.write(buffer)
        return w.done()

    def store_directories(self, directories, push_session_id = None, mount_hash=None):
        if push_session_id is not None and mount_hash is not None:
            self.log_push(push_session_id,mount_hash)
        unseen_file_hashes = udk.UdkSet()
        dirs_stored = udk.UdkSet()
        dirs_mismatch = udk.UdkSet()
        for dir_hash, dir_contents in six.iteritems(directories):
            dir_hash = udk.UDK.ensure_it(dir_hash)
            dir_contents = udk.NamedUDKs.ensure_it(dir_contents)
            dir_content_dump = str(dir_contents)
            lookup = self.lookup(dir_hash)
            if not lookup.found() :
                w = self.writer()
                w.write(dir_content_dump, done=True)
                lookup = self.lookup(dir_hash)
                if lookup.found() :
                    dirs_stored.add(dir_hash)
                else:
                    dirs_mismatch.add(dir_hash)
            for file_name in dir_contents:
                file_hash = dir_contents[file_name]
                if not file_hash.named_udk_bundle:
                    lookup = self.lookup(file_hash)
                    if not lookup.found():
                        unseen_file_hashes.add(file_hash)
        if len(dirs_mismatch) > 0:
            raise ValueError('could not store directories: %r' % dirs_mismatch)
        return len(dirs_stored), unseen_file_hashes

    def lookup(self, k):
        k = ensure_udk(k)
        for lookup_contr in (InlineLookup, FileLookup, DbLookup):
            l = lookup_contr(self, k)
            if l.found():
                return l
        return NULL_LOOKUP

    def get_content(self, k):
        return self.lookup(k).stream()

    def delete(self, k):
        return self.lookup(k).delete()

    def writer(self_store):
        class Writer:
            def __init__(self):
                self.store = self_store
                self.buffer = six.binary_type()
                self.incoming_file = None
                self.digest = hashlib.sha256()
                self.k = None

            def write(self,content,done = False):
                content = ensure_bytes(content)
                self.digest.update(content)
                if self.buffer is not None:
                    if udk.db_max > len(self.buffer) + len(content):
                        self.buffer += content
                    else:
                        self.incoming_file = IncommingFile(self.store)
                        if len(self.buffer) > 0:
                            self.incoming_file.fd.write(self.buffer)
                        self.buffer = None
                if self.buffer is None:
                    self.incoming_file.fd.write(content)
                if done:
                    return self.done()

            def done(self):
                if self.buffer is not None:
                    self.k = udk.UDK_from_digest_and_inline_data(self.digest,self.buffer,self.store.inline_data_in_udk)
                    if self.k.has_data():
                        log.debug('no need to store: %s' % self.k)
                    else:
                        DbLookup(self_store, self.k).save_content(self.buffer)
                    self.buffer = None
                elif self.incoming_file is not None:
                    self.k = self.incoming_file.save_as(self.digest.hexdigest())
                    self.incoming_file = None
                if self.k is None:
                    raise AssertionError('k has to be set at this point')
                return self.k

        return Writer()



