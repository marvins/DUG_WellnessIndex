#!/usr/bin/env bash

export SKIP_WRITE_COLLECTION_FILE='1'

VERBOSITY=''

for ARG in "$@"; do
    case ${ARG} in
        -d)
            ./purge-all.sh
            ;;
        -v)
            VERBOSITY='-vvv'
            ;;
    esac
done

pushd ..
jupyter-book build ${VERBOSITY} landsat_processing
popd

