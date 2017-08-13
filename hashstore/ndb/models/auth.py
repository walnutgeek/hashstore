from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Enum, ForeignKey, Column, String, Boolean
from hashstore.ndb.mixins import ReprIt, GuidPk, Cdt, Udt, \
    NameIt, ServersMixin
from hashstore.ids import Cake_TYPE, SSHA_TYPE
import enum


Base = declarative_base()


class PermissionType(enum.Enum):
    Read_Particular_Cake = 0
    ''' `cake` field is not null 
    Allows to read any `CakePath` that start with that cake 
    '''
    Read_Any_Cake = 1
    ''' global permission
    Allows to read any existing `Cake` or `CakePath` 
    '''
    Write_Any_Data = 2
    ''' global permission
    Allows to write any data and generate new content address 
    based cakes. 
    Permission assumes `Read_Any_Cake` permission.
    '''
    Write_Particular_Door = 3
    ''' `cake` field is not null and points to existing doors.door_id 
    you can upload any data, and repoint particular door_id to it
    Permission assumes `Write_Any_Data` permission.
    '''
    Create_New_Doors = 4
    ''' global permission
    Allows to write any data and generate new doors. New doors will 
    be automatically assigned `Own_Particular_Door` pemission to that 
    user. Permission assumes `Write_Any_Data` permission.
    '''
    Own_Particular_Door = 5
    ''' `cake` field is not null and points to existing doors.door_id 
     read, write and grant rights to that door
    '''
    Admin = 42
    '''global permission
    can read, write create doors and grant rights to anything
    '''


class UserState(enum.Enum):
    disabled = 0
    active = 1
    invitation = 2


class User(GuidPk, NameIt, Cdt, Udt, ReprIt, Base):
    email= Column(String, nullable=False)
    user_state = Column(Enum(UserState), nullable=False)
    passwd = Column(SSHA_TYPE, nullable=False)
    name = Column(String, nullable=True)


class Portal(GuidPk, NameIt, Cdt, Udt, Base):
    latest = Column(Cake_TYPE, nullable=True)
    service = Column(Boolean, nullable=False, default=False)


class PortalRoute(GuidPk, NameIt, Cdt, Base):
    portal_id = Column(None, ForeignKey('portal.id'))
    modified_by = Column(None, ForeignKey('user.id'))
    cake = Column(Cake_TYPE, nullable=False)


class Permission(GuidPk, NameIt, Cdt, Udt, Base):
    door_id = Column(None, ForeignKey('portal.id'))
    user_id = Column(None, ForeignKey('user.id'))
    cake = Column(Cake_TYPE, nullable=False)
    permission_type = Column(Enum(PermissionType), nullable=False)


class Server(ServersMixin, Base):
    seen_by = Column(None,ForeignKey('server.id'))
    services = relationship('Portal', secondary="service_home")


class ServiceHome(NameIt,Base):
    server_id = Column(None, ForeignKey("server.id"), primary_key=True)
    service_id = Column(None, ForeignKey("portal.id"), primary_key=True)
