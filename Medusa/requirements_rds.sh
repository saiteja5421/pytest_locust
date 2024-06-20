#!/bin/bash

exit_on_error() {
    exit_code=$1
    if [ $exit_code -ne 0 ]; then
        echo "command failed with exit code ${exit_code}."
        exit $exit_code
    fi
}

# NOTE: Commands are expected to be run in root user (don't need to use sudo)
# Install Oracle Basiz zip file & unzip in an opt directory
echo "Starting pre-requisite dependencies for Oracle DB . . ."
echo "Downloading/validating Oracle Basic Package . . ."
cd $HOME
wget https://download.oracle.com/otn_software/linux/instantclient/219000/instantclient-basic-linux.x64-21.9.0.0.0dbru.zip
mkdir -p /opt/oracle
unzip $HOME/instantclient-basic-linux.x64-21.9.0.0.0dbru.zip
mv $HOME/instantclient_21_9 /opt/oracle
cd /opt/oracle

# Install libaio1 & add path to external variable LD_LIBRARY_PATH
echo "Installing libaio1 & adding path . . ."
apt-get install libaio1 -y
export LD_LIBRARY_PATH=/opt/oracle/instantclient_21_9:$LD_LIBRARY_PATH >> ~/.bashrc
source ~/.bashrc
echo $LD_LIBRARY_PATH
exit_on_error $?