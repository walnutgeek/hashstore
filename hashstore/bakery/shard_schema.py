from hashstore.ids import Cake, Cake_TYPE
from hashstore.bakery.content import ContentAddress_TYPE
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


