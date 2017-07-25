from nose.tools import eq_,ok_
import hashstore.ids as ids
import six
from hashstore.utils import ensure_bytes
from hashstore.tests import TestSetup, doctest_it

from sqlalchemy import Table, MetaData, Column, types, \
    create_engine, select

import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_docs():
    import hashstore.content_address as test_subject
    doctest_it(test_subject)





