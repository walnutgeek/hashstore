from hashstore.db import _session, Session, DbFile

class ContentDB(DbFile):

    def datamodel(self):
        '''
        table:content
          content_id UUID1 PK
          parent_id FK(content) AK(content_ak)
          key JSON AK(content_ak)
          content_meta JSON null
          content UDK null
          update_dt UPDATE_DT
        table:host
          host_id UUID1 PK
          host_name TEXT AK
          host_meta JSON
        table:mount
          mount_id UUID1 PK
          content_id FK(content)
          host_id FK(host)
          mount_meta JSON
        '''
        return self.datamodel.__doc__

