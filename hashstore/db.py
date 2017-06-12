from hashstore.session import Session, _session
import os
import re
import six
import uuid
import datetime
import json
import hashstore.udk as udk
from hashstore.utils import reraise_with_msg,LazyVars,none2str,call_if_defined

SHARD_SIZE = 3
SQLITE_EXT = '.sqlite3'
db_max=65535

import logging
log = logging.getLogger(__name__)


def to_blob(v):
    if six.PY2:
        return buffer(v)
    else:
        return v if isinstance(v, bytes) else memoryview(v)

def _join(data, expression, delim=',', filter_keys=lambda key: True):
    return delim.join(map( expression, filter(filter_keys, data)))



'''
Cardinalty, row id, etc:

  PK - primary key, if type is not specified INTEGER is assumed
  AK(index_name) - alternative key, create unique index for all fields
  INDEX(0[AD]:index_name) - index key, create index for fields
  FK(table name) - reference to primary key of table, field use same type as PK
  NOT NULL, NULL - pass thru
  BIG - mark field not to be included on `select *`, so only way to retrive that
    field is to mention it explicitly, type will be automticaly set to BLOB

Data types and  data:

  UUID1,UUID4: if used with PK automaticaly generate bits on insert
  JSON - stored as json string
  SORTED_DICT - dictionary stored as json string but keys
       ordered alphabetically, so string equals will work detrministically
  DT - timestamp converted to naive datetime
  INSERT_DT - dt field that automatically populated on every insert with current
        utc time
  UPDATE_DT - dt field that automatically populated on every updatewith current
        utc time

'''
DEFAULT_PK_TYPE = 'INTEGER'


def ensure_uuid(value):
    if not (isinstance(value, uuid.UUID)):
        value = uuid.UUID(value)
    return to_blob(value.bytes)


def _define_roles():
    class PK:
        type = DEFAULT_PK_TYPE
        @staticmethod
        def column_ddl(constraint):
            return 'PRIMARY KEY'
        @staticmethod
        def init_column(column, constraint):
            column.table.primarykey = column

    class AK:
        @staticmethod
        def init_column(column, constraint):
            index_name = constraint.param
            table = column.table
            if index_name is not None:
                index = Index.get_index(table,index_name)
                index.columns.append(constraint.column.name)
            else:
                table.altkey = constraint.column
        @staticmethod
        def column_ddl(constraint):
            return 'UNIQUE NOT NULL' if constraint.param is None else ''

    class OPTIONS:
        @staticmethod
        def column_ddl(constraint):
            return 'CHECK(%s in (%s))' % (constraint.column.name, constraint.param )

    class FK:
        @staticmethod
        def deffered_init_column(column,constraint):
            column.fk = lambda: column.table.schema.tables[constraint.param]
            if not(column.type):
                for fk_constrain in column.fk().primarykey.constraints:
                    if fk_constrain.is_type():
                        fk_constrain.clone(column).init_constraint(column)
                        break

        @staticmethod
        def column_ddl(constraint):
            column = constraint.column
            fk_table = column.fk()
            add_type = fk_table.primarykey.type if column.type is None else ''
            return '%s references %s(%s)' % (add_type, fk_table.name, fk_table.primarykey.name)

    class BIG:
        type = 'BLOB'

    class UUID1:
        type = 'UUID1'
        @staticmethod
        def column_ddl(constraint): return ''
        @staticmethod
        def on_INSERT(constraint, vars):
            if 'PK' in constraint.column.roles:
                return uuid.uuid1()
        @staticmethod
        def on_GET(constraint, value):
            return None if value is None else uuid.UUID(bytes=value)
        @staticmethod
        def on_SET(constraint, value):
            return ensure_uuid(value)


    class UUID4:
        type = 'UUID4'
        @staticmethod
        def column_ddl(constraint): return ''
        @staticmethod
        def on_INSERT(constraint, vars):
            if 'PK' in constraint.column.roles:
                return uuid.uuid4()
        @staticmethod
        def on_GET(constraint, value):
            return None if value is None else uuid.UUID(bytes=value)
        @staticmethod
        def on_SET(constraint, value):
            return ensure_uuid(value)

    class JSON:
        type = 'TEXT'
        @staticmethod
        def on_GET(constraint, value):
            return json.loads(value)
        @staticmethod
        def on_SET(constraint, value):
            return json.dumps(value)

    class SORTED_DICT:
        type = 'TEXT'
        @staticmethod
        def on_GET(constraint, value):
            return json.loads(value)
        @staticmethod
        def on_SET(constraint, d):
            k2json = lambda k: json.dumps(k)+':'+json.dumps(d[k])
            return '{' + ','.join( map(k2json, sorted(d.keys())) ) + '}'

    class UDK:
        type = 'TEXT'
        @staticmethod
        def on_GET(constraint, value):
            return udk.UDK(value)
        @staticmethod
        def on_SET(constraint, d):
            return str(d)

    class DT:
        type = 'TIMESTAMP'

    class INSERT_DT(DT):
        @staticmethod
        def on_INSERT(constraint, vars):
            return datetime.datetime.utcnow()

    class UPDATE_DT(DT):
        @staticmethod
        def on_UPDATE(constraint, vars):
            return datetime.datetime.utcnow()

    return locals()

ROLES = _define_roles()

ACTIONS = ['GET','SET','INSERT','UPDATE']


class Constraint:
    def __init__(self,column,i,p,to_be_cloned=None):
        self.column = column
        if to_be_cloned is None:
            self.param = None
            self.name = p
            self.role = None
            m = re.match(r'(\w+)\(([,\'\w]+)\)', p)
            if not(m):
                m = re.match(r'(\w+)()', p)
            if m :
                n = m.group(1)
                if n in ROLES:
                    self.name = n
                    self.role = ROLES[n]
                    if m.group(2):
                        self.param = m.group(2)
            if i == 0 and not(self.role):
                self.role = type('', (), {})()
                self.role.type = self.name
        else:
            self.param = to_be_cloned.param
            self.name = to_be_cloned.name
            self.role = to_be_cloned.role
            # self.column.constraints.append(self)
            # self.column.roles[self.name] = self

    def clone(self,column):
        return Constraint(column,None,None,to_be_cloned=self)

    def init_constraint(self, column):
        if column.type is None and hasattr(self.role, 'type'):
            column.type = self.role.type
        for action in ACTIONS:
            method_name = 'on_' + action
            if hasattr(self.role, method_name):
                if action not in column.actions:
                    def set_action(action_method):
                        column.actions[action] = lambda x: action_method(self, x)
                    set_action(getattr(self.role, method_name))

    def is_type(self):
        return hasattr(self.role,'type')

    def __str__(self):
        return none2str(call_if_defined(self.role, 'column_ddl', self)) if self.role else self.name


class Column:
    def __init__(self,table,line):
        self.table = table
        parts = re.split(r'\s+',line)
        self.name = parts[0]
        self.constraints = [Constraint(self, i, p) for i,p in enumerate(parts[1:])]
        self.roles= {}
        self.role = None
        self.type = None
        self.unique = False
        self.actions = {}
        for constraint in self.constraints:
            if constraint.role:
                constraint.init_constraint(self)
            self.roles[constraint.name] = constraint
        for constraint in self.constraints:
            if hasattr(constraint.role, 'init_column'):
                constraint.role.init_column(self,constraint)
        self.table.column_names.append(self.name)
        self.table.columns[self.name] = self

    def init_column(self):
        for _,constraint in six.iteritems(self.roles):
            if hasattr(constraint.role, 'deffered_init_column'):
                constraint.role.deffered_init_column(self,constraint)

    def __str__(self):
        return '%s %s %s ' % (self.name, none2str(self.type), ' '.join(str(p) for p in self.constraints))


class Index:
    @staticmethod
    def get_index(table,name):
        if name in table.indexes:
            return table.indexes[name]
        else:
            return Index(table,name)

    def __init__(self,table,name):
        self.table = table
        self.name = name
        self.columns = []
        self.unique = True
        self.table.indexes[name] = self

    def __str__(self):
        return 'CREATE %s INDEX %s on %s ( %s );' % (
            'UNIQUE' if self.unique else '' ,
            self.name, self.table.name,  ','.join( self.columns ) )


class Table:
    def __init__(self, schema, name):
        self.name = name
        self.schema = schema
        self.schema.tables[name] = self
        self.column_names = []
        self.columns = {}
        self.indexes = {}

    def init_columns(self):
        for col_name in self.column_names:
            self.columns[col_name].init_column()

    def __str__(self):
        cols_defn = ','.join(str(self.columns[c]) for c in self.column_names)
        return 'CREATE TABLE %s ( %s );' % ( self.name, cols_defn)

    def all_column_names(self, include_only_role=None,
                         exclude_role='BIG'):
        """
        by default return all  columns,
        except columns marked as BIG
        """
        def gen(check):
            for c in self.column_names:
                if check(self.columns[c]):
                    yield c
        if include_only_role :
            return gen(lambda col: include_only_role in col.roles)
        elif exclude_role:
            return gen(lambda col: exclude_role not in col.roles)
        else:
            return self.column_names

    def get_actions(self, action, for_columns ):
        """
        Retrieve dictionary of column name to getter function
        for all columns that require coversion after select

        :param for_columns: list of column names
        :return: dictionary of column name to getter
        """
        actions = {}
        for col_name in for_columns:
            col = self.columns[col_name]
            if action in col.actions:
                actions[col_name] = col.actions[action]
        return actions

class Schema:
    def __init__(self,model):
        self.tables = {}
        table = None
        for l in model.split('\n'):
            l = l.strip()
            if len(l) > 0:
                if l.lower()[:6] == 'table:':
                    table = Table(self, l[6:].strip())
                elif table:
                    Column(table,l)
        for table in six.itervalues(self.tables):
            table.init_columns()

    def create_statments(self):
        for table_name, table in six.iteritems(self.tables):
            yield str(table)
            for index_name, index in six.iteritems(table.indexes):
                yield str(index)


old_value_key = lambda key: key[:1] != '_'
new_value_key = lambda key: key[:1] == '_'
column_name_from_key = lambda k: k if old_value_key(k) else k[1:]


SELECT_TMPL = 'select {selectors} from {table_name} where {conditions}'
INSERT_TMPL = 'insert into {table_name} ( {into_columns} ) values ( {values} )'
UPDATE_TMPL = 'update {table_name} set {assignments} where {conditions}'
DELETE_TMPL = 'delete from {table_name} where {conditions}'
SELECT_PK_TMPL = 'select {pk} from {table_name} where {conditions}'


class DbFile:
    def __init__(self, file, datamodel=None, ):
        self.dbf = self
        if datamodel is None:
            datamodel = self.datamodel()
            log.debug(datamodel)
        self.schema = Schema(datamodel)
        self.file = file

    def exists(self):
        return os.path.exists(self.file)

    def ensure_db(self, after_create=None, compare=True):
        if not (self.exists()):
            directory = os.path.dirname(self.file)
            if not (os.path.isdir(directory)):
                os.makedirs(directory)
            self.create_db(after_create)
        elif compare:
            warnings, none_of_tables = self.compare_tables()
            if none_of_tables:
                self.create_db(after_create)
            elif len(warnings) > 0:
                raise ValueError(warnings)
        return self


    @_session
    def compare_tables(self, session=None):
        warnings = []
        none_of_tables = True

        def _deep_equals(in_code, in_db, warn_text):
            in_code = json.dumps(in_code)
            in_db = json.dumps(in_db)
            r = in_db == in_code
            if not (r):
                warnings.append('%s in_code: %s in_db: %s' % (warn_text, in_code, in_db))
            return r

        tables_in_db = [r['name'] for r in session.get_tables(session=session)]
        for tablename in self.schema.tables:
            if tablename not in tables_in_db:
                warnings.append('table %s in not in db' % tablename)
            else:
                none_of_tables = False
                columns = session.table_info(tablename, session=session)
                columnnames_in_db = sorted(c['name'] for c in columns)
                table_in_code = self.schema.tables[tablename]
                columnnames_in_code = sorted(table_in_code.column_names)
                if _deep_equals(columnnames_in_code, columnnames_in_db,
                                'Column names does not match: table:%s ' % tablename):
                    for c in columns:
                        col_in_code = table_in_code.columns[c['name']]
                        type_in_code = col_in_code.type
                        if type_in_code != c['type']:
                            warnings.append('type mismatch col %s.%s %r != %r' % (tablename, c['name'],type_in_code, c['type']))
                        if c['pk']:
                            if col_in_code.table.primarykey.name != c['name']:
                                warnings.append('pkey mismatch col %s.%s' % (tablename, c['name']))
        return warnings, none_of_tables


    @_session
    def create_db(self, after_create=None, session=None):
        for create_sql in self.schema.create_statments():
            session.execute(create_sql)
        if after_create is not None:
            after_create(self, session)

    class SmartVars(LazyVars):
        def __init__(self, dbf, table_name, data, select = None, alias = None, op=None ):
            if op is not None and op not in ['INSERT','UPDATE']:
                raise AssertionError('op:%r is not supported'%op)
            self.dbf = dbf
            self.table_name = table_name
            self.table = dbf.schema.tables[table_name]
            self.data = data
            self.select = select
            self.alias = '' if alias is None else alias + '.'
            if op is not None:
                op_actions = self.table.get_actions(op, self.table.column_names)
                if len(op_actions) > 0 :
                    for column_name, action in six.iteritems(op_actions):
                        v = action(self)
                        if v is not None:
                            self.data['_'+column_name] = v
            LazyVars.__init__(
                self,
                table_name=table_name,
                pk=self.table.primarykey.name,
                assignments=lambda: _join(
                    self.data,
                    lambda k: k[1:] + ' = :' + k,
                    filter_keys=new_value_key),
                conditions=lambda: _join(
                    self.data,
                    lambda k: self.alias + (k+' is null' if self.data[k] is None else k+'=:'+k),
                    filter_keys=old_value_key, delim=' and '),
                into_columns=lambda: _join(
                    self.data, column_name_from_key) ,
                values=lambda: _join(
                    self.data, lambda k: ':' + k),
                columns = lambda: list(self.table.all_column_names(
                    include_only_role=self.select)),
                selectors=lambda: _join(
                    self['columns'],
                    lambda key: self.alias + key),
                data=lambda: self.update_data()
                )

        def update_data(self):
            actions = self.table.get_actions('SET', [ column_name_from_key(k) for k in self.data ])
            if len(actions) > 0:
                updated = { k:v for k,v in six.iteritems(self.data)}
                for column_name in actions:
                    def update_if(k):
                        if k in updated:
                            updated[k] = actions[column_name](updated[k])
                    update_if(column_name)
                    update_if('_'+column_name)
                return updated
            else:
                return self.data

        def format(self,template):
            '''
            similar to `template.format(**vars)`, but this way if does
            not  unnecessarily execute __getitem__ on every key because
            no unpacking `**vars` needed
            :param template: format string
            :return: formatted string, only necessary attributes resolved
            '''
            from string import Formatter
            return Formatter().vformat(template,[],self)

        def ensure_rowid(self, session):
            pk = self.table.primarykey
            if pk is not None and pk.type == DEFAULT_PK_TYPE:
                self.data['_' + pk.name] = session.lastrowid()
            return self.data['_' + pk.name]

        def select_pk(self, session):
            rs = session.query(self.format(SELECT_PK_TMPL), self['data'])
            rec_id = None
            if len(rs) > 0:
                rec_id = rs[0][0]
                pk = self.table.primarykey
                if 'GET' in pk.actions:
                    rec_id = pk.actions['GET'](rec_id)
            return rec_id

        def get_pk(self):
            n = self.table.primarykey.name
            if n in self.data:
                return self.data[n]
            return self.data['_' + n ]

    @_session
    def select(self, table_name, data, where='', select=None, selectors = None,
               session=None, q=SELECT_TMPL):
        vars = DbFile.SmartVars(self, table_name, data, select=select)
        try:
            if selectors is not None:
                vars.values['selectors'] = selectors
            result = session.query(vars.format(q) + where, vars['data'], as_dicts=True)
            if len(result) > 0 and selectors is None:
                actions = vars.table.get_actions('GET', vars['columns'])
                if len(actions) > 0 :
                    for row in result:
                        for column_name in actions:
                            row[column_name] = actions[column_name](row[column_name])
        except:
            reraise_with_msg('%s <- %r' % (q+where, vars))

        return result

    @_session
    def select_one(self, table_name, data, where='', select=None, selectors = None,
                   session=None, q=SELECT_TMPL):
        r = self.select( table_name, data, where=where,
            select=select, selectors=selectors, session=session, q=q)
        n_rec = len(r)
        if n_rec == 0:
            return None
        if n_rec == 1:
            return r[0]
        raise AssertionError('select_one returned %d records' % n_rec)

    @_session
    def store(self, table_name, data, session=None):
        vars = DbFile.SmartVars(self, table_name, data, op='UPDATE')
        session.execute(vars.format(UPDATE_TMPL), vars['data'])
        if session.rowcount() > 1:
            raise AssertionError('{rowcount} records (more then one) were updated with {conditions} {data}'.format(
                rowcount=session.rowcount(), **vars))
        try:
            rec_id = vars.get_pk()
        except KeyError:
            pass
        if session.rowcount() == 1:
            rec_id = vars.select_pk(session)
        else:
            vars = DbFile.SmartVars(self, table_name, data, op='INSERT')
            session.execute(vars.format(INSERT_TMPL), vars['data'])
            rec_id = vars.ensure_rowid(session)
        return rec_id


    @_session
    def insert(self, table_name, data, session=None):
        vars = DbFile.SmartVars(self, table_name, data, op='INSERT')
        session.execute(vars.format(INSERT_TMPL), vars['data'])
        vars.ensure_rowid(session)
        return data


    @_session
    def update(self, table_name, data, session=None):
        vars = DbFile.SmartVars(self, table_name, data, op='UPDATE')
        session.execute(vars.format(UPDATE_TMPL), vars.update_data())
        return session.rowcount()


    @_session
    def delete(self, table_name, data, session=None):
        vars = DbFile.SmartVars(self, table_name, data, op='UPDATE')
        session.execute(vars.format(DELETE_TMPL), vars['data'])
        return session.rowcount()


    @_session
    def resolve_ak(self, table_name, ak_value, data = None,
                   ensure=True, session=None):
        if data is None:
            data = {}
        vars = DbFile.SmartVars(self, table_name, data, op='INSERT')
        if ak_value is not None:
            vars.data[vars.table.altkey.name] = ak_value
        rec_id = vars.select_pk(session)
        if rec_id is None:
            if ensure:
                session.execute(vars.format(INSERT_TMPL), vars['data'])
                rec_id = vars.ensure_rowid(session)
        return rec_id

