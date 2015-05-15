#!/bin/bash
NAME=$1
echo "Creating a test from dummy with 1 router, one host and 1 service to " $1

cp test_dummy.py test_$1.py
cp etc/alignak_1r_1h_1s.cfg etc/alignak_$1.cfg
cp -r etc/1r_1h_1s etc/$1
sed "s/1r_1h_1s/$1/" etc/alignak_$1.cfg -i
sed "s/1r_1h_1s/$1/" test_$1.py -i

echo "Test creation succeed"
