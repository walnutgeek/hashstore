import os
import shutil
import datetime
import pylru

from hashstore.bakery import NotFoundError
from hashstore.bakery.ids import Cake
from hashstore.ndb import Dbf
from hashstore.utils import binary_type, ensure_bytes,ensure_directory

from sqlalchemy import func,select

import hashlib

from .content import ContentAddress, is_it_shard, Content
from ..ndb.models.shard import shard_meta, blob
from ..ndb.models.incoming import incoming_meta, incoming

import logging

log = logging.getLogger(__name__)


class Lookup:
    def __init__(self, store, file_id):
        self.size = None
        self.created_dt = None
        self.file_id = file_id
        self.store = store

    def found(self):
        return self.size is not None and self.size >= 0

    def content(self):
        raise NotFoundError


NULL_LOOKUP = Lookup(None, None)


class ContentAddressLookup(Lookup):
    def __init__(self, store, file_id):
        Lookup.__init__(self,store,file_id)
        self.dir = os.path.join(store.root, self.file_id.shard_name)

    def blob_db(self):
        return self.store.blob_dbf(self.file_id.shard_name)


class CacheLookup(Lookup):
    def __init__(self, lookup, data):
        Lookup.__init__(self, lookup.store, lookup.file_id)
        self.size = lookup.size
        self.created_dt = lookup.created_dt
        self.data = data
        self.store.cache[self.file_id] = self

    def content(self):
        return Content(data=self.data)


class DbLookup(ContentAddressLookup):
    def __init__(self, store, file_id):
        ContentAddressLookup.__init__(self,store,file_id)
        blob_db = self.blob_db()
        if blob_db.exists():
            q = select([
                    func.char_length(blob.c.content).label('size'),
                    blob.c.created_dt
                ]).where(blob.c.file_id == self.file_id)
            result = blob_db.execute(q).fetchall()
            if len(result) == 1:
                self.size = result[0].size
                self.created_dt = result[0].created_dt
            elif len(result) != 0:
                raise AssertionError('PK?: %r' % self.file_id)

    def save_content(self, content):
        blob_db = self.blob_db()
        if not self.found():
            ensure_directory(self.dir)
            blob_db.ensure_db()
            blob_db.execute(blob.insert().values(
                    content = content,
                    file_id = self.file_id ))
            return True
        else:
            return False

    def content(self):
        row = self.blob_db().execute(
            select([blob.c.content])
            .where(blob.c.file_id == self.file_id)).fetchone()
        if self.size < self.store.cached_max_size:
            return CacheLookup(self, row.content).content()
        return Content(row.content)


class FileLookup(ContentAddressLookup):
    def __init__(self, store, file_id):
        ContentAddressLookup.__init__(self, store, file_id)
        self.file = os.path.join(self.dir, str(self.file_id) )
        try:
            (self.size, _, _, ctime) = os.stat(self.file)[6:]
            self.created_dt=datetime.datetime.utcfromtimestamp(ctime)
        except OSError as e:
            if e.errno != 2:  # No such file
                 raise # pragma: no cover

    def content(self):
        content = Content(file=self.file)
        if self.size < self.store.cached_max_size:
            return CacheLookup(self, content.stream().read()).content()
        return content



MAX_DB_BLOB_SIZE = 1 << 16

class LiteBackend:
    '''
    Storage backend that keep blobs in set of sharded directories.
    BLOBs smaller then db_limit will be stored in SQLite and bigger
    as individual files in directory

    '''
    def __init__(self, root, cache_size=1000, cached_max_size=80000):
        self.root = root
        self.cache = pylru.lrucache(cache_size)
        self.cached_max_size = cached_max_size
        self.incoming_dir = os.path.join(self.root,'incoming')
        ensure_directory(self.incoming_dir)
        self.in_db = Dbf(incoming_meta, self.incoming_dir + '.db')
        self.in_db.ensure_db()

    def blob_dbf(self, shard_name):
        path = os.path.join(self.root, shard_name, 'blob.db')
        return Dbf(shard_meta, path)

    @staticmethod
    def cache_lookup_factory(self, file_id):
        try:
            return self.cache[file_id]
        except KeyError:
            return NULL_LOOKUP

    def __iter__(self):
        for shard_name in filter(is_it_shard, os.listdir(self.root)):
            blob_db = self.blob_dbf(shard_name)
            if blob_db.exists():
                for row in blob_db.execute(select([blob.c.file_id])):
                    yield row.file_id
            shard_path = os.path.join(self.root, shard_name)
            for f in os.listdir(shard_path):
                if len(f) > 48:
                    yield ContentAddress(f)

    def get_content(self, k):
        return self.lookup(k).content().set_data_type(k)

    def lookup(self, cake_or_cadr):
        if isinstance(cake_or_cadr, Cake):
            file_id = ContentAddress(cake_or_cadr)
        else:
            file_id = ContentAddress.ensure_it(cake_or_cadr)
        for lookup_contr in (self.cache_lookup_factory,
                             FileLookup, DbLookup):
            l = lookup_contr(self, file_id)
            if l.found():
                return l
        return NULL_LOOKUP

    def writer(self):
        return ContentWriter(self)


class IncomingFile:
    def __init__(self, backend):
        self.backend = backend
        rp = self.backend.in_db.execute( incoming.insert())
        self.incoming_id = rp.lastrowid
        self.file = os.path.join(self.backend.incoming_dir,
                                 '%d.tmp' % self.incoming_id)
        self.fd = open(self.file, 'wb')

    def write(self, input):
        return self.fd.write(input)

    def close(self, lookup):
        new = not lookup.found()
        self.fd.close()
        self.fd = None
        if new:
            ensure_directory(lookup.dir)
            log.debug('mv %s %s' % (self.file, lookup.file))
            shutil.move(self.file, lookup.file)
        else:
            log.debug('rm %s' % self.file)
            os.remove(self.file)
        self.backend.in_db.execute(
            incoming.update().values(new=new,
                                     file_id=lookup.file_id)
                .where( incoming.c.incoming_id == self.incoming_id))


class ContentWriter:
    def __init__(self, backend):
        self.backend = backend
        self.buffer = binary_type()
        self.incoming_file = None
        self.digest = hashlib.sha256()
        self.file_id = None

    def write(self, content, done=False):
        if not isinstance(content,binary_type):
            raise AssertionError('expecting bytes, got: %s %r' %
                                 (type(content),content))
        content = ensure_bytes(content)
        self.digest.update(content)
        if self.buffer is not None:
            if MAX_DB_BLOB_SIZE > (len(self.buffer) + len(content)):
                self.buffer += content
            else:
                self.incoming_file = IncomingFile(self.backend)
                if len(self.buffer) > 0:
                    self.incoming_file.write(self.buffer)
                self.buffer = None
        if self.buffer is None:
            self.incoming_file.write(content)
        if done:
            return self.done()

    def done(self):
        if self.file_id is None:
            self.file_id = ContentAddress(self.digest)
            if self.buffer is not None:
                lookup = DbLookup(self.backend, self.file_id)
                lookup.save_content(self.buffer)
                self.buffer = None
            elif self.incoming_file is not None:
                file_lookup = FileLookup(self.backend, self.file_id)
                self.incoming_file.close(file_lookup)
                self.incoming_file = None
            else:
                raise AssertionError('what else: %r' % self.file_id )
        return self.file_id

