from hashstore.ids import Cake, Cake_TYPE
from sqlalchemy import *
import datetime
import enum


class ActorType(enum.Enum):
    mount = 1
    user = 2
    server = 3

auth_meta = MetaData()
meta = auth_meta

invitation = Table(
    'invitation', auth_meta,
    Column('invitation_id', Cake_TYPE, primary_key=True,
           default=lambda: Cake.new_guid()),
    Column('active', Boolean),
    Column('created_actor_id', None, ForeignKey("actor.actor_id"),
           nullable=True),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('updated_dt', DateTime, nullable=True,
           onupdate = lambda: datetime.datetime.utcnow()),
    )

actor = Table(
    'actor', auth_meta,
    Column('actor_id', Cake_TYPE, primary_key=True,
        default=lambda: Cake.new_guid()),
    Column('actor_type', Enum(ActorType), nullable=False),
    Column('alias', String, nullable=False, unique=True, index=True),
    Column('secret', String, nullable=False),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('updated_dt', DateTime, nullable=True,
           onupdate = lambda: datetime.datetime.utcnow()),
    )

session = Table(
    'session', auth_meta,
    Column('session_id', Cake_TYPE, primary_key=True,
           default=lambda: Cake.new_guid()),
    Column('actor_id', None, ForeignKey("actor.actor_id")),
    Column('active', Boolean),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('updated_dt', DateTime, nullable=True,
           onupdate = lambda: datetime.datetime.utcnow()),
    )

door = Table(
    'door', auth_meta,
    Column('door_id', Cake_TYPE, primary_key=True),
    Column('latest_cake', Cake_TYPE, nullable=True),
    Column('retention_details', String),
    )

door_event = Table(
    'event', auth_meta,
    Column('event_id', Cake_TYPE, primary_key=True,
           default=lambda: Cake.new_guid()),
    Column('door_id', None, ForeignKey("door.door_id"),
           nullable=False),
    Column('modified_by', None, ForeignKey("actor.actor_id")),
    Column('created_dt', DateTime,
           default = lambda: datetime.datetime.utcnow()),
    Column('cake', Cake_TYPE, nullable=False),
    )


