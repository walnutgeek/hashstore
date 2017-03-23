# hashstore

Tested with 2.7, need to retest with 3.x

```
$ pip install -r requirements.txt
Requirement already satisfied: pytz in /Users/sergeyk/anaconda/lib/python2.7/site-packages (from -r requirements.txt (line 1))
Requirement already satisfied: pyyaml....
$ pip install -r test-requirements.txt
....
$ nosetests
.................
----------------------------------------------------------------------
Ran 17 tests in 9.181s

OK
$ sniffer
Using scent:
.................
----------------------------------------------------------------------
Ran 17 tests in 9.728s

OK
Name                   Stmts   Miss Branch BrMiss  Cover   Missing
------------------------------------------------------------------
hashstore/__init__         0      0      0      0   100%
hashstore/backup          76      3     28      4    93%   22, 108-109
hashstore/content          4      0      0      0   100%
hashstore/db             421     24    192     29    91%   27-46, 259-260, 389, 403, 422, 425
hashstore/hashery        109      4     18      5    93%   74, 76, 99-100
hashstore/localstore     201      6     68      7    95%   88, 97, 110, 119, 200, 208
hashstore/mount          131      2     42      4    97%   212-213
hashstore/session         67      2     10      0    97%   36-37
hashstore/storage         39      1      6      1    96%   20
hashstore/udk            211      0     61      0   100%
hashstore/utils          101      1     50      6    95%   57
------------------------------------------------------------------
TOTAL                   1360     43    475     56    95%
In good standing
$

```