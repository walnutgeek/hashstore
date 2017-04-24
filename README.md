# hashstore

Content Addressable Storage written in python

See more: https://en.wikipedia.org/wiki/Content-addressable_storage

## Usage

TBD

### Use case: Backup

TBD

## Developer Environment

You have to have miniconda3 instaled in path. set_devenv.sh will create 'py2' and
'py3' virtual environments with dependencies. sniffer will run tests on both
continuously.

```
$ ./set_devenv.sh
....
$ sniffer
Using scent:
......................
----------------------------------------------------------------------
Ran 22 tests in 7.597s

OK
......................
----------------------------------------------------------------------
Ran 22 tests in 8.420s

OK
{'py2': True, 'py3': True}
Name                        Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------
hashstore/__init__.py           0      0      0      0   100%
hashstore/backup.py            66      3     20      3    93%   33, 91-92, 32->33, 63->65, 74->exit
hashstore/db.py               426      6    194     16    96%   396, 410, 429, 432, 545-546, 96->exit, 97->exit, 98->97, 201->208, 227->224, 348->343, 391->397, 395->396, 409->410, 423->414, 428->429, 431->432, 571->580, 608->610, 611->613, 615->618
hashstore/local_store.py      226      0     66      0   100%
hashstore/mount.py            164     10     56      6    91%   201-209, 245, 279-280, 35->41, 50->48, 113->115, 195->197, 231->239, 244->245
hashstore/py2.py                2      0      0      0   100%
hashstore/remote_store.py     101      9     18      5    87%   68-72, 79, 81, 107-109, 65->68, 78->79, 80->81, 101->109, 104->107
hashstore/session.py           74      3     14      1    95%   36-37, 66, 65->66
hashstore/shash.py             27      0      6      0   100%
hashstore/storage.py           39      1      6      1    96%   20, 17->20
hashstore/udk.py              195      0     52      0   100%
hashstore/utils.py            127      0     46      0   100%
-----------------------------------------------------------------------
TOTAL                        1447     32    478     32    96%
In good standing

^C
$
```