from hashstore.ids import Cake, Cake_TYPE
from hashstore.content_address import ContentAddress_TYPE
from sqlalchemy import *
import datetime

shard_meta = MetaData()
meta = shard_meta

blob = Table('blob', shard_meta,
    Column('blob_id', Integer,
           primary_key=True, autoincrement=True),
    Column('file_id', ContentAddress_TYPE, nullable=False),
    Column('content', LargeBinary),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    )

shard = Table(
    'shard', shard_meta,
    Column('cake', Cake_TYPE, primary_key=True),
    Column('file_id', ContentAddress_TYPE, nullable=False),
    Column('blob_id', None, ForeignKey('blob.blob_id'), nullable=True),
    )


