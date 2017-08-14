from sqlalchemy import VARCHAR, String, Integer, TypeDecorator, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from hashstore.utils import AltKeyMapper

import os


class StringCast(TypeDecorator):
    impl = VARCHAR

    def __init__(self, stringable_cls, *args, **kw):
        TypeDecorator.__init__(self, *args, **kw)
        self.cls = stringable_cls

    def process_bind_param(self, value, dialect):
        if isinstance(value, self.cls):
            return str(value)
        else:
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return self.cls(value)


class IntCast(TypeDecorator):
    impl = Integer

    def __init__(self, values, get_altkey=None,*arg, **kw):
        TypeDecorator.__init__(self, *arg, **kw)
        if isinstance(values,AltKeyMapper):
            self.mapper = values
        else:
            self.mapper = AltKeyMapper(values, get_altkey=get_altkey)

    def process_bind_param(self, value, dialect):
        return self.mapper.to_altkey(value)

    def process_result_value(self, value, dialect):
        return self.mapper.to_value(value)


class Dbf:
    def __init__(self,meta,path):
        self.path = path
        self.meta = meta
        self._engine = None

    def engine(self):
        if self._engine is None:
            self._engine = create_engine('sqlite:///%s' % self.path)
        return self._engine

    def exists(self):
        return os.path.exists(self.path)

    def ensure_db(self):
        self.meta.create_all(self.engine())

    def execute(self, statement, *multiparams, **params):
        return self.engine().execute(statement, *multiparams, **params)

    def connect(self):
        return self.engine().connect()

