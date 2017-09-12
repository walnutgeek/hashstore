from hashstore.bakery.ids import Cake, NamedCAKes, CakePath

from hashstore.ndb.models.server_config import ServerKey, \
    ServerConfigBase
from hashstore.ndb.models.glue import PortalType, Portal, \
    PortalHistory, GlueBase, User, UserState, Permission, \
    PermissionType, Acl

from sqlalchemy import or_, and_



def find_user(glue_sess, user_or_email):
    if '@' in user_or_email:
        column = User.email
    else:
        column = User.id
        user_or_email = Cake.ensure_it(user_or_email)
    return glue_sess.query(User).filter(column == user_or_email).one()


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
        cake_stack.append(cake)
        if cake.is_resolved() or cake.has_data():
            return cake_stack
        if len(cake_stack) > 10:
            raise AssertionError('cake loop? %r' % cake_stack)
        cake = glue_sess.query(Portal).filter(Portal.id == cake)\
            .one().latest

def edit_portal(glue_sess,portal):
    glue_sess.merge(portal)
    glue_sess.add(PortalHistory(portal_id=portal.id,
                                cake=portal.latest))

PERM_SORT = lambda r: (r.permission_type.name, str(r.cake))
