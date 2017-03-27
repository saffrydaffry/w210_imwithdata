#!/usr/bin/env bash

cd $HOME/w210_imwithdata/imwithdata/

zip -r src/imwithdata.zip * -x \*__pycache__\* \*.DS_Store\*

cd $HOME/w210_imwithdata/imwithdata/src/
scp imwithdata.zip es://imwithdata.zip