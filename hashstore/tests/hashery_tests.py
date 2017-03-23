import os
import time
from nose.tools import eq_,ok_,with_setup

import hashstore.mount as mount

from hashstore.tests import zzzetup, file_set1, file_set2, prep_mount, run_bg

log,test_dir = zzzetup(__name__,ensure_enpty=True)


test_config = os.path.join(os.path.dirname(__file__), 'hashery.back-it-up')
substitutions = {'{test_dir}': test_dir}

import hashstore.backup

def test_backup():
    hashery_dir = os.path.join(test_dir, 'hashery')
    os.makedirs(hashery_dir)
    port = 9753
    run_bg('hashstore.hashery',[
        '--dir', hashery_dir,
        '--port',str(port) ], os.path.join(test_dir, 'hashery.log') )
    time.sleep(2)
    files = os.path.join(test_dir, 'files')
    prep_mount(files, file_set1)
    b = hashstore.backup.Backup(test_config, os.path.join(test_dir,'backup.db'), substitutions)
    v1 = b.backup()
    prep_mount(files, file_set2)
    v2 = b.backup()
    h1 = 'X88a9b058784619c42e4d630812a8d0a20cd112a1b97d9735c4542bf7ac0664c5'
    eq_(str(v1[files]), h1)
    h2 = 'X2f55b6a35d6b1b528262d45a3b57363867b3ce5e7ab77cb2ed3ec663173ae712'
    eq_(str(v2[files]), h2)
    f1 = os.path.join(test_dir, 'files1')
    b.restore(v1[files], f1)
    f2 = os.path.join(test_dir, 'files2')
    b.restore(v2[files], f2)
    eq_(str(mount.MountDB(f1).scan()[1]), h1)
    eq_(str(mount.MountDB(f2).scan()[1]), h2)
    run_bg('hashstore.hashery',[ '--shutdown', '--port',str(port)],
           os.path.join(test_dir, 'shut.log') )
