import os
import shutil
import datetime
import six

from hashstore.ids import Cake, KeyStructure, DataType
from hashstore.new_db import varchar_type,Dbf
from hashstore.utils import binary_type, ensure_bytes,ensure_directory

from sqlalchemy import func

import hashlib

from .content import ContentAddress, is_it_shard
from .shard_schema import shard_meta, catalog, blob
from .incoming_schema import incoming_meta, incoming

import logging
log = logging.getLogger(__name__)

class Lookup:
    def __init__(self, store, file_id, cake):
        self.size = None
        self.created_dt = None
        self.file_id = file_id
        self.store = store
        if self.file_id.match(cake):
            self.cake = cake
        else:
            if cake is None:
                data_type = DataType.UNCATEGORIZED
            else:
                log.warning('file_id:%r  does not mach %r' %
                            (file_id,cake))
                data_type = cake.data_type
            self.cake = Cake(file_id.hash_bytes, KeyStructure.SHA256,
                             data_type)

    def found(self):
        return self.size is not None and self.size >= 0

    def open_fd(self):
        return None

    def stream(self):
        return None

    def delete(self):
        return False

NULL_LOOKUP = Lookup(None, None, None)


class ContentAddressLookup(Lookup):
    def __init__(self, store, file_id, cake):
        Lookup.__init__(self,store,file_id, cake)
        self.dir = os.path.join(store.root, self.file_id.shard_name)

    def blob_db(self):
        return self.store.blob_dbf(self.file_id.shard_name)

    def store_in_catalog(self, conn, blob_id = None):
        rp = conn.execute(catalog.select(catalog.c.cake)
                          .where(catalog.c.cake == self.cake))
        if rp.rowcount() == 0:
            rp = conn.execute(catalog.insert().values(
                cake=self.cake,
                file_id=self.file_id,
                blob_id=blob_id,
            ))
            if rp.rowcount() != 1:
                raise AssertionError('cannot catalog %r' %
                                     rp.last_inserted_params())


class DbLookup(ContentAddressLookup):
    def __init__(self, store, file_id, cake = None):
        ContentAddressLookup.__init__(self,store,file_id,cake)
        blob_db = self.blob_db()
        if blob_db.exists():
            q = blob.select(
                    func.char_length(blob.c.content).label('size'),
                    blob.c.created_dt
                ).where(blob.c.file_id == self.file_id)
            result = blob_db.execute(q).one_or_none()
            if result is not None:
                self.size = result.size
                self.created_dt = result.created_dt


    def save_content(self, content):
        blob_db = self.blob_db()
        if not self.found():
            blob_db.ensure_db()
            with blob_db.connect() as conn:
                rp = conn.execute(blob.insert().values(
                    content = content,
                    file_id = self.file_id ))
                blob_id = rp.lastrowid
                self.store_in_catalog(conn, blob_id=blob_id)
            return True
        else:
            return False

    def stream(self):
        row = self.blob_db().execute(
            blob.select(blob.c.content)
            .where(blob.c.file_id == self.file_id)).one()
        return six.BytesIO(row.content)

    def delete(self):
        r = self.blob_db.execute(blob.delete()
                             .where(blob.c.file_id == self.file_id))
        return r.rowcont() == 1


class FileLookup(ContentAddressLookup):
    def __init__(self, store, file_id, cake=None):
        ContentAddressLookup.__init__(self, store, file_id, cake)
        self.file = os.path.join(self.dir, self.file_id)
        try:
            (self.size, _, _, ctime) = os.stat(self.file)[6:]
            self.created_dt=datetime.datetime.utcfromtimestamp(ctime)
        except OSError as e:
            if e.errno != 2:  # No such file
                 raise # pragma: no cover

    def open_fd(self):
        return os.open(self.file,os.O_RDONLY)

    def stream(self):
        return open(self.file,'rb')

    def delete(self):
        os.remove( self.file )
        return True

    def     update_catalog(self):
        blob_db = self.blob_db()
        if not self.found():
            blob_db.ensure_db()
            with blob_db.connect() as conn:
                self.store_in_catalog(conn)

MAX_DB_BLOB_SIZE = 1 << 16

class LiteBackend:
    '''
    Storage backend that keep blobs in set of sharded directories.
    BLOBs smaller then db_limit will be stored in SQLite and bigger
    as individual files in directory

    '''
    def __init__(self, root):
        self.root = root
        self.incoming_dir = os.path.join(self.root,'incoming')
        ensure_directory(self.self.incoming_dir)
        self.in_db = Dbf(incoming_meta, self.incoming + '.db')
        self.in_db.ensure_db()

    def blob_dbf(self, shard_name):
        path = os.path.join(self.root, shard_name, 'blob.db')
        return Dbf(shard_meta, path)

    def iterate_udks(self):
        for shard_name in filter(is_it_shard, os.listdir(self.root)):
            blob_db = self.blob_dbf(shard_name)
            result = blob_db.execute(catalog.select(catalog.c.cake))
            for row in result:
                yield row.cake

    def lookup(self, k):
        if isinstance(k, Cake):
            file_id = ContentAddress(k)
            cake = k
        else:
            file_id = ContentAddress.ensure_it(k)
            cake = None
        for lookup_contr in (FileLookup, DbLookup):
            l = lookup_contr(self, file_id, cake)
            if l.found():
                return l
        return NULL_LOOKUP

    def writer(self, external_cake):
        return ContentWriter(self, external_cake)


class IncomingFile:
    def __init__(self, backend):
        self.backend = backend
        rp = self.backend.in_db.execute( incoming.insert())
        self.incoming_id = rp.lastrowid()
        self.file = os.path.join(self.backend.incoming_dir,
                                 '%d.tmp' % self.incoming_id)
        self.fd = open(self.file, 'wb')

    def write(self, input):
        return self.fd.write(input)

    def save_as(self, cake):
        cake = Cake.ensure_it(cake)
        self.fd.close()
        self.fd = None
        dest = FileLookup(self.backend, cake)
        new = not dest.found()
        if new:
            ensure_directory(dest.dir)
            log.debug('mv %s %s' % (self.file, dest.file))
            shutil.move(self.file, dest.file)
        else:
            self.backend.in_db.execute(
            incoming.update(new=new, cake=cake)
                .where(incoming.c.incoming_id == self.incoming_id))
        return dest.cake

    def close(self, file_id, move_to=None):
        self.fd.close()
        self.fd = None
        found = move_to is None
        if found:
            log.debug('rm %s' % self.file)
            os.remove(self.file)
        else:
            log.debug('mv %s %s' % (self.file, move_to))
            shutil.move(self.file, move_to)
        self.backend.in_db.execute(
            incoming.update(new=not found, file_id=file_id)
                .where( incoming.c.incoming_id == self.incoming_id))


class ContentWriter:
    def __init__(self, backend, external_cake ):
        self.backend = backend
        self.cake = external_cake
        self.buffer = binary_type()
        self.incoming_file = None
        self.digest = hashlib.sha256()
        self.file_id = None

    def write(self, content, done=False):
        content = ensure_bytes(content)
        self.digest.update(content)
        if self.buffer is not None:
            if MAX_DB_BLOB_SIZE < len(self.buffer) + len(content):
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
        self.file_id = ContentAddress(self.digest)
        if self.buffer is not None:
            lookup = DbLookup(self.backend, self.file_id, self.cake)
            lookup.save_content(self.buffer)
            self.buffer = None
        elif self.incoming_file is not None:
            lookup = FileLookup(self.backend, self.file_id, self.cake)
            new = not lookup.found()
            if new:
                self.incoming_file.close(self.file_id, move_to=lookup.file)
            else:
                self.incoming_file.close(self.file_id)
            self.incoming_file = None
            lookup.update_catalog()
        else:
            raise AssertionError('what else: %r' % self.cake )
        return self.file_id

