from hashstore.bakery import Cake, NamedCAKes, CakePath, Role

from hashstore.ndb.models.server_config import ServerKey, \
    ServerConfigBase
from hashstore.ndb.models.glue import Portal, \
    PortalHistory, User, Permission, VolatileTree, UserType

from sqlalchemy import or_, and_

from hashstore.utils import is_str


def find_normal_user(glue_sess, user_or_email):
    if is_str(user_or_email) and '@' in user_or_email:
        column = User.email
    else:
        column = User.id
        user_or_email = Cake.ensure_it(user_or_email)
    return glue_sess.query(User)\
        .filter(column == user_or_email,
                User.user_type == UserType.normal).one()


def find_permissions(glue_sess, user, *acls):
    condition = Permission.user == user
    n_acls = len(acls)
    if n_acls > 0:
        from_acls = [acl.condition() for acl in acls]
        if n_acls == 1:
            condition = and_( condition, from_acls[0])
        else:
            condition = and_( condition,  or_(*from_acls))
    return glue_sess.query(Permission).filter(condition).all()


def resolve_cake_stack(glue_sess, cake):
    cake_stack = []
    while True:
        cake_loop = cake in cake_stack
        cake_stack.append(cake)
        if cake.is_immutable():
            return cake_stack
        if cake_loop or len(cake_stack) > 10:
            raise AssertionError('cake loop? %r' % cake_stack)
        cake = glue_sess.query(Portal).filter(Portal.id == cake)\
            .one().latest


def ensure_vtree_path(glue_sess, cake_path, asof_dt, user):
    if cake_path is None:
        return
    parent = cake_path.parent()
    VT = VolatileTree
    parent_path = '' if parent is None else parent.path_join()
    path = cake_path.path_join()
    entry = glue_sess.query(VT) \
        .filter(
            VT.portal_id == cake_path.root,
            VT.path == path,
            VT.end_dt == None
        ).one_or_none()
    add = entry is None
    if not(add) and entry.cake is not None:
        raise AssertionError(
            'cannot overwrite %s with %s' %
            (Role.SYNAPSE, Role.NEURON))
    if add:
        glue_sess.add(VT(
            portal_id=cake_path.root,
            path=path,
            parent_path=parent_path,
            start_by=user.id,
            cake=None,
            start_dt=asof_dt,
            end_dt=None
        ))
        ensure_vtree_path(glue_sess, parent, asof_dt, user)


def edit_portal(glue_sess,portal):
    glue_sess.merge(portal)
    if portal.latest is not None:
        glue_sess.add(PortalHistory(portal_id=portal.id,
                                    cake=portal.latest))

def query_users_by_type(glue_session, user_type):
    return glue_session.query(User).filter(
        User.user_type == user_type)

def get_special_users(glue_session):
    return tuple(query_users_by_type(glue_session, t).one_or_none()
                 for t in (UserType.guest, UserType.system))

PERM_SORT = lambda r: (r.permission_type.name, str(r.cake))
