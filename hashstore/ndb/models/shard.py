from hashstore.bakery import ContentAddress
from hashstore.ndb import StringCast
from hashstore.ndb.mixins import ReprIt, NameIt, Cdt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Integer, Column, LargeBinary

Base = ShardBase = declarative_base(name='ShardBase')


class Blob(NameIt, ReprIt, Cdt, ShardBase):
    blob_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(StringCast(ContentAddress), nullable=False)
    content = Column(LargeBinary)

shard_meta = ShardBase.metadata
blob = Blob.__table__
