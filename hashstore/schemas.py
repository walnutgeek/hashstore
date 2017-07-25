from hashstore.ids import Cake, Cake_TYPE
from hashstore.content_address import ContentAddress_TYPE
from sqlalchemy import *
import datetime
import enum
import os

class UserType(enum.Enum):
    mount = 1
    user = 2
    server = 3

auth_meta = MetaData()

invitation = Table(
    'invitation', auth_meta,
    Column('invitation_id', Cake_TYPE, primary_key=True,
           default=lambda: Cake.new_guid()),
    Column('invitation_body', JSON),
    Column('door_id', None, ForeignKey("door.door_id")),
    Column('active', Boolean),
    Column('created_user_id', None, ForeignKey("user.user_id"),
           nullable=True),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('updated_dt', DateTime, nullable=True,
           onupdate = lambda: datetime.datetime.utcnow()),
    )

user = Table(
    'user', auth_meta,
    Column('user_id', Cake_TYPE, primary_key=True,
        default=lambda: Cake.new_guid()),
    Column('user_type', Enum(UserType), nullable=False),
    Column('mount_session', Cake_TYPE, nullable=False),
    Column('user_details', JSON),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    )

auth = Table(
    'auth', auth_meta,
    Column('session_id', Cake_TYPE, primary_key=True,
           default=lambda: Cake.new_guid()),
    Column('user_id', None, ForeignKey("user.user_id")),
    Column('active', Boolean),
    Column('session_details', JSON),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('updated_dt', DateTime, nullable=True,
           onupdate = lambda: datetime.datetime.utcnow()),
    )

door = Table(
    'door', auth_meta,
    Column('door_id', Cake_TYPE, primary_key=True),
    Column('latest_value', Cake_TYPE, nullable=True),
    Column('door_config', JSON),
    )

rule = Table(
    'rule', auth_meta,
    Column('rule_id', Cake_TYPE, primary_key=True,
           default=lambda: Cake.new_guid()),
    Column('user_id', None, ForeignKey("user.user_id")),
    Column('door_id', None, ForeignKey("door.door_id")),
    Column('rule_body', JSON),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('updated_dt', DateTime, nullable=True,
           onupdate = lambda: datetime.datetime.utcnow())
    )


door_event = Table(
    'door_event', auth_meta,
    Column('event_id', Cake_TYPE, primary_key=True,
           default=lambda: Cake.new_guid()),
    Column('door_id', None, ForeignKey("door.door_id"),
           nullable=False),
    Column('modified_by', None, ForeignKey("user.user_id")),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('value', Cake_TYPE, nullable=False),
    )


incoming_meta = MetaData()

incoming = Table('incoming', incoming_meta,
    Column('incoming_id', Integer,
           primary_key=True, autoincrement=True),
    Column('file_id', ContentAddress_TYPE, nullable=True),
    Column('new', Boolean),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('updated_dt', DateTime, nullable=True,
           onupdate = lambda: datetime.datetime.utcnow())
    )

shard_meta = MetaData()

blob = Table('blob', shard_meta,
    Column('blob_id', Integer,
           primary_key=True, autoincrement=True),
    Column('file_id', ContentAddress_TYPE, nullable=False),
    Column('content', LargeBinary),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    )

shard = Table(
    'shard', shard_meta,
    Column('cake', Cake_TYPE, primary_key=True),
    Column('file_id', ContentAddress_TYPE, nullable=False),
    Column('blob_id', None, ForeignKey('blob.blob_id'), nullable=True),
    )


