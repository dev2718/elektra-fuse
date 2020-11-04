#!/bin/bash 
docker run --privileged -it elektra-deb:1.0 /bin/bash -c "nohup ~/src/create_keys_and_mount_debug.sh && bash"

