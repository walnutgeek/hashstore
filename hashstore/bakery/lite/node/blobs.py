import os
import shutil
import datetime
from typing import Union

import pylru
from hashstore.utils.db import Dbf
from hashstore.utils.fio import ensure_directory
from hashstore.kernel.hashing import (is_it_shard, Hasher)
from sqlalchemy import func, select
from hashstore.kernel.bakery import (NotFoundError, CakeRole,
                              Content, Cake)
from . import (blob_meta, blob,
               incoming_meta, incoming,
               ContentAddress, MAX_NUM_OF_SHARDS)
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

    def _content(self, role: CakeRole)->Content:
        raise NotFoundError

    def content(self, role: CakeRole)->Content:
        content = self._content(role)
        content.size = self.size
        content.created_dt = self.created_dt
        return content


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

    def _content(self, role: CakeRole)->Content:
        return Content.from_data_and_role(
            role=role, data=self.data)


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

    def _content(self, role: CakeRole)->Content:
        row = self.blob_db().execute(
            select([blob.c.content])
            .where(blob.c.file_id == self.file_id)).fetchone()
        if self.size < self.store.cached_max_size:
            return CacheLookup(self, row.content)._content(role)
        return Content.from_data_and_role(
            role=role, data=row.content)


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

    def _content(self, role: CakeRole)->Content:
        content = Content.from_data_and_role(
            file=self.file, role=role)
        if self.size < self.store.cached_max_size:
            return CacheLookup(self, content.stream().read())._content(role)
        return content


MAX_DB_BLOB_SIZE = 1 << 16


class BlobStore:
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
        return Dbf(blob_meta, path)

    @staticmethod
    def cache_lookup_factory(self, file_id):
        try:
            return self.cache[file_id]
        except KeyError:
            return NULL_LOOKUP

    def __iter__(self):
        for shard_name in filter(
                lambda s: is_it_shard(s,MAX_NUM_OF_SHARDS),
                os.listdir(self.root)):
            blob_db = self.blob_dbf(shard_name)
            if blob_db.exists():
                for row in blob_db.execute(select([blob.c.file_id])):
                    yield row.file_id
            shard_path = os.path.join(self.root, shard_name)
            for f in os.listdir(shard_path):
                if len(f) > 48:
                    yield ContentAddress(f)

    def get_content(self, k:Union[Cake,ContentAddress]):
        role = k.header.role if isinstance(k, Cake) else CakeRole.SYNAPSE
        return self.lookup(k).content(role)

    def lookup(self, cake_or_cadr):
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
        self.buffer = bytes()
        self.incoming_file = None
        self.hasher = Hasher()
        self.file_id = None

    def write(self, content, done=False):
        if not isinstance(content,bytes):
            raise AssertionError(
                f'expecting bytes, got: {type(content)} {content!r}')
        self.hasher.update(content)
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
            self.file_id = ContentAddress(self.hasher)
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

