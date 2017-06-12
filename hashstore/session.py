"""
This module contains of data access session.

"""
import sqlite3
import logging
import hashstore.utils as utils
import traceback

log = logging.getLogger(__name__)


class Session:
    def __init__(self, dbf, trace_stack = None):
        self.dbf = dbf
        self.file = dbf.file
        self.trace_stack = trace_stack
        self.conn = sqlite3.connect(self.file)
        self.conn.execute('pragma foreign_keys = on')
        stack = '\n' + ''.join(traceback.format_stack(limit=self.trace_stack)) if self.trace_stack is not None else ''
        log.debug('CONNECT: %s%s' % (self.file, stack))
        self.cursor = self.conn.cursor()
        self.success = True


    def set_for_rollback(self):
        self.success = False

    def execute(self, q, data=None):
        log.debug('EXECUTE: %r + %r' % (q, data))
        try:
            if data is None:
                self.cursor.execute(q)
            else:
                self.cursor.execute(q, data)
        except Exception as e:
            utils.reraise_with_msg('q=%s data=%r' % (q, data), e)


    def query(self, q, params=None, as_dicts=False):
        self.execute(q,params)
        result = self.cursor.fetchall()
        if as_dicts:
            header = list(self.cursor.description)
            return list({col[0]: v[i] for (i, col) in enumerate(header)} for v in result)
        else:
            return list(result)

    def rowcount(self):
        return self.cursor.rowcount

    def lastrowid(self):
        return self.cursor.lastrowid

    def table_info(self,table, session=None):
        return self.query('PRAGMA table_info(%s)' % table,
                          as_dicts=True )

    def get_tables(self,session=None):
        return self.query("select * from sqlite_master where type='table'",
                          as_dicts=True)

    def _tx_action(self, commit_or_rollback):
        msg = commit_or_rollback + ':' + self.file
        if self.trace_stack is not None:
            msg += '\n' + ''.join(traceback.format_stack(limit=self.trace_stack))
        log.debug(msg)
        getattr(self.conn,commit_or_rollback)()

    def commit(self):
        self._tx_action('commit')

    def rollback(self):
        self._tx_action('rollback')

    def close(self):
        if self.success:
            self.commit()
        else:
            self.rollback()
        self.conn.close()

def _session(fn):
    return _session_dbf(lambda args: args[0].dbf)(fn)


def _session_dbf(dbf_factory):
    def decorate(fn):
        def decorated(*args, **kwargs):
            if kwargs.get('session'):
                return fn(*args, **kwargs)
            else:
                dbf = dbf_factory(args) if callable(dbf_factory) else dbf_factory
                session = Session(dbf)
                try:
                    kwargs['session'] = session
                    return fn(*args, **kwargs)
                except:
                    session.set_for_rollback()
                    raise
                finally:
                    session.close()
        return decorated
    return decorate

