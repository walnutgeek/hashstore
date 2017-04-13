from nose.tools import eq_,ok_,with_setup
import hashstore.shash as shash
from hashstore.tests import TestSetup
import sys

test = TestSetup(__name__,ensure_empty=True)
log = test.log

def test_args_parser():
    p = shash.args_parser()
    args = p.parse_args(["start", "--port", "345"])
    eq_(args.command, "start")
    eq_(args.port, 345)

    args = p.parse_args(["start", "--port", "345",
                         '--store_dir', '/u1/abc/store'])
    eq_(args.command, "start")
    eq_(args.port, 345)
    eq_(args.store_dir, '/u1/abc/store')
    eq_(args.secure, True)

    args = p.parse_args(["start", "--port", "345",
                         '--store_dir', '/u1/abc/store' ,'--insecure'])
    eq_(args.command, "start")
    eq_(args.port, 345)
    eq_(args.store_dir, '/u1/abc/store')
    eq_(args.secure, False)

    args = p.parse_args(["stop", "--port", "345"])
    eq_(args.command, "stop")
    eq_(args.port, 345)

    args = p.parse_args("register --url http://abc:345 "
                        "--dir /u1/abc/docs".split())
    eq_(args.command, "register")
    eq_(args.url, "http://abc:345")
    eq_(args.dir, '/u1/abc/docs')

    args = p.parse_args(["register", "--url", "http://abc:345",
                         "--dir", "/u1/abc/docs"])
    eq_(args.command, "register")
    eq_(args.url, "http://abc:345")
    eq_(args.dir, '/u1/abc/docs')

    args = p.parse_args(["backup", "--dir", "/u1/abc/docs"])
    eq_(args.command, "backup")
    eq_(args.dir, '/u1/abc/docs')

    try:

        args = p.parse_args(["-h"])
        ok_(False)
    except SystemExit:
        pass

    save_err = sys.stderr
    sys.stderr = sys.stdout
    try:
        args = p.parse_args(["abc"])
        ok_(False)
    except SystemExit:
        pass
    sys.stderr = save_err

