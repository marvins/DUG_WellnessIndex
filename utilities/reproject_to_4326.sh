#!/bin/bash
#

OVERWRITE='0'

for ARG in "$@"; do

    case ${ARG} in

        -o)
            OVERWRITE='1'
            ;;
    esac
done

INPUT_DIR='/data1/naip_orig'

OUTPUT_DIR='/data1/naip_tileserver/epsg_4326'


TIF_LIST="`find ${INPUT_DIR} -name '*.tif'`"

DEST_EPSG='EPSG:4326'

INTERP='bilinear'

for TIF in ${TIF_LIST}; do

    #  Get the source path
    SRC_PATH="${TIF}"

    DST_PATH="${OUTPUT_DIR}/gtiff/`basename ${TIF}`"

    if [[ ! -f "${DST_PATH}" || "${OVERWRITE}" = '1' ]]; then

        echo "converting ${SRC_PATH} to ${DST_PATH}"

        CMD="gdalwarp -overwrite -t_srs ${DEST_EPSG} -r ${INTERP} -of GTiff ${SRC_PATH} ${DST_PATH}"
        echo "${CMD}"
        ${CMD}
    else
        echo "Skipping conversion of ${SRC_PATH}. ${DST_PATH} already exists."
    fi

done

