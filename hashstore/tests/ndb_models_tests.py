from nose.tools import eq_,ok_
import hashstore.ids as ids
from hashstore.tests import TestSetup, doctest_it

from sqlalchemy import Table, MetaData, Column, types, select

from hashstore.ndb import Dbf
import hashstore.ndb.models.server as server
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__,ensure_empty=True)
log = test.log



def test_server():

    #'sqlite:///:memory:'

    pass


