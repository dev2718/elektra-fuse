#!/bin/bash
kdb set user/person/name "Alexander Firbas"
kdb set user/person/alter 21
kdb set user/info "Eine user-information"

kdb meta-set user/person height 180

kdb set user/dir_and_file_at_once "Contents of a non-leaf node"
kdb set user/dir_and_file_at_once/leaf "leaf node"


kdb set system/debuginfo "Systeminformation"

