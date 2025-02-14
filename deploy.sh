#!/bin/bash


if [ "$#" -ne 1 ]; then
    echo "Usage: $0 {local|server}"
    exit 1
fi

MODE=$1

if [ "$MODE" != "local" ] && [ "$MODE" != "server" ]; then
    echo "Invalid parameter. Use 'local' or 'server'."
    exit 1
fi

PWD=$(pwd)

SERVICE_FILES_DESTINATION="/etc/systemd/system/"

if [ "$MODE" == "local" ]; then
    SERVICE_FILES_SOURCE=(${PWD}/local_client/service_files/)
else
    SERVICE_FILES_SOURCE=(${PWD}/server/service_files/)
fi

for SERVICE_FILE in ${SERVICE_FILES_SOURCE}*.service; do
    
    SERVICE_NAME=$(basename ${SERVICE_FILE})
    DEST_FILE=${SERVICE_FILES_DESTINATION}$(basename ${SERVICE_FILE})

    set -o xtrace
    sudo cp ${SERVICE_FILE} ${SERVICE_FILES_DESTINATION}
    sudo sed -i "s|PWD|${PWD}|g" ${DEST_FILE}
    sudo systemctl enable ${SERVICE_NAME}
    sudo systemctl restart ${SERVICE_NAME}
    set +o xtrace
done