import os
import datetime
from hashstore.bakery import (
    NotAuthorizedError, CredentialsError, Cake, CakeRack,
    CakePath, CakeType, CakeRole, PatchAction, Content)
from hashstore.kernel import reraise_with_msg, utf8_reader
from hashstore.utils import tuple_mapper
from hashstore.utils.file_types import (BINARY, guess_name, file_types)
from hashstore.kernel.hashing import SaltedSha
from hashstore.bakery.cake_tree import CakeTree
from hashstore.utils.db import MultiSessionContextManager
import hashstore.bakery.lite.dal as dal
from sqlalchemy import and_, or_

from hashstore.bakery.lite.node import UserSession

from hashstore.bakery.lite.node import (
    User, UserState, Permission,
    PermissionType as PT, Acl, UserType
)

from hashstore.bakery.lite.node import (
    Portal, VolatileTree
)

import logging

from hashstore.utils.api import ApiCallRegistry

log = logging.getLogger(__name__)

FROM_COOKIE='FROM_COOKIE'


class Permissions:
    read_data_cake = (PT.Read_, PT.Read_Any_Data)
    read_portal = (PT.Read_, PT.Read_Any_Portal)
    write_data = (PT.Write_Any_Data,)
    portals = (PT.Read_, PT.Edit_Portal_, PT.Own_Portal_)


class StoreContext(MultiSessionContextManager):
    def __init__(self, store, remote_host=None):
        MultiSessionContextManager.__init__(self)
        self.store = store
        self.remote_host = remote_host
        self.params = {}

    def glue_session(self):
        return self.get_session(lambda : self.store.glue_db)

    def srvcfg_session(self):
        return self.get_session(lambda : self.store.srvcfg_db)

    def cake_session(self, cake):
        if cake is None:
            raise AssertionError('cake is alwais need to be provided to '
                                 'be able to shard this db in future')
        return self.get_session(lambda : self.store.cake_shard_db(cake))

    def validate_session(self, session_id, client_id=None):
        if session_id is not None:
            user_session = self.srvcfg_session().query(UserSession)\
                .filter(UserSession.id == session_id,
                        UserSession.active == True)\
                .one_or_none()
            if user_session is not None:
                if user_session.client is not None:
                    if not user_session.client.check_secret(str(client_id)):
                        raise CredentialsError('client_id does not match')
                self.params['user_id'] = user_session.user
                self.params['session_id'] = user_session.id
                return PrivilegedAccess(self, user=user_session.user)
        log.warning('{session_id} {client_id}'.format(**locals()))
        raise CredentialsError('cannot validate session')


guest_api = ApiCallRegistry()


class GuestAccess:

    api = guest_api

    def __init__(self, ctx, user=None, user_type=UserType.guest):
        self.ctx = ctx
        if user is None:
            self.auth_user = dal.query_users_by_type(
                self.ctx.glue_session(), user_type).one()
        else:
            self.auth_user = self.ensure_user(user)

    def ensure_user(self, user):
        if isinstance(user, User):
            return user
        else:
            return dal.find_normal_user(self.ctx.glue_session(), user)

    def blob_store(self):
        return self.ctx.store.blob_store()

    def process_api_call(self, method, params):
        # log.debug("{self} {method}({params})".format(**locals()))
        return self.api.run(self, method, params)

    @guest_api.call()
    def info(self):
        return {"isAuthenticated": False, "anyCakeAccess": False}

    @guest_api.call()
    def login(self, email, passwd, client_id=None):
        user = dal.find_normal_user(self.ctx.glue_session(), email)
        if user.passwd.check_secret(passwd):
            client_ssha = None
            if client_id is not None:
                client_ssha = SaltedSha.from_secret(client_id)
            user_session = UserSession(
                user=user.id,
                client=client_ssha,
                active=True,
                remote_host = self.ctx.remote_host)
            self.ctx.srvcfg_session().add(user_session)
            self.ctx.commit()
            return user_session.id
        else:
            raise CredentialsError('Credentials does not match for: '
                                   + email)

    def authorize(self, cake, pts):
        if self.auth_user.id == cake and PT.Read_ in pts:
            return
        required_acls = Acl.cake_acls(cake, pts)
        for acl in required_acls:
            if acl in self.auth_user.acls():
                return
        raise NotAuthorizedError('%s does not have %r permissions' %
                                 (self.auth_user.email, required_acls))

    def server_login(self, server_id, server_secret):
        pass # validate and create server session logic

    def get_content(self, cake_or_path):
        '''
        get_content(data_cake)   -> Content

            permissions: Read_, Read_Any_Data

            Reads data by data_cake

        or

        get_content(portal_cake) -> Content

            permissions: Read_, Read_Any_Portal

            Read portal, if portal points to other portal permission needs
            to be check on all portals in redirect chain. redirect chain
            cannot be longer then 10.
        '''
        if isinstance(cake_or_path, CakePath):
            return self.get_content_by_path(cake_or_path)
        cake = cake_or_path
        if cake.has_data():
            return Content.from_data_and_role(
                role=cake.header.role, data=cake.data())
        elif cake.is_resolved():
            self.authorize(cake_or_path, Permissions.read_data_cake)
            return self.blob_store().get_content(cake_or_path)
        elif cake.header.type.is_portal:
            self.authorize(cake_or_path, Permissions.read_portal)
            if cake.header.type == CakeType.PORTAL :
                resolution_stack = dal.resolve_cake_stack(
                    self.ctx.cake_session, cake_or_path)
                for resolved_portal in resolution_stack[:-1]:
                    self.authorize(cake_or_path, Permissions.read_portal)
                return self.blob_store().get_content(resolution_stack[-1])
            elif cake.header.type in [CakeType.DMOUNT, CakeType.VTREE]:
                return self.get_content_by_path(CakePath(None, _root=cake, _path=[]))
        else:
            raise AssertionError('should never get here')

    def get_content_by_path(self, cake_path):
        '''
        get_content_by_path (cake/a/b/c) -> cake     Read_, Read_Any_Data
                                                     Read_Any_Portal
            Read data behind cake, require specific Read_ permission or
            Read_Any_* . Also if there are portals in the path permissions
            will be validated on them before you able to proceed further.
        '''
        if cake_path.relative():
            raise AssertionError(f'Has to be absolute: {cake_path}')
        root = cake_path.root
        if root.header.type == CakeType.VTREE:
            return self._read_vtree(cake_path)
        elif root.header.type == CakeType.DMOUNT:
            return self._read_dmount(cake_path)
        content=self.get_content(root)
        for next_name in cake_path.path:
            bundle = CakeRack(utf8_reader(content.stream()))
            try:
                next_cake = bundle[next_name]
            except:
                reraise_with_msg(f'{cake_path} {bundle.content()}')

            if next_cake.is_resolved():
                content = self.blob_store().get_content(next_cake)
            else:
                content = self.get_content(next_cake)
        if content.file_type == BINARY:
            content.file_type = guess_name(cake_path.filename())
            content.mime = file_types[self.file_type].mime
        return content


user_api = ApiCallRegistry()


class PrivilegedAccess(GuestAccess):
    api = user_api

    @staticmethod
    def system_access(ctx):
        return PrivilegedAccess(ctx, user_type=UserType.system)

    @user_api.call()
    def info(self):
        any_cake = Acl(None,PT.Read_Any_Data,None) \
                   in self.auth_user.acls()
        return {"isAuthenticated": True, "anyCakeAccess": any_cake}

    @user_api.call()
    def logout(self):
        session_id = self.ctx.params['session_id']
        user_session = self.ctx.srvcfg_session().query(UserSession)\
            .filter(UserSession.id == session_id).one()
        user_session.active = False

    def authorize_all(self, cakes, pts):
        autorized = set()
        for cake in cakes:
            if cake in autorized:
                continue
            self.authorize(cake, pts)
            autorized.add(cake)

    def writer(self):
        '''
            get writer object
        '''
        self.authorize(None, Permissions.write_data)
        return self.blob_store().writer()

    def write_content(self, fp, chunk_size=65355):
        '''
            Write content
        '''
        w = self.writer()
        while True:
            buf = fp.read(chunk_size)
            if len(buf) == 0:
                break
            w.write(buf)
        return w.done()


    @user_api.call()
    def store_directories(self, directories):
        '''
        store_directories(directories)    -> data_cake        Write_Any_Data
            Write data

        :param directories:
        :return:
        '''
        self.authorize(None, Permissions.write_data)
        name2cakepath = tuple_mapper(
            CakePath.ensure_it_or_none,
            Cake.ensure_it,
            CakeRack.ensure_it)
        directories = map(name2cakepath, directories)
        unseen_cakes = set()
        dirs_stored = set()
        dirs_mismatch_input_cake = set()

        def store_bundle(dir_cake, dir_contents):
            if not(dir_cake.has_data()):
                lookup = self.blob_store().lookup(dir_cake)
                if not lookup.found():
                    w = self.blob_store().writer()
                    w.write(bytes(dir_contents), done=True)
                    lookup = self.blob_store().lookup(dir_cake)
                    if lookup.found():
                        dirs_stored.add(dir_cake)
                    else: # pragma: no cover
                        dirs_mismatch_input_cake.add(dir_cake)
            for file_name in dir_contents:
                self._collect_unseen(dir_contents[file_name],
                                     unseen_cakes)

        for cake_path, dir_cake, dir_contents in directories:
            if cake_path is None or cake_path.root is None \
                    or cake_path.root.header.type == CakeType.PORTAL :
                store_bundle(dir_cake, dir_contents)
                if cake_path is not None and cake_path.is_root():
                    self.create_portal(portal_id=cake_path.root,
                                       cake=dir_cake)
            elif cake_path.root.header.type == CakeType.VTREE:
                path = cake_path.path_join()
                prev_dir = self._make_bundle(
                    self._query_vtree(cake_path.root, None)(
                        VolatileTree.parent_path == path).all())
                name2cakepath = tuple_mapper(None,cake_path.child)
                patches = [name2cakepath(t) for t in
                           dir_contents.merge(prev_dir)]
                dirs_stored.add(dir_cake)
                unseen_cakes.update(self.edit_portal_tree(patches))
            else:
                raise AssertionError('cannot store: {cake_path!s} '
                                     '{cake_path.root.header.type!s}'
                                     .format(**locals()))

        if len(dirs_mismatch_input_cake) > 0: # pragma: no cover
            raise AssertionError('could not store directories: %r' %
                                 dirs_mismatch_input_cake)
        return len(dirs_stored), list(unseen_cakes)

    def _collect_unseen(self, cake, unseen_set):
        if not cake.has_data():
            lookup = self.blob_store().lookup(cake)
            if not lookup.found():
                unseen_set.add(cake)

    def add_user(self, email, ssha_pwd, full_name = None):
        self.authorize(None, (PT.Admin,))
        self.ctx.glue_session().merge(User(email=email, passwd=ssha_pwd,
                         full_name=full_name,
                         user_state=UserState.active))

    def remove_user(self, user_or_email):
        self.authorize(None, (PT.Admin,))
        user = dal.find_normal_user(self.ctx.glue_session(), user_or_email)
        user.user_state = UserState.disabled

    def add_acl(self, user_or_email, acl):
        self.authorize(None, (PT.Admin,))
        user = self.ensure_user(user_or_email)
        session = self.ctx.glue_session()
        if acl is not None:
            if len(dal.find_permissions(session, user, acl)) == 0:
                session.add(Permission(
                    user=user,
                    permission_type=acl.permission_type,
                    cake=acl.cake))
        return user, sorted(user.permissions, key=dal.PERM_SORT)

    def remove_acl(self, user_or_email, acl):
        self.authorize(None, (PT.Admin,))
        session = self.ctx.glue_session()
        user = self.ensure_user(user_or_email)
        perms = dal.find_permissions(session, user, acl)
        if len(perms) > 0 :
            session.delete(perms[0])
        return user, sorted(user.permissions, key=dal.PERM_SORT)

    @user_api.query()
    def list_acls(self):
        ''' show all acls for user'''
        return [{"permission": p.permission_type.name ,
                  "cake": p.cake }
                 for p in self.auth_user.permissions]


    @user_api.call()
    def create_portal(self, portal_id, cake):
        '''
        create portal pointing to cake, if portal is already exist -
        fail.

        This call could be used to edit portal if portal is owned
        by user.

        '''
        portal_id = Cake.ensure_it(portal_id)
        portal_id.assert_portal()
        self.authorize(None, (PT.Create_Portals,))
        cake = Cake.ensure_it_or_none(cake)
        cake_session = self.ctx.cake_session(portal_id)
        portal_in_db = cake_session.query(Portal).\
            filter(Portal.id == portal_id).one_or_none()
        add_portal = portal_in_db is None
        already_own = False
        if not add_portal:
            try:
                self.authorize(portal_id, (PT.Own_Portal_,))
                already_own = True
            except NotAuthorizedError:
                pass

        if add_portal or already_own:
            dal.edit_portal(cake_session,
                            Portal(id=portal_id, latest=cake),
                            self.auth_user)
            if not already_own:
                self.ctx.glue_session().add(Permission(
                    user=self.auth_user,
                    permission_type=PT.Own_Portal_,
                    cake=portal_id))
        else:
            raise AssertionError('portal %r is already exists.' %
                                 portal_id)

    @user_api.call()
    def edit_portal(self, portal_id, cake):
        '''
        change cake that portal points too
        '''
        portal_id, cake = map(Cake.ensure_it,(portal_id,cake))
        portal_id.assert_portal()
        self.authorize(portal_id, (PT.Edit_Portal_, PT.Admin))
        cake_session = self.ctx.cake_session(portal_id)
        portal = cake_session.query(Portal).\
            filter(Portal.id == portal_id).one_or_none()
        if portal is not None:
            portal.latest = cake
            dal.edit_portal(cake_session,
                            Portal(id=portal_id, latest=cake),
                            self.auth_user)
        else:
            raise AssertionError('portal %r does not exists.' %
                                 portal_id)

    def _assert_vtree_(self, cake_path):
        cake_path = CakePath.ensure_it(cake_path)
        if cake_path.relative():
            raise ValueError('cake_path has to be absolute: %r'
                             % cake_path)
        CakeType.VTREE.assert_equals(cake_path.root.header.type)
        return cake_path

    def _read_vtree(self, cake_path, asof_dt=None):
        cake_path = self._assert_vtree_(cake_path)
        path = cake_path.path_join()
        query = self._query_vtree(cake_path.root, asof_dt)
        neuron_maybe = query(VolatileTree.path == path).one_or_none()
        if neuron_maybe.cake is None: # yes it is
            namedCakes = self._make_bundle(
                query(VolatileTree.parent_path == path).all())
            content = Content.from_data_and_role(
                role=CakeRole.NEURON, data=bytes(namedCakes))
            content.created_dt=neuron_maybe.start_dt
            return content
        else:
            return self.get_content(neuron_maybe.cake)

    @staticmethod
    def _make_bundle(vtree_rs):
        namedCakes = CakeRack()
        for child in vtree_rs:
            if child.path == '':
                continue
            _, file = os.path.split(child.path)
            namedCakes[file] = child.cake
        return namedCakes

    def _query_vtree(self, portal_id, asof_dt):
        def query(path_condition):
            cake_session = self.ctx.cake_session(portal_id)
            VT = VolatileTree
            if asof_dt is not None:
                condition = and_(
                    VT.portal_id == portal_id,
                    path_condition,
                    VT.start_dt <= asof_dt,
                    or_(VT.end_dt == None, VT.end_dt > asof_dt))
            else:
                condition = and_(
                    VT.portal_id == portal_id,
                    path_condition,
                    VT.end_dt == None)
            return cake_session.query(VolatileTree).filter(condition)
        return query

    def _read_dmount(self, cake_path, asof_dt=None):
        raise AssertionError('not impl')

    @user_api.call()
    def edit_portal_tree(self, files, asof_dt=None):
        '''
        update path with cake in portal_tree
        '''
        ensure_types = tuple_mapper(PatchAction.ensure_it,
                                    self._assert_vtree_,
                                    Cake.ensure_it_or_none )
        files = list(map(ensure_types,files))
        roots = set(t[1].root for t in files)
        for root in roots:
            in_db = self.ctx.cake_session(root).query(Portal)\
                .filter(Portal.id == root).one_or_none()
            if in_db is None:
                self.create_portal(root, None)
        self.auth_user.acls(force_refresh=True)
        self.authorize_all(roots,(PT.Edit_Portal_, PT.Admin))
        VT = VolatileTree
        if asof_dt is None:
            asof_dt = datetime.datetime.utcnow()
        unseen_cakes = set()

        def add_cake_to_vtree(action, cake_path, cake):
            if action == PatchAction.delete:
                self.delete_in_portal_tree(cake_path,asof_dt)
            else:
                portal_id = cake_path.root
                path = cake_path.path_join()
                parent = cake_path.parent()
                cake_session = self.ctx.cake_session(portal_id)
                under_edit = cake_session.query(VT)\
                    .filter(
                        VT.portal_id == portal_id,
                        VT.path == cake_path.path_join(),
                        VT.end_dt == None
                    ).one_or_none()
                change = True
                if under_edit is not None:
                    if under_edit.cake is None:
                        raise AssertionError(
                            'cannot overwrite %s with %s' %
                            (CakeRole.NEURON, CakeRole.SYNAPSE))
                    if under_edit.start_dt > asof_dt:
                        raise ValueError(
                            "cannot endate under_edit:%r for asof_dt:%r " %
                            (under_edit,asof_dt))
                    if under_edit.cake != cake:
                        under_edit.end_dt = asof_dt
                        under_edit.end_by = self.auth_user.id
                        cake_session.add(under_edit)
                    else:
                        change = False
                if change:
                    parent_path = parent.path_join()
                    cake_session.add(VT(
                        portal_id=portal_id,
                        path=path,
                        parent_path=parent_path,
                        start_by=self.auth_user.id,
                        cake=cake,
                        start_dt=asof_dt))
                    self._collect_unseen(cake, unseen_cakes)
                    dal.ensure_vtree_path(cake_session, parent, asof_dt,
                                          self.auth_user)

        for action, cake_path, cake in files:
            add_cake_to_vtree(action,cake_path,cake)
        return list(unseen_cakes)

    @user_api.call()
    def delete_in_portal_tree(self, cake_path, asof_dt = None):
        cake_path = self._assert_vtree_(cake_path)
        self.authorize(cake_path.root, (PT.Edit_Portal_, PT.Admin))
        path = cake_path.path_join()
        VT = VolatileTree
        cake_session = self.ctx.cake_session(cake_path.root)
        if asof_dt is None:
            asof_dt = datetime.datetime.utcnow()
        delete_root = cake_session.query(VT) \
            .filter(
                VT.portal_id == cake_path.root,
                VT.path == path,
                VT.end_dt == None
            ).one_or_none()
        if delete_root is None:
            return False
        if delete_root.start_dt > asof_dt:
            raise ValueError( "cannot endate :%r for asof_dt:%r " %
                              (delete_root, asof_dt))
        if delete_root.cake is not None:
            delete_root.end_dt = asof_dt
            delete_root.end_by = self.auth_user.id
        else:
            rc = cake_session.query(VT).filter(
                VT.portal_id == cake_path.root,
                or_(VT.path == path,
                    VT.path.startswith(path+'/', autoescape=True)),
                VT.end_dt == None
            ).update({VT.end_dt: asof_dt,
                      VT.end_by: self.auth_user.id},
                     synchronize_session=False)
        return True

    @user_api.call()
    def get_portal_tree(self, portal_id, asof_dt=None):
        '''
        read whole tree into `CakeTree`
        '''
        portal_id = Cake.ensure_it(portal_id)
        if portal_id.type != CakeType.VTREE:
            raise AssertionError("%s is not a TREE:%s " % (
                portal_id, portal_id.type, ))
        VT = VolatileTree
        if asof_dt is not None:
            condition = and_(VT.portal_id == portal_id, VT.start_dt <= asof_dt,
                             or_(VT.end_dt == None, VT.end_dt > asof_dt))
        else:
            condition = and_(VT.portal_id == portal_id, VT.end_dt == None)
        tree_paths = self.ctx.cake_session(portal_id).query(VT).filter(
            condition).all()
        tree = CakeTree(portal=portal_id)
        for r in tree_paths:
            tree[r.path] = r.cake
        return tree

    @user_api.call()
    def grant_portal(self, portal_id, grantee, permission_type):
        '''
        grant Read_, Edit_Portal_ or Own_Portal_ permission to
        grantee. `user has to have PT.Own_Portal_ or PT.Admin to do
        this.
        '''
        portal_id = Cake.ensure_it(portal_id)
        portal_id.assert_portal()
        self.authorize(portal_id, (PT.Own_Portal_, PT.Admin))

        portal = self.ctx.cake_session(portal_id).query(Portal).\
            filter(Portal.id == portal_id).one()
        if permission_type not in Permissions.portals:
            raise AssertionError('pt:%r has to be one of %r' %
                                 (permission_type,
                                  Permissions.portals))

        grantee = self.ensure_user(grantee)

        if portal is not None:
            self.ctx.glue_session().add(Permission(
                user=grantee,
                permission_type=permission_type,
                cake=portal.id))
        else:
            raise AssertionError('portal %r does not exists.' %
                                 portal_id)

    @user_api.call()
    def delete_portal(self, portal_id):
        '''
        disown portal, if nobody owns it deactivate it in
        Portal table
        '''
        portal_id = Cake.ensure_it(portal_id)
        portal_id.assert_portal()
        self.authorize(portal_id, (PT.Own_Portal_, PT.Admin))
        portal = self.ctx.cake_session(portal_id).query(Portal).\
            filter(Portal.id == portal_id).one()
        portal.active=False


