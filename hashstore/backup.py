import os
import yaml
from hashstore.db import _session, DbFile
from hashstore.utils import create_path_resolver,\
    read_in_chunks,ensure_directory,reraise_with_msg
import datetime
import hashstore.mount as mount
import hashstore.udk as udk
import hashstore.storage as storage

import logging
log = logging.getLogger(__name__)

default_config = os.path.join(os.environ['HOME'],'.back-it-up')


class Backup(DbFile):
    def __init__(self, db_location , mount_locations, storage_or_config):
        DbFile.__init__(self, db_location )
        self.ensure_db()
        self.mounts = []
        for location in mount_locations:
            mount_id = self.resolve_ak('mount', location)
            entry = (mount_id, location)
            self.mounts.append(entry)
            log.info(entry)
        if isinstance(storage_or_config, storage.Storage):
            self.storage = storage_or_config
        else:
            self.storage = storage.factory(storage_or_config)

    @staticmethod
    def from_config(config=default_config, db_location = None, substitutions = {}):
        config = yaml.load(open(config))
        if db_location is None:
            db_location = config + '.db'
        path_resolver = create_path_resolver(substitutions)
        mount_locations = [path_resolver(m['location']) for m in config['mounts']]
        storage_config = config['storage']
        for var_name in [ 'path' , 'url']:
            if var_name in storage_config:
                storage_config[var_name] = path_resolver(storage_config[var_name])
        return Backup(db_location,mount_locations,storage_config)

    def datamodel(self):
        '''
        table:mount
          mount_id PK
          dir TEXT AK
          created TIMESTAMP INSERT_DT
          last_push_id FK(push) NULL
        table:push
          push_id PK
          mount_id FK(mount)
          directory_synched INT NULL
          files_synched INT NULL
          started TIMESTAMP INSERT_DT
          complited TIMESTAMP UPDATE_DT NULL
          hash UDK NULL

        '''
        return self.datamodel.__doc__

    @_session
    def backup(self, now = None, session=None):
        if now is None:
            now = datetime.datetime.utcnow()
        versions = {}
        for mount_id, location in self.mounts:
            m = mount.MountDB(location, scan_now=False)
            m.push_files(self.storage)
            versions[location] = m.last_hash
        return versions

    def restore(self, k, path):
        k = udk.UDK.ensure_it(k)
        if k.named_udk_bundle:
            content = self.storage.get_content(k)
            log.info('%r'%content)
            bundle = udk.UDKBundle(content)
            ensure_directory(path)
            for n in bundle:
                file_path = os.path.join(path, n)
                file_k = bundle[n]
                if file_k.named_udk_bundle:
                    self.restore(file_k, file_path)
                else:
                    try:
                        out_fp = open(file_path, "wb")
                        in_fp = self.storage.get_content(file_k)
                        for chunk in read_in_chunks(in_fp):
                             out_fp.write(chunk)
                        out_fp.close()
                    except:
                        reraise_with_msg("%s -> %s" % (file_k,file_path) )
