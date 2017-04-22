import os
import yaml
from hashstore.db import _session, DbFile
from hashstore.utils import create_path_resolver,\
    read_in_chunks,ensure_directory,reraise_with_msg
import datetime
import hashstore.mount as mount
import hashstore.udk as udk
from hashstore.utils import quict
import hashstore.storage as storage

import logging
log = logging.getLogger(__name__)

default_config = os.path.join(os.environ['HOME'],'.back-it-up')


class Backup(DbFile):
    def __init__(self, config=default_config, db_location = None, substitutions = {}):
        self.config=yaml.load(open(config))
        if db_location is None:
            db_location = config+'.db'
        DbFile.__init__(self, db_location )
        self.ensure_db()
        path_resover = create_path_resolver(substitutions)
        self.mounts = []
        for m in self.config['mounts']:
            location,frequency = (m[k] for k in ['location','frequency'])
            location = path_resover(location)
            mount_id = self.resolve_ak('mount', location)
            self.mounts.append([mount_id, location, frequency] )
            log.info( (mount_id,location,frequency) )
        self.storage = storage.factory(path_resover, self.config['storage'])


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
        for mount_id, location, frequency in self.mounts:
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



