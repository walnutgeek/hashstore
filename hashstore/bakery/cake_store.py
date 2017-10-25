import os
from hashstore.bakery import NotAuthorizedError, CredentialsError, \
    Content, Cake, NamedCAKes, CakePath, SaltedSha, check_favorite_name
from hashstore.bakery.backend import LiteBackend
from hashstore.ndb import Dbf, MultiSessionContextManager
from hashstore.utils import ensure_dict,reraise_with_msg
import hashstore.bakery.dal as dal

from hashstore.ndb.models.server_config import UserSession, ServerKey, \
    ServerConfigBase
from hashstore.ndb.models.glue import PortalType, Portal, \
    GlueBase, User, UserState, Permission, \
    PermissionType as PT, Acl, Favorite

import logging

from hashstore.utils.api import ApiCallRegistry

log = logging.getLogger(__name__)

FROM_COOKIE='FROM_COOKIE'

class StoreContext(MultiSessionContextManager):
    def __init__(self, store, remote_host=None):
        MultiSessionContextManager.__init__(self)
        self.store = store
        self.remote_host = remote_host
        self.params = {}

    def session_factory(self, name):
        return getattr(self.store, name +'_db').session()

    @MultiSessionContextManager.decorate
    def glue_session(self):  # pragma: no cover
        pass

    @MultiSessionContextManager.decorate
    def srvcfg_session(self):  # pragma: no cover
        pass

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
                return PrivilegedAccess(self, user_session.user)
        raise CredentialsError('cannot validate session')


class _Access:
    def __init__(self, ctx):
        self.ctx = ctx

    def backend(self):
        return self.ctx.store.backend()

    def process_api_call(self, method, params):
        # log.debug("{self} {method}({params})".format(**locals()))
        return self.api.run(self, method, params)

guest_api = ApiCallRegistry()


class GuestAccess(_Access):
    api = guest_api

    @guest_api.call()
    def info(self):
        return {"isAuthenticated": False}

    @guest_api.call()
    def login(self, email, passwd, client_id=None):
        user = dal.find_user(self.ctx.glue_session(), email)
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

    def server_login(self, server_id, server_secret):
        pass # validate and create server session logic

user_api = ApiCallRegistry()


class PrivilegedAccess(_Access):
    api = user_api

    @user_api.call()
    def info(self):
        return {"isAuthenticated": True}

    @user_api.call()
    def logout(self):
        session_id = self.ctx.params['session_id']
        user_session = self.ctx.srvcfg_session().query(UserSession)\
            .filter(UserSession.id == session_id).one()
        user_session.active = False

    class Permissions:
        read_data_cake = (PT.Read_, PT.Read_Any_Data)
        read_portal = (PT.Read_, PT.Read_Any_Portal)
        write_data = (PT.Write_Any_Data,)
        portals = (PT.Read_, PT.Edit_Portal_, PT.Own_Portal_)

    def __init__(self, ctx, auth_user, system_access=False):
        _Access.__init__(self,ctx)
        self.system_access = system_access
        if self.system_access:
            self.auth_user = None
        else:
            self.auth_user = self.ensure_user(auth_user)

    @staticmethod
    def system_access(ctx):
        return PrivilegedAccess(ctx, None, system_access=True)

    def is_authenticated(self):
        return self.auth_user is not None

    def ensure_user(self, user):
        if isinstance(user, User):
            return user
        else:
            return dal.find_user(self.ctx.glue_session(), user)

    def authorize(self, cake, pts):
        if self.system_access:
            return
        required_acls = Acl.cake_acls(cake, pts)
        for acl in required_acls:
            if acl in self.auth_user.acls():
                return
        raise NotAuthorizedError('%s does not have %r permissions' %
                                 (self.auth_user.email, required_acls))

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
        if cake_or_path.has_data():
            return Content(data=cake_or_path.data())\
                .set_data_type(cake_or_path)
        elif cake_or_path.is_resolved():
            self.authorize(cake_or_path, self.Permissions.read_data_cake)
            return self.backend().get_content(cake_or_path)
        elif cake_or_path.is_portal():
            self.authorize(cake_or_path, self.Permissions.read_portal)
            resolution_stack = dal.resolve_cake_stack(
                self.ctx.glue_session(), cake_or_path)
            for resolved_portal in resolution_stack[:-1]:
                self.authorize(cake_or_path, self.Permissions.read_portal)
            return self.backend().get_content(resolution_stack[-1])
        else:
            raise AssertionError('should never get here')



    def writer(self):
        '''
            get writer object
        '''
        self.authorize(None, self.Permissions.write_data)
        return self.backend().writer()

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


    def get_content_by_path(self, cake_path):
        '''
        get_content_by_path (cake/a/b/c) -> cake     Read_, Read_Any_Data
                                                     Read_Any_Portal
            Read data behind cake, require specific Read_ permission or
            Read_Any_* . Also if there are portals in the path permissions
            will be validated on them before you able to proceed further.
        '''
        if cake_path.relative():
            raise AssertionError('path has to be absolute: %s '%cake_path)
        content=self.get_content(cake_path.root)
        for next_name in cake_path.path:
            bundle = NamedCAKes(content.stream())
            try:
                next_cake = bundle[next_name]
            except:
                reraise_with_msg(' %r %r' % (cake_path, bundle.content()))

            if next_cake.is_resolved():
                content = self.backend().get_content(next_cake)
            else:
                content = self.get_content(next_cake)
        return content

    #TODO query and
    # @user_api.call()
    # def get_query_cake_dict(self, query_names):
    #     query_cake_dict = {}
    #     return query_cake_dict
    #
    # @user_api.call()
    # def get_query_content(self, query_name):
    #     query_content = None
    #     return query_content

    @user_api.call()
    def store_directories(self, directories):
        '''
        store_directories(directories)    -> data_cake        Write_Any_Data
            Write data

        :param directories:
        :return:
        '''
        directories = ensure_dict( directories, Cake, NamedCAKes)
        unseen_cakes = set()
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
                        unseen_cakes.add(file_cake)
        if len(dirs_mismatch_input_cake) > 0: # pragma: no cover
            raise AssertionError('could not store directories: %r' %
                                 dirs_mismatch_input_cake)
        return len(dirs_stored), list(unseen_cakes)


    def add_user(self, email, ssha_pwd, full_name = None):
        self.authorize(None, (PT.Admin,))
        self.ctx.glue_session().merge(User(email=email, passwd=ssha_pwd,
                         full_name=full_name,
                         user_state=UserState.active))

    def remove_user(self, user_or_email):
        self.authorize(None, (PT.Admin,))
        user = dal.find_user(self.ctx.glue_session(), user_or_email)
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
    def list_acl_cakes(self):
        '''
        inspects Read_ permissions for user and return any specific
        cakes he allowed to see
        '''
        return [str(p.cake) for p in self.auth_user.permissions
            if p.permission_type.needs_cake()]

    @user_api.query()
    def favorites(self):
        '''
        loads user's favorites
        '''
        r = NamedCAKes()
        for p in self.auth_user.favorites:
            r[p.name] = p.cake
        return r

    @user_api.query()
    def save_favorite(self, name, cake):
        '''
        add cake to favorites than will
        '''
        self.authorize(cake, self.Permissions.read_data_cake)
        check_favorite_name(name)
        self.ctx.glue_session().merge(
            Favorite(name=name, cake=cake, user=self.auth_user))

    @user_api.query()
    def remove_favorite(self, name):
        '''
        remove favorite
        '''
        session = self.ctx.glue_session()
        fav = session.query(Favorite).filter(
            Favorite.name == name,
            Favorite.user == self.auth_user).one_or_none()
        if fav is None:
            raise ValueError("favorite does not exist:" + name)
        session.delete(fav)

    @user_api.call()
    def list_portals(self):
        '''
        :return: list all active portals known for storage
        '''
        self.authorize(None, (PT.Read_Any_Portal,))
        return self.ctx.glue_session().query(Portal)\
            .filter(Portal.active == True).all()

    @user_api.call()
    def create_portal(self, portal_id, cake,
                      portal_type = PortalType.content):
        '''
        create portal pointing to cake, if portal is already exist -
        fail. Tiny portals validated against majority of  servers to
        achieve consistency.

        This call could be used to edit portal if portal is owned
        by user.

        '''
        self.authorize(None, (PT.Create_Portals,))
        portal_id, cake = map(Cake.ensure_it,(portal_id,cake))
        if not portal_id.is_portal():
            raise AssertionError('has to be a portal: %r' % portal_id)
        form_db = self.ctx.glue_session().query(Portal).\
            filter(Portal.id == portal_id).one_or_none()
        add_portal = form_db is None
        already_own = False
        if not add_portal:
            try:
                self.authorize(portal_id, (PT.Own_Portal_,))
                already_own = True
            except NotAuthorizedError:
                pass

        if add_portal or already_own:
            dal.edit_portal(self.ctx.glue_session(),
                            Portal(id=portal_id, latest=cake,
                                   portal_type=portal_type))
            if self.is_authenticated():
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
        if not portal_id.is_portal():
            raise AssertionError('has to be a portal: %r' % portal_id)
        self.authorize(portal_id, (PT.Edit_Portal_, PT.Admin))
        portal = self.ctx.glue_session().query(Portal).\
            filter(Portal.id == portal_id).one_or_none()
        if portal is not None:
            portal.latest = cake
            dal.edit_portal(self.ctx.glue_session(),
                            Portal(id=portal_id, latest=cake))
        else:
            raise AssertionError('portal %r does not exists.' %
                                 portal_id)

    @user_api.call()
    def grant_portal(self, portal_id, grantee, permission_type):
        '''
        grant Read_, Edit_Portal_ or Own_Portal_ permission to
        grantee. `user has to have PT.Own_Portal_ or PT.Admin to do
        this.
        '''
        portal_id = Cake.ensure_it(portal_id)
        if not portal_id.is_portal():
            raise AssertionError('has to be a portal: %r' % portal_id)
        self.authorize(portal_id, (PT.Own_Portal_, PT.Admin))

        portal = self.ctx.glue_session().query(Portal).\
            filter(Portal.id == portal_id).one()
        if permission_type not in self.Permissions.portals:
            raise AssertionError('pt:%r has to be one of %r' %
                                 (permission_type,
                                  self.Permissions.portals))

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
        if not portal_id.is_portal():
            raise AssertionError('has to be a portal: %r' % portal_id)
        if self.is_authenticated():
            self.authorize(portal_id, (PT.Own_Portal_, PT.Admin))
            portal = self.ctx.glue_session().query(Portal).\
                filter(Portal.id == portal_id).one()
            portal.active=False


class CakeStore:
    def __init__(self, store_dir):
        self.store_dir = store_dir
        self._backend = None
        self.srvcfg_db = Dbf(ServerConfigBase.metadata,
                             os.path.join(self.store_dir, 'server.db'))
        self.glue_db = Dbf(GlueBase.metadata,
                           os.path.join(self.store_dir, 'glue.db'))

    def backend(self):
        if self._backend is None:
            self._backend = LiteBackend(
                os.path.join(self.store_dir, 'backend')
            )
        return self._backend

    def initdb(self, external_ip, port):
        if not os.path.exists(self.store_dir):
            os.makedirs(self.store_dir)
        self.srvcfg_db.ensure_db()
        os.chmod(self.srvcfg_db.path, 0o600)
        self.glue_db.ensure_db()
        self.backend()
        with self.srvcfg_db.session_scope() as session:
            skey = session.query(ServerKey).one_or_none()
            if skey is None:
                skey = ServerKey()
            skey.port = port
            skey.external_ip = external_ip
            session.merge(skey)

    def ctx(self):
        return StoreContext(self)

    def server_config(self):
        with self.srvcfg_db.session_scope() as session:
            return session.query(ServerKey).one()
