#!/bin/bash

ALIGNAK_SHARE_DIR=${ALIGNAK_SHARE_DIR:-/alignak}
ALIGNAK_USER=${ALIGNAK_USER:-alignak}
ALIGNAK_GROUP=${ALIGNAK_GROUP:-alignak}

chown -R $ALIGNAK_USER:$ALIGNAK_GROUP $ALIGNAK_SHARE_DIR
chmod -R 775 $ALIGNAK_SHARE_DIR

echo $@ > /cmd
su --preserve-environment $ALIGNAK_USER -c "sh /cmd"