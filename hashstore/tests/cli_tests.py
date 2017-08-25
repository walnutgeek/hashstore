from hashstore.tests import TestSetup, file_set1, file_set2, \
    prep_mount, update_mount, fileset1_cake, fileset2_cake
import os

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


def test_scan_ls():
    files = os.path.join(test.dir, 'files')
    prep_mount(files, file_set1)

    test.run_script_and_wait('hsi scan --dir %s' % files,expect_rc=0,
                             expect_read=fileset1_cake)

    test.run_script_and_wait('hsi ls --dir %s' % files,expect_rc=0,
                             expect_read='''
          DirId: ...
          Cake: %s
          
            FILE  105000  too.sol
            DIR   10955   q
            DIR   1885    x
            DIR   1659    a
          total_size: 119499''' % fileset1_cake)

    update_mount(files, file_set2)

    test.run_script_and_wait('hsi scan --dir %s' % files, expect_rc=0,
                             expect_read=fileset2_cake)

    test.run_script_and_wait('hsi ls --dir %s' % files, expect_rc=0,
                             expect_read='''
          DirId: ...
          Cake: %s

            DIR   107941  x
            FILE  105000  too.sol
            DIR   10955   q
            DIR   1743    a
          total_size: 225639''' % fileset2_cake)
