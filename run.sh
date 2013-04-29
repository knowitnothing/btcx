#!/bin/sh
PYTHON="python2.7"
PYTHONPATH="dep"

NAME="demo_1.py"

PYTHONPATH=${PYTHONPATH} ${PYTHON} ${NAME} $@
