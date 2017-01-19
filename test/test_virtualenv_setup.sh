#!/bin/bash

set -e

STOP_ON_FAILURE=0
SKIP_PERMISSION=0
SUFFIX_TESTFILE=""

# Big travis specific part
if [[ "$TRAVIS" == "true" ]]; then
    sudo apt-get install -y python-virtualenv mlocate
    sudo updatedb # Debugging purpose
    SKIP_PERMISSION=1  # Umask on travis is different, causing some file to have a bad chmod
    SUFFIX_TESTFILE="_travis" # Some file are also missing
    unset PYTHONWARNINGS  # We don't need them anymore

    # Clean previous install
    sudo ./test/uninstall_alignak.sh

    # Remove Travis "virtualenv"
    unset VIRTUAL_ENV
    #PATH=${PATH#*:}
    rm -rf alignak.egg-info
fi

if [[ "$(which virtualenv)" == "" ]]; then
    echo "Please install virtualenv. Needed to test alignak install"
    exit 1
fi

if [[ "$(which locate)" == "" ]]; then
    echo "Please install (mlocate). Needed to purge alignak"
    exit 1
fi

function get_python_version_formatted(){
    python --version 2>&1 | awk -F "[ .]" '{print "python"$2"."$3}'
}

function get_alignak_version_formatted(){
    awk -F "[ \"]" '/VERSION/ {print $4}' alignak/version.py
}

# Not used for now
function get_distro(){
    DISTRO=$(lsb_release -i | cut -f 2 | tr [A-Z] [a-z])

    if [[ $? -ne 0 ]]; then
       DISTRO=$(head -1 /etc/issue | cut -f 1 -d " " | tr [A-Z] [a-z])
    fi

    echo $DISTRO
}

# Debugging function to find where the wanted path could be
function get_first_existing_path(){
    path="$1/.."
    while true; do
        true_path=$(readlink -m $path)
        if [[ -e $true_path ]]; then
            echo $true_path
            ls -l  $true_path
            return
        else
            path="$path/.."
        fi
    done
}

# Yeah sometimes you know, shit happens with umask
# So yeah lets try to guess expected rights then
# Only for files, not directories
# Not used for now
function hack_umask(){
    cur_umask=$(umask)
    exp_umask="0022"
    file=$1
    cur_chmod=$2
    if [[ "$exp_umask" != "$cur_umask" && -f $file ]]; then
        diff_mask=$(xor_octal $exp_umask $cur_umask)
        cur_chmod=$(xor_octal $cur_chmod $diff_mask)
    fi
    echo $cur_chmod
}

function ignore_sticky_or_setid(){
    if [[ ${#1} -gt 3 ]]; then
        echo ${1:${#1}-3:3}
    else
        echo $1
    fi
}

function xor_octal(){
    exp=$1
    cur=$2

    # The 1 param can be a octal on 3 digit only
    # Fill with 0
    if [[ "${#exp}" != "${#cur}" ]]; then
        exp=0$exp
    fi

    out=""
    for i in $(seq ${#exp}); do
        out=${out}$(( ${exp:$i-1:1} ^ ${cur:$i-1:1} ))
    done

    echo $out
}

function setup_virtualenv(){
    rm -rf $HOME/pyenv_$1 && virtualenv ~/pyenv_$1 && source ~/pyenv_$1/bin/activate
    export VIRTUALENVPATH="$HOME/pyenv_$1"
}

function test_setup(){
error_found=0
for raw_file in $(awk '{print $2}' $1); do

    file=$(echo "$raw_file" | sed  -e "s:VIRTUALENVPATH:$VIRTUALENVPATH:g" \
                                   -e "s:PYTHONVERSION:$PYTHONVERSION:g" \
                                   -e "s:ALIGNAKVERSION:$ALIGNAKVERSION:g"\
                                   -e "s:SHORTPYVERSION:$SHORTPYVERSION:g")
    exp_chmod=$(grep "$raw_file$" $1| cut -d " " -f 1 )
    if [[ "$exp_chmod" == "" ]]; then
        echo "Can't find file in conf after sed - RAWFILE:$raw_file, FILE:$file"
    fi
    echo "Found the file: $file"

    cur_chmod=$(stat -c "%a" $file 2>> /tmp/stat.failure)
    if [[ $? -ne 0 ]];then
        tail -1 /tmp/stat.failure

        if [[ $error_found -eq 0 ]]; then
            get_first_existing_path $file
            sudo updatedb
            locate -i alignak | grep -v "monitoring"
        fi

        if [[ $STOP_ON_FAILURE -eq 1 ]];then
            return 1
        else
            error_found=1
            continue
        fi
    fi

    if [[ $SKIP_PERMISSION -eq 0 ]]; then
        # Sometimes there are sticky bit or setuid or setgid on dirs
        # Let just ignore this.
        cur_chmod=$(ignore_sticky_or_setid $cur_chmod)

        if [[ "$exp_chmod" != "$cur_chmod" ]]; then
            echo "Right error on file $file - expected: $exp_chmod, found: $cur_chmod"
            if [[ $STOP_ON_FAILURE -eq 1 ]]; then
                return 1
            else
                error_found=1
            fi
        fi
    fi
done 

return $error_found
}

#TODO
# check owner also, maybe we will need specific user tests

error_found_global=0
ALIGNAKVERSION=$(get_alignak_version_formatted)
SUDO="sudo"

for pyenv in "root" "virtualenv"; do
    for install_type in "install" "develop"; do
        if [[ "$pyenv" == "virtualenv" ]]; then
            setup_virtualenv $install_type
            SUDO=""
        fi

        PYTHONVERSION=$(get_python_version_formatted)
        SHORTPYVERSION=$(echo $PYTHONVERSION | sed "s:thon::g")

        if [[ ! -e ./test/virtualenv_install_files/${install_type}_${pyenv}${SUFFIX_TESTFILE} ]]; then
            echo "Test not supported for python setup.py $install_type $pyenv with suffix : ${SUFFIX_TESTFILE}"
            continue
        fi

        echo "============================================"
        echo "TEST SETUP for ${install_type} ${pyenv}"
        echo "============================================"

        echo "Installing alignak_setup..."
        $SUDO pip install alignak_setup 2>&1 1>/dev/null
        echo "Installing test requirements..."
        $SUDO pip install -r test/requirements.txt 2>&1 1>/dev/null
        echo "Installing alignak..."
        $SUDO python setup.py $install_type 2>&1 >/dev/null

        echo "Running test (${install_type}_${pyenv}${SUFFIX_TESTFILE})..."
        test_setup "test/virtualenv_install_files/${install_type}_${pyenv}${SUFFIX_TESTFILE}"

        if [[ $? -ne 0 ]];then
            echo "**********"
            echo "***** An error occurred during ${install_type} ${pyenv} *****"
            echo "**********"
            if [[ $STOP_ON_FAILURE -eq 1 ]];then
                exit 1
            else
                error_found_global=1
            fi
        fi

        $SUDO pip uninstall -y alignak 2>&1 1>/dev/null
        $SUDO ./test/uninstall_alignak.sh
        $SUDO git clean -fdx 2>&1 1>/dev/null
        $SUDO git reset --hard 2>&1 1>/dev/null

        if [[ "$pyenv" == "virtualenv" ]]; then
            deactivate
            unset VIRTUALENVPATH
        fi

        echo "==============================================="
        echo "TEST SETUP for ${install_type} ${pyenv} DONE"
        echo "==============================================="

    done
done

exit $error_found_global
