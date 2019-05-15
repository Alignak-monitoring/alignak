#!/bin/bash

chown $ALIGNAK_USER:$ALIGNAK_GROUP $ALIGNAK_SHARE_DIR
chmod -R 775 $ALIGNAK_SHARE_DIR

echo $@ > /cmd
su --preserve-environment $ALIGNAK_USER -c "sh /cmd"