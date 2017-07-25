from sqlalchemy import *


def varchar_type(cls):
    class BuiltType(TypeDecorator):
        impl = VARCHAR

        def process_bind_param(self, value, dialect):
            if isinstance(value, cls):
                return str(value)
            else:
                return value

        def process_result_value(self, value, dialect):
            if value is None:
                return value
            else:
                return cls(value)
    return BuiltType

class Dbf:
    def __init__(self,meta,path):
        self.path = path
        self.meta = meta

    def engine(self):
        if self._engine is not None:
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