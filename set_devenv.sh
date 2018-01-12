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
done
if [ "$1" == "run_all_test" ] ; then
    . deactivate
    python scent.py
fi

