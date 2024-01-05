#!/bin/bash

#SKIP_IF_EXISTS="--skip-if-exists"

EPSG="32613"

GSD='0.5'

INPUT_DIR='/data1/naip_orig'

OUTPUT_DIR='/data1/naip_tileserver/epsg_32613'

CMD="./utilities/lsp-create-geotiff-tileserver.py -s ${INPUT_DIR} -d ${OUTPUT_DIR} -e ${EPSG} -g ${GSD} -n naip ${SKIP_IF_EXISTS} -b"
echo "${CMD}"
${CMD}
