from hashstore.tests import TestSetup

test = TestSetup(__name__,ensure_empty=True)
log = test.log


def test_hsi():
    '''
usage: hsi.py [-h] [--debug] {login,logout,ls,find,scan,backup,pull,sync} ...

hsi - hashstore client

positional arguments:
  {login,logout,ls,find,scan,backup,pull,sync}
    login               authorize client to interact with server
    logout              logout from server
    ls                  list directory as of last scan.
    find                find file with particular criteria.
    scan                scan tree and recalculate hashes for all changed files
    backup              save local files on remote server
    pull                download remote changes for a dir
    sync                backup and pull. Use dir_id as portal.

optional arguments:
  -h, --help            show this help message and exit
  --debug               set logging level to DEBUG. default is INFO
    '''
    test.run_script_and_wait('hsi -h',expect_rc=0,
                             expect_read=test_hsi.__doc__)


def test_hsd():
    '''
usage: hsd.py [-h] [--store_dir store_dir] [--debug]
              {initdb,add_user,remove_user,acl,start,stop} ...

hsd - hashstore server

positional arguments:
  {initdb,add_user,remove_user,acl,start,stop}
    initdb              initialize storage and set host specific parameters
    add_user
    remove_user
    acl                 Manage ACL
    start               start server
    stop                stop server

optional arguments:
  -h, --help            show this help message and exit
  --store_dir store_dir
                        a directory where hashstore data resides. Default is:
                        '.'.
  --debug               set logging level to DEBUG. default is INFO
    '''
    test.run_script_and_wait('hsd -h',expect_rc=0,
                             expect_read=test_hsd.__doc__)
