# hashstore

[![travis-ci.org](https://travis-ci.org/walnutgeek/hashstore.svg?branch=master)](https://travis-ci.org/walnutgeek/hashstore)
[![codecov.io](https://codecov.io/github/walnutgeek/hashstore/coverage.svg?branch=master)](https://codecov.io/github/walnutgeek/hashstore?branch=master)
[![pypi_version](https://img.shields.io/pypi/v/hashstore.svg)](https://pypi.python.org/pypi/hashstore)
[![pypi_support](https://img.shields.io/pypi/pyversions/hashstore.svg)](https://pypi.python.org/pypi/hashstore)


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
