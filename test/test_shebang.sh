#!/bin/sh

testEquality() {
    files=`find ./ -type f -name "*.py"`
    for i in $files;do
        h=`head -n 1 $i`
        assertEquals "$i" "#!/usr/bin/env python" "$h"
    done
}

. test/shunit2-2.0.3/src/shell/shunit2
