# hashstore

Content Addressable Storage written in python

See more: https://en.wikipedia.org/wiki/Content-addressable_storage

### Installation

```
pip install hashstore
```

### Use case: Backup

Start storage server
```
backup-host:~$ shash start --store_dir ~/store --port 9753 start &> store.log &
backup-host:~$
```

Create invitation
```
backup-host:~$ shash invite --store_dir ~/store
9d739ff3-c218-4a52-a6c3-22fb669c74df
backup-host:~$
```

Register directory to backup on
```
desktop:~$ shash register --dir ~/work --url http://backup-host:9753/ --invitation 9d739ff3-c218-4a52-a6c3-22fb669c74df
desktop:~$
```


Every time you want to backup:
```
desktop:~$ shash backup --dir ~/work
desktop:~$
```

`--dir` option could be ommited, then it assumed to be current directory.

```
desktop:~/work$ shash backup
desktop:~/work$
```


## Developer environment setup

You have to have miniconda3 instaled in path. `set_devenv.sh` will create 'py2' and
'py3' virtual environments with dependencies. `sniffer` will run tests on both
continuously.

```
$ bash ./set_devenv.sh
...

$ sniffer
Using scent:
.......................
----------------------------------------------------------------------
Ran 23 tests in 21.290s

OK
.......................
----------------------------------------------------------------------
Ran 23 tests in 20.471s

OK
{'py2': True, 'py3': True}
Name                       Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------
hashstore/__init__.py          0      0      0      0   100%
hashstore/backup.py           68      4     22      4    91%   28, 36, 94-95, 27->28, 35->36, 66->68, 77->exit
hashstore/db.py              425      6    192     15    97%   396, 410, 429, 432, 545-546, 96->exit, 97->exit, 98->97, 201->208, 227->224, 348->343, 391->397, 395->396, 409->410, 423->414, 428->429, 431->432, 607->609, 610->612, 614->617
hashstore/local_store.py     236      1     72      1    99%   213, 212->213
hashstore/mount.py           204      6     64      9    94%   244-245, 256, 297, 332-333, 37->43, 52->50, 115->117, 196->198, 207->exit, 227->exit, 255->256, 283->291, 296->297
hashstore/py2.py               2      0      0      0   100%
hashstore/server.py          121      4     24      6    93%   100, 102, 148-150, 80->82, 92->94, 99->100, 101->102, 142->150, 145->148
hashstore/session.py          73      3     14      1    95%   35-36, 65, 64->65
hashstore/shash.py            45      0     16      0   100%
hashstore/storage.py          58      1      6      1    97%   23, 20->23
hashstore/udk.py             195      0     52      0   100%
hashstore/utils.py           131      0     48      0   100%
----------------------------------------------------------------------
TOTAL                       1558     25    510     37    97%
In good standing


^CGood bye.
$
```