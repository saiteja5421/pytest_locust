#!/bin/bash -x

cd $WORKSPACE/Medusa/

# old proxy: http://web-proxy.corp.hpecorp.net:8080
export http_proxy="http://hpeproxy.its.hpecorp.net:443"
export https_proxy="http://hpeproxy.its.hpecorp.net:443"
export HTTP_PROXY="http://hpeproxy.its.hpecorp.net:443"
export HTTPS_PROXY="http://hpeproxy.its.hpecorp.net:443"
export no_proxy="localhost,127.0.0.1,*.nimblestorage.com"

python3 -m venv venv && . venv/bin/activate && pip3 install -r requirements_backup_and_recovery.txt && pip3 install -r requirements_rds.txt

export LD_LIBRARY_PATH="/opt/oracle/instantclient_21_9"

pytest --collect-only tests/functional/
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "ERROR while running 'pytest --collect-only tests/functional/'"
    exit $retVal
fi

export SERVICE_VERSION=service1
pytest --collect-only tests/catalyst_gateway_e2e
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "ERROR while running 'SERVICE_VERSION=service1 pytest --collect-only tests/catalyst_gateway_e2e'"
    exit $retVal
fi

export SERVICE_VERSION=service2
pytest --collect-only tests/e2e/aws_protection
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "ERROR while running 'pytest --collect-only tests/e2e/aws_protection'"
    exit $retVal
fi

pytest --collect-only tests/e2e/azure_protection
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "ERROR while running 'pytest --collect-only tests/e2e/azure_protection'"
    exit $retVal
fi
