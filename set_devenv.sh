#!/bin/bash -x
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
targets="6 7"
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
    coverage html
    shift

    for e in $targets
    do
        if [ $(cat py${e}.status) != 0 ] ; then
            echo FAILED
            exit 1
        fi
    done
fi

if [ "$1" == "deploy_dev" ] ; then
    source activate py${devenv}
    rm dist/hashstore*tar.gz || echo not here - great
    python setup.py sdist >& sdist.log
    conda remove -n dev${devenv} --all -y|| echo py${e} not here, it is ok!
    conda create -y -n dev${devenv} python=3.${devenv}
    source activate dev${devenv}
    pip install dist/hashstore*tar.gz
    if [ -e test-out/store ] ; then
        hsd --store_dir test-out/store stop
        sleep 2
    fi
    rm -rf test-out/store
    cp -a test-out/py6/hashstore.bakery.tests.server_tests/store test-out/
    hsd --store_dir test-out/store initdb --port 338${devenv}
    BUILD_ID=doNotKillMe hsd --store_dir test-out/stort start >& start.log &
fi






