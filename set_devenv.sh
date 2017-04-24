#!/bin/bash
# script assume that you have miniconda3 instaled in path
# it will create python v2 and v3 virtual environments. and install
# dependencies in both of them
#
conda create -y -n py3 python=3 python
conda create -y -n py2 python=2 python
. activate py2
pip install -r requirements.txt
pip install -r test-requirements.txt
. activate py3
pip install -r requirements.txt
pip install -r test-requirements.txt
