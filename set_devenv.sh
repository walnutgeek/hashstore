#!/bin/bash
# script assume that you have miniconda3 instaled in path
# it will create python v2 and v3 virtual environments. and install
# dependencies in both of them
#
. deactivate
pip install sniffer
for e in 2 3
do
    conda remove -n py${e} --all -y|| echo py${e} not here, it is ok!
    conda create -y -n py${e} python=${e} python
    . activate py${e}
    pip install -r requirements.txt
    pip install -r test-requirements.txt
    npm install
    npm run build
    cd hashstore/bakery/js
    npm install
    npm run build
    cd -
    if [ "$1" == "run_all_tests" ] ; then
      coverage run -p -m nose
      echo $? > $e.status
    fi
done
if [ "$1" == "run_all_tests" ] ; then
  source activate py2
  coverage combine
  coverage report -m
fi
test $(cat py2.status) == 0 && test $(cat py3.status) == 0


