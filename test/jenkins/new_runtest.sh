#!/usr/bin/env bash
#
# Copyright (C) 2015-2015: Alignak team, see AUTHORS.txt file for contributors
#
# This file is part of Alignak.
#
# Alignak is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Alignak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Alignak.  If not, see <http://www.gnu.org/licenses/>.
#
#
# This file incorporates work covered by the following copyright and
# permission notice:
#  Copyright (C) 2009-2014:
#     Gabes Jean, naparuba@gmail.com
#     Gerhard Lausser, Gerhard.Lausser@consol.de
#
#  This file is part of Shinken.
#
#  Shinken is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Shinken is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with Shinken.  If not, see <http://www.gnu.org/licenses/>.


#############################################################################
#
# the following env variables can be used
# to configure this script behavior:
#
# JENKINS_PYTHON : set the path to the python interpreter you want to use
#                  default to system one (which python)
# SKIP_CORE : if == 1 then will skip the core tests.
# FAILFAST : if == 1 then will failfast
# DEBUG_BASH_SCRIPT : if == 1 then will activate more debug of this script
#
#############################################################################



enable_debug() {
    test "$DEBUG_BASH_SCRIPT" = "1" && set -x
}
disable_debug() {
    set +x
}

cat << END
========================================
+ Launched from: $PWD
+ datetime: $(date)
+ argv[0]: $0
+ argv[*]: $@
* environ: $(env)
========================================
END


enable_debug


MODULELIST=$(readlink -f $2)
COVERAGE=$3
PYLINT=$4
PEP8=$5

# NB:
# if env variable JENKINS_PYTHON is defined then that's the python
# that'll be used for setting up with the virtualenv.

test "$JENKINS_PYTHON" || JENKINS_PYTHON=$(which python)
PY_VERSION=$("$JENKINS_PYTHON" -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
SHORT_PY_VERSION=$("$JENKINS_PYTHON" -c "import sys; print(''.join(map(str, sys.version_info[:2])))")

if test "$6"
then
    REGEXPCMD="$6"
elif [[ "$(echo $1 | tr [A-Z] [a-z])" == "long" ]]; then
    REGEXPCMD=";" # Mod is long, we will take all tests
else
    REGEXPCMD="| grep -v test_long.*\.py" # Mod is normal, we will skip long tests
fi
test "$COVERAGE" == "COVERAGE" || COVERAGE="NOCOVERAGE"
test "$PYLINT" == "PYLINT" || PYLINT="NOPYLINT"
test "$PEP8" == "PEP8" || PYLINT="NOPEP8"

PIP_DOWNLOAD_CACHE=$HOME/.pip/download_cache
COVERAGE_PROCESS_START=$DIR/.coveragerc

# Will be /path/to/alignak/test/jenkins
DIR=$(dirname $(readlink -f "$0"))

ALIGNAKDIR=$(readlink -f "$DIR/../..")
RESULTSDIR="results"


#Check virtualenv, pip and nosetests
function check_req {
    if [[ "$(which virtualenv)" == "" ]];then
        echo "virtualenv needed, please install it"
        exit 2
    fi

    if [[ "$(which pip)" == "" ]];then
        echo "pip needed, please install it"
        exit 2
    fi

}

# Check if the reqs changed
# If the reqs match the previous, copy the previous environment
# Otherwise, create a new one, calc the hash and before going anywhere, copy it under here.
function prepare_environment {
    local virtualenv_args="-p $JENKINS_PYTHON"

    local all_requirements_inputs="requirements.txt ../requirements.txt ../../requirements.txt"
    local all_requirements

    # order is important !
    for f in $all_requirements_inputs
    do
    	all_requirements="$all_requirements $DIR/$f"
    done
    # now look for specific requirements for this python version:
    for dir in . .. ../..
    do
        f="$DIR/$dir/requirements.py${SHORT_PY_VERSION}.txt"
        test -f "$f" && all_requirements="$all_requirements $f"
    done

    HASH=$(cat $all_requirements | md5sum | cut -d' ' -f1)
    if [ -e last_env_hash_${PY_VERSION} -a -f "last_env${PY_VERSION}/bin/activate" ]
    then
        OLDHASH=$(cat last_env_hash_${PY_VERSION})
    else
        OLDHASH=""
    fi

    echo "OLD REQS HASH AND NEW REQS HASH: $OLDHASH vs $HASH"

    # Cache the environment if it hasn't changed.
    if [ "$OLDHASH" != "$HASH" ]; then
        echo "ENVIRONMENT SPECS CHANGED - CREATING A NEW ENVIRONMENT"
        rm -rf "env${PY_VERSION}" || true
        virtualenv --distribute $virtualenv_args env${PY_VERSION}
        . env${PY_VERSION}/bin/activate || {
            echo "Failed to activate the fresh env !"
            rm -rf "env${PY_VERSION}/" || true
            return 3
        }
        pip install --upgrade pip || {
            echo "Failed upgrading pip ! Trying to continue.."
        }
        for req in $all_requirements
        do
            pip install --upgrade -r $req || {
                echo "Failed upgrading $req .."
                return 2
            }
        done
        cd ../../  #
        python setup.py develop
        cd test/jenkins
    else
        echo "ENVIRONMENT SPECS HAVE NOT CHANGED - USING CACHED ENVIRONMENT"
        . env${PY_VERSION}/bin/activate || {
            echo "FAILED to activate the virtualenv !"
            rm -rf "last_env${PY_VERSION}" "env${PY_VERSION}"
            return 2
        }
    fi

    echo "Done Installing"
    echo $HASH > last_env_hash_${PY_VERSION}
}


# Launch the given test with nose test. Nose test has a different behavior than the standard unit test.
function launch_and_assert {
    local res
    SCRIPT=$1
    NAME=$(echo $(basename $SCRIPT) | sed s/\\.py$//g | tr [a-z] [A-Z])
    cat << END
-------------------------------
-> launch_and_assert $SCRIPT
-> pwd=$PWD
-------------------------------
END
    local start=$(date +%s)
    if test $SCRIPT == "test_module_backcompatible.py"; then
      HOOK=""
     else
      HOOK="../alignak/shinken_import_hook.py"
    fi
    if test $COVERAGE == "NOCOVERAGE"; then
      ${PYTHONTOOLS}/nosetests -v -s --with-xunit $HOOK ./$SCRIPT --xunit-file="$RESULTSDIR/xml/$NAME.xml"
      res=$?
    else
      ${PYTHONTOOLS}/nosetests -v -s --with-xunit --with-coverage $HOOK ./$SCRIPT --xunit-file="$RESULTSDIR/xml/$NAME.xml"
      res=$?
      mv .coverage .coverage.$COUNT
      COUNT=$((COUNT + 1))
    fi
    local stop=$(date +%s)
    local duration="$((( $stop-$start ) / 60)):$((( $stop - $start ) % 60))"
    cat << END
-----------------------------------------
-> launch_and_assert $SCRIPT finished with result=$res runtime=$duration
END
    if [ $res != 0 ]
    then
        echo "Error: the test $SCRIPT failed"
        return 2
    else
        echo "test $SCRIPT succeeded, next one"
    fi
    echo -----------------------------------------
    return $res
}


function test_core {
    # REGEXPCMD is ; or grep -v blabla
    # If ;, we are in normal mode
    if test "$SKIP_CORE" = "1"
    then
        echo "SKIP_CORE is set, skipping core tests"
        return 0
    fi
    for test in $(eval "ls test_*.py $REGEXPCMD")
    do
        launch_and_assert $test
        test $? -eq 0 || {
            cat << END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
~ A core test failed : $test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
END
            test "$FAILFAST" = "1" && return 1
        }
    done
}


# Must be in repos/test before launching
function grab_modules {
    local mod_requirements
    cat << END
==============================================================
= Grabbing modules ($(cat $MODULELIST)) ..
==============================================================
END

    rm modules/* || true # first clean out everything of modules subdir
    GIT_URL="https://github.com/shinken-monitoring"
    for module in $(cat $MODULELIST)
    do
        cat << END
===> Grab $module ..
END
        git clone $GIT_URL/$module.git tmp/$module

        # cp alignak_test.py alignak_modules.py tmp/$module/test

        # Symlink of config files to etc
        if [ -d "tmp/$module/test/etc" ]; then
            for conf_file in tmp/$module/test/etc/*; do
               ln -s ../$conf_file etc/
            done
        fi

        # symlink to the test "modules" directory:
        ( cd modules && ln -s ../tmp/$module/module ${module/mod-/} )

        mod_requirements="tmp/$module/test/requirements.txt"
        test -f "${mod_requirements}" && pip install -r "${mod_requirements}"
    done
    # mod-logstore-mongodb and sqlite
    # depends on mock_livestatus from mod-livestatus, so we need to copy it (here in alignak/test)
    # so it's available to them
    cp tmp/mod-livestatus/test/mock_livestatus.py ./

    cat << END
==============================================================
== ALL GRAB DONE
==============================================================
END
}


function test_modules {
    for mod in $(grep -vE "#|^ *$" $MODULELIST)
    do
        if [ -d "tmp/$mod/test/" ]
        then
            cat << END
~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=
~= Launching module $mod tests ..
~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=~=
END
            for ptest in $(eval "ls tmp/$mod/test/test_*.py $REGEXPCMD");do
                launch_and_assert $ptest
                test $? -eq 0 || {
                    echo  "A module ($mod) failed : $ptest"
                    test "$FAILFAST" = "1" && return 1
                }
            done
        else
            echo "No tests found for $mod. Skipping"
        fi
    done
}

function test_core {
    # REGEXPCMD is ; or grep -v blabla
    # If ;, we are in normal mode
    for test in $(eval "ls test_*.py $REGEXPCMD")
    do
        launch_and_assert $test
        test $? -eq 0 || {
            echo "A test failed : $test"
            test "$FAILFAST" = "1" && return 1
        }
    done
}

function main {

    local tests_rc

    export PYTHONPATH=$PYTHONPATH:$ALIGNAKDIR

    enable_debug

    check_req

    cd ${DIR}

    prepare_environment || {
        echo "prepare_environment failed ; exiting.."
        exit 2
    }
    PYTHONBIN="python"
    PYTHONTOOLS=$(dirname $(which $PYTHONBIN))
    echo "PYTHONTOOLS=$PYTHONTOOLS"

    cd .. # We should now be into /path/to/alignak/test/

    if [[ ! -d "$RESULTSDIR" ]]; then
        echo "Creation dir $RESULTSDIR"
        mkdir -p $RESULTSDIR || return 2
    fi

    for dir in "xml" "htmlcov"; do
        if [[ ! -d "$RESULTSDIR/$dir" ]]; then
            mkdir $RESULTSDIR/$dir || return 2
        fi
    done

    # Cleanup leftover files from former runs
    rm -f "$RESULTSDIR/xml/nosetests.xml"
    test $COVERAGE == "COVERAGE" && {
        rm -f "$RESULTSDIR/xml/*"
        rm -f "$RESULTSDIR/htmlcov/*"
        rm -f ".coverage*"
    }
    rm -rf tmp/*
    # Clean previous symlinks
    find etc/ -maxdepth 1 -type l -exec rm {} \;

    # Some module still use the shinken_* file so cp for now
    cp etc/alignak_1r_1h_1s.cfg etc/shinken_1r_1h_1s.cfg
    cp etc/alignak_livestatus_authuser.cfg etc/shinken_livestatus_authuser.cfg
    cp etc/alignak_problem_impact.cfg etc/shinken_problem_impact.cfg

    # Init Count for coverage
    COUNT=1

    do_tests() {
        local is_branch_1=$IS_BRANCH_1
        test_core || return 2
        test "$is_branch_1" || {
            is_branch_1=$(git describe --long)
            if test "1" = "${is_branch_1/\.*/}"
            then
                is_branch_1=1
            else
                is_branch_1=0
            fi
        }
        # on old branch 1.* modules are included in alignak,
        # so no need to bother with them in such case:
        test "$is_branch_1" = "1" && return 0
        grab_modules || return 2
        test_modules
    }
    do_tests
    tests_rc=$?

    # Create the coverage file
    if [[ $COVERAGE == "COVERAGE" ]]; then
        echo "Merging coverage files"
        ${PYTHONTOOLS}/coverage combine
        ${PYTHONTOOLS}/coverage xml --omit=/usr/lib -o "$RESULTSDIR/xml/coverage.xml"
        ${PYTHONTOOLS}/coverage html --omit=/usr/lib -d "$RESULTSDIR/htmlcov"
    fi

    if [[ $PYLINT == "PYLINT" ]]; then
        echo "Pylint Checking"
        cd $ALIGNAKDIR
        ${PYTHONTOOLS}/pylint --rcfile $DIR/pylint.rc alignak > "test/$RESULTSDIR/pylint.txt"
        cd -
    fi

    if [[ $PEP8 == "PEP8" ]]; then
        echo "Pep8 Checking"
        cd $ALIGNAKDIR
        ${PYTHONTOOLS}/pep8 --max-line-length=100 --ignore=E303,E302,E301,E241 --exclude='*.pyc' alignak/* > "test/$RESULTSDIR/pep8.txt"
        cd -
    fi

    if [[ $COVERAGE == "COVERAGE" && $PYLINT == "PYLINT" ]]; then
        # this run's purpose was to collect metrics, so let jenkins think, it's ok
        # Compile coverage info.
        coverage combine
        coverage xml
        return 0
    fi

    return $tests_rc
}


main
