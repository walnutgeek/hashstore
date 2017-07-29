from hashstore.bakery.content import ContentAddress_TYPE
from sqlalchemy import *
import datetime

incoming_meta = MetaData()
meta = incoming_meta

incoming = Table('incoming', incoming_meta,
    Column('incoming_id', Integer,
           primary_key=True, autoincrement=True),
    Column('file_id', ContentAddress_TYPE, nullable=True),
    Column('new', Boolean),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('updated_dt', DateTime, nullable=True,
           onupdate = lambda: datetime.datetime.utcnow())
    )