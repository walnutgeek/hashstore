from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Enum, ForeignKey, Column, String
from hashstore.bakery.db_mixins import ReprIt, GuidPk, Cdt, Udt
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


class User(GuidPk, Cdt, Udt, ReprIt, Base):
    __tablename__ = 'users'
    email= Column(String, nullable=False)
    user_state = Column(Enum(UserState), nullable=False)
    passwd = Column(SSHA_TYPE, nullable=False)
    name = Column(String, nullable=True)


class Door(GuidPk, Cdt, Udt, Base):
    __tablename__ = 'doors'
    latest = Column(Cake_TYPE, nullable=True)


class DoorEvent(GuidPk, Cdt, Base):
    __tablename__ = 'door_events'
    door_id =  Column(None, ForeignKey('doors.id'))
    modified_by = Column(None, ForeignKey('users.id'))
    cake = Column(Cake_TYPE, nullable=False)


class Permission(GuidPk, Cdt, Udt, Base):
    __tablename__ = 'permissions'
    door_id = Column(None, ForeignKey('doors.id'))
    user_id = Column(None, ForeignKey('users.id'))
    cake = Column(Cake_TYPE, nullable=False)
    permission_type = Column(Enum(PermissionType), nullable=False)


class HostType(enum.Enum):
    client = 0
    server = 1


class Host(GuidPk, Cdt, Udt, Base):
    __tablename__ = 'known_hosts'
    id = Column(Cake_TYPE, primary_key=True)
    secret = Column(SSHA_TYPE,nullable=False)
    host_name = Column(String)
    host_type = Column(Enum(HostType))
    authorized = Column(None, ForeignKey('users.id'), nullable=True)


# not part of replicated state
class Session(GuidPk,Cdt,Udt,ReprIt, Base):
    __tablename__ = 'user_sessions'
    user = Column(None, ForeignKey('users.id'), nullable=True)
    host = Column(None, ForeignKey('known_hosts.id'), nullable=True)
    state = Column(String)

