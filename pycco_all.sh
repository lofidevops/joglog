#!/bin/sh

filelist=$( find . -name '*.py' | grep -v ".tox" )
pycco -ip $filelist
