#!/bin/sh
PYTHON="python2.7"
PYTHONPATH="src:src/dep"

NAME="demo_1.py"

PYTHONPATH=${PYTHONPATH} ${PYTHON} ${NAME} $@
