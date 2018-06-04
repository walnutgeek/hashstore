#!/bin/bash
# script assume that you have miniconda3 instaled in path
# it will create python v2 and v3 virtual environments. and install
# dependencies in both of them
#
cd hashstore/bakery/js
npm install
npm run build
cd -
. deactivate
pip install sniffer
for e in 6
do
    conda remove -n py${e} --all -y|| echo py${e} not here, it is ok!
    conda create -y -n py${e} python=3.${e}
    . activate py${e}
    pip install -r requirements.txt
    pip install -r test-requirements.txt
    if [ "$1" == "run_all_tests" ] ; then
      coverage run -p -m nose
      echo $? > py${e}.status
    fi
done
if [ "$1" == "run_all_tests" ] ; then
  source activate py6
  coverage combine
  coverage report -m
  test $(cat py6.status) == 0
fi


