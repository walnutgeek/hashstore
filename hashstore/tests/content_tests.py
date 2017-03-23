import os
import six
import shutil
import logging
from .. import content
from nose.tools import eq_,ok_,with_setup

test_dir = os.path.join(os.path.abspath("test-out"),__name__)
if os.path.isdir(test_dir):
    shutil.rmtree(test_dir)
os.makedirs(test_dir)

log = logging.getLogger(__name__)

def test_ticker_portfolio():
    c = content.ContentDB('')
    log.debug(c.schema)
    # ok_(False)