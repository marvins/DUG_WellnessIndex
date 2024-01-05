#!/bin/bash

GSD='5.058923138e-06'

SKIP_IF_EXISTS='--skip-if-exists'

INPUT_DIR='/data1/naip_orig'

OUTPUT_DIR='/data1/naip_tileserver/epsg_4326'

CMD="./utilities/lsp-create-geotiff-tileserver.py -s ${INPUT_DIR} -d ${OUTPUT_DIR} -e 4326 -g ${GSD} -n naip ${SKIP_IF_EXISTS} -b"
echo "${CMD}"
${CMD}
