#!/bin/bash

set -e 

#  Get the path
if [ "$#" -ne "1" ]; 
    then echo "illegal number of parameters"
    exit 1
fi
BASE_DIR="${1}"

#  Get the collection id
CID="`basename ${BASE_DIR}`"

pushd ${BASE_DIR}

#  Find the 3 bands we need for processing
R_BAND="`find . -name \"${CID}_B4\.*\" | grep -v '.aux.xml'`"
if [ ! -f "${R_BAND}" ]; then
    echo "error: No red band located. Expected: ${R_BAND}"
    exit 1
fi

G_BAND="`find . -name \"${CID}_B3\.*\" | grep -v '.aux.xml'`"
if [ ! -f "${G_BAND}" ]; then
    echo "error: No green band located. Expected: ${G_BAND}"
    exit 1
fi

B_BAND="`find . -name \"${CID}_B2\.*\" | grep -v '.aux.xml'`"
if [ ! -f "${B_BAND}" ]; then
    echo "error: No blue band located. Expected: ${B_BAND}"
    exit 1
fi

OUTPATH="${CID}_color.TIF"

#  Run GDAL Merge
CMD="gdal_merge.py -separate -n 0 -a_nodata 0 -ot UInt16 -of GTiff -o ${OUTPATH} ${R_BAND} ${G_BAND} ${B_BAND}"
echo "${CMD}"
${CMD}
