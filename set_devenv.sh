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
devenv=6
targets="6"
for e in $targets
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
    source activate py${devenv}
    coverage combine
    coverage report -m
    shift
fi

for e in $targets
do
    if [ $(cat py${e}.status) != 0 ] ; then
        exit 1
    fi
done
rm dist/hashstore*tar.gz || echo not here - great
python setup.py sdist

if [ "$1" == "deploy_dev" ] ; then
    conda remove -n dev${devenv} --all -y|| echo py${e} not here, it is ok!
    conda create -y -n dev${devenv} python=3.${devenv}
    pip install dist/hashstore*tar.gz
fi






