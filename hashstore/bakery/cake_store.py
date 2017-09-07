import os
from hashstore.bakery.backend import LiteBackend
from hashstore.bakery.content import Content
from hashstore.bakery.ids import Cake, NamedCAKes, CakePath
from hashstore.ndb import Dbf
from hashstore.utils import ensure_dict

from hashstore.ndb.models.server_config import ServerKey, \
    ServerConfigBase
from hashstore.ndb.models.glue import PortalType, Portal, \
    PortalHistory, GlueBase, User, UserState, Permission, \
    PermissionType, Acl

import logging
log = logging.getLogger(__name__)


def _find_user(session, user_or_email):
    if '@' in user_or_email:
        column = User.email
    else:
        column = User.id
        user_or_email = Cake.ensure_it(user_or_email)
    return session.query(User).filter(column == user_or_email).one()

def _find_permission(session, user, acl):
    conditions = [Permission.user == user,
                  Permission.permission_type == acl.permission_type]
    if acl.cake is not None:
        Permission.cake == acl.cake
    return session.query(Permission).filter(*conditions).one_or_none()

def _resolve_stack(session, cake):
    cake_stack = []
    while True:
        cake_stack.append(cake)
        if cake.is_resolved() or cake.has_data():
            return cake_stack
        if len(cake_stack) > 10:
            raise AssertionError('cake loop? %r' % cake_stack)
        cake = session.query(Portal)\
            .filter(Portal.id == cake).one().latest

_sort_perms = lambda r: (r.permission_type.name, str(r.cake))

class UserSessionActions:

    def __init__(self, session, user_id_or_email):
        self.user = _find_user(session, user_id_or_email)
        self.acls = self.user.acls()

    '''
    get_content(data_cake)   -> Content          Read_, Read_Any_Data
        Reads data by data_cake

    read_portal (portal)     -> cake             Read_, Read_Any_Portal
        Read portal

    get_content_by_path (cake/a/b/c) -> cake     Read_, Read_Any_Data
                                                 Read_Any_Portal
        Read data behind cake, require specific Read_ permission or
        Read_Any_* . Also if there are portals in the path permissions
        will be validated on them before you able to proceed further.

    store_directories(directories)    -> data_cake        Write_Any_Data
        Write data

    write_data (data)        -> data_cake        Write_Any_Data
        Write data

    list_acl_cakes ()        -> [cake...]
        inspects Read_ permissions for user and return any specific
        cakes he allowed to see

    list_portals ()          -> [portal...]      Read_Any_Portal
        list all active portals known for storage

    edit_portal(portal,cake)                     Edit_Portal_, Admin
        change cake that portal points too

    create_portal(portal, cake)                  Create_Portals
        create portal pointing to cake, if portal is already exist -
        fail. Tiny portals validated against majority of  servers to
        achieve consistency.

    grant_portal(portal, user, perm[*_])         Own_Portal_, Admin

    delete_own_portal(portal)                    Own_Portal_
        disown portal, if nobody owns it deactivate it in
        Portal table

    delete_portal(portal)                        Admin
        deactivate portal and remove any ownership
        permissions on it


    add_user(user)                               Admin
    remove_user(user)                            Admin

    add_acl(user, acl)                           Admin
    remove_acl(user, acl)                        Admin

    '''

class CakeResolver:
    def __init__(self,store, *initial_cakes):
        self.dict = {}


class CakeStore:
    def __init__(self, store_dir):
        self.store_dir = store_dir
        self._backend = None
        self.server_db = Dbf(ServerConfigBase.metadata,
            os.path.join(self.store_dir, 'server.db')
        )
        self.glue_db = Dbf(GlueBase.metadata,
            os.path.join(self.store_dir, 'glue.db')
        )

    def backend(self):
        if self._backend is None:
            self._backend = LiteBackend(
                os.path.join(self.store_dir, 'backend')
            )
        return self._backend

    def initdb(self, external_ip, port):
        if not os.path.exists(self.store_dir):
            os.makedirs(self.store_dir)
        self.server_db.ensure_db()
        os.chmod(self.server_db.path, 0o600)
        self.glue_db.ensure_db()
        self.backend()
        with self.server_db.session_scope() as session:
            skey = session.query(ServerKey).one_or_none()
            if skey is None:
                skey = ServerKey()
            skey.port = port
            skey.external_ip = external_ip
            session.merge(skey)

    def store_directories(self, directories):
        directories = ensure_dict( directories, Cake, NamedCAKes)
        unseen_file_hashes = set()
        dirs_stored = set()
        dirs_mismatch_input_cake = set()
        for dir_cake in directories:
            dir_contents=directories[dir_cake]
            lookup = self.backend().lookup(dir_cake)
            if not lookup.found() :
                w = self.backend().writer()
                w.write(dir_contents.in_bytes(), done=True)
                lookup = self.backend().lookup(dir_cake)
                if lookup.found():
                    dirs_stored.add(dir_cake)
                else: # pragma: no cover
                    dirs_mismatch_input_cake.add(dir_cake)
            for file_name in dir_contents:
                file_cake = dir_contents[file_name]
                if not(file_cake.has_data()) and \
                        file_cake not in  directories:
                    lookup = self.backend().lookup(file_cake)
                    if not lookup.found():
                        unseen_file_hashes.add(file_cake)
        if len(dirs_mismatch_input_cake) > 0: # pragma: no cover
            raise AssertionError('could not store directories: %r' % dirs_mismatch_input_cake)
        return len(dirs_stored), list(unseen_file_hashes)


    def get_content_by_path(self, cakepath):
        #self.get_content(cakepath.root)
        pass

    def get_content(self, cake):
        if isinstance(cake,CakePath):
            return self.get_content_by_path(cake)
        if cake.has_data():
            return Content(data=cake.data())
        return self.backend().lookup(cake).content()

    def writer(self):
        return self.backend().writer()

    def write_content(self, fp, chunk_size=65355):
        w = self.writer()
        while True:
            buf = fp.read(chunk_size)
            if len(buf) == 0:
                break
            w.write(buf)
        return w.done()

    def create_portal(self,portal_id, cake,
                      portal_type = PortalType.content):
        portal_id = Cake.ensure_it(portal_id)
        cake = Cake.ensure_it(cake)
        with self.glue_db.session_scope() as session:
            session.merge(Portal(id=portal_id, latest=cake,
                   portal_type=portal_type))
            session.add(PortalHistory(portal_id = portal_id, cake=cake))

    def add_user(self, email, ssha_pwd, full_name = None):
        with self.glue_db.session_scope() as session:
            session.merge(User(email=email, passwd=ssha_pwd,
                             full_name=full_name,
                             user_state=UserState.active))

    def remove_user(self, user_or_email):
        with self.glue_db.session_scope() as session:
            user = _find_user(session, user_or_email)
            user.user_state = UserState.disabled

    def add_permission(self, user_or_email, acl):
        with self.glue_db.session_scope() as session:
            user = _find_user(session, user_or_email)
            if acl is not None:
                perm = _find_permission(session, user, acl)
                if perm is None:
                    session.add(Permission(
                        user=user,
                        permission_type=acl.permission_type,
                        cake=acl.cake))
            return user, sorted(user.permissions, key=_sort_perms)

    def remove_permission(self, user_or_email, acl):
        with self.glue_db.session_scope() as session:
            user = _find_user(session, user_or_email)
            perm = _find_permission(session, user, acl)
            if perm is not None:
                session.delete(perm)
            return user, sorted(user.permissions, key=_sort_perms)
