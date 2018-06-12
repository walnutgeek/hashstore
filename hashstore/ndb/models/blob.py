import enum

import datetime
from typing import Any

from hashstore.bakery import ContentAddress
from hashstore.ndb import StringCast
from hashstore.ndb.mixins import ReprIt, NameIt, Cdt
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import LargeBinary, Column, Integer

Base:Any = declarative_base(name='BlobBase')
BlobBase:Any = Base

class Blob(NameIt, ReprIt, Cdt, BlobBase):
    blob_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(StringCast(ContentAddress), nullable=False)
    content = Column(LargeBinary)

blob_meta = BlobBase.metadata
blob = Blob.__table__
