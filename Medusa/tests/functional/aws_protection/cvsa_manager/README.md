# CVSA Manager Functional Tests

## How to set up local environment:

To run tests on local machine cVSA Manager source code is required to proceed. 
You can get it using git: https://github.hpe.com/nimble-dcs/atlantia-cvsa-manager

## Prerequisite:
Run `docker-compose up -d` command to spin up all dependencies for cVSA Manager application.

## Setup application:

Please set up all the environment variables to every terminal that is starting cVSA application.

* **General**

```shell
export http_proxy=http://hpeproxy.its.hpecorp.net:443/
export https_proxy=http://hpeproxy.its.hpecorp.net:443/

make build
```

* **Kafka**

```shell
export KAFKA_BROKERS=localhost:9092
```

* **Cadence**

```shell
export CADENCE_ADDR=localhost:7933
```

* **Database**

```shell
export POSTGRESQL_URL='postgres://postgres:example@localhost:5432/atlantia-cvsa-manager?sslmode=disable'

make setup_db
```

* **Vault**

```shell
export VAULT_ADDR=http://127.0.0.1:8200

source scripts/vault_setup.sh
```

The output of the script provides token to Vault, it is required by tests and application to be set.

* **Application related settings**

```shell
export TEST_REGION=eu-central-1
```

* **Localstack** (only if you want to run tests on Localstack)

```shell
export LOCALSTACK_ADDR=http://localhost
export LOCALSTACK_URL=http://localhost:4566
export AWS_AMI_PREFIX=suse
export AWS_SECRET_ACCESS_KEY=test
export AWS_ACCESS_KEY_ID=test
export ALLOWED_AWS_REGIONS=eu-central-1
export TEST_REGION=eu-central-1

./dist/functional-tests setup
```
* **AWS** (only if you want to run tests on AWS)

```shell
export AWS_SECRET_ACCESS_KEY=<YOUR CREDENTIALS FOR AWS HERE>
export AWS_ACCESS_KEY_ID=<YOUR CREDENTIALS FOR AWS HERE>
export ALLOWED_AWS_REGIONS=eu-central-1
# flag below required only when 985870503702 dev AWS account is used 
export LOCAL_ENV=true 

./dist/functional-tests setup
```

* **Start application**

Consumer:
```shell
./dist/atlantia-cvsa-manager consumer
```

Cadence Worker:
```shell
./dist/atlantia-cvsa-manager cadence-worker
```

## How to execute test suite:

You need to have environment variables in the terminal on top of what you're executing test cases.

Environment variables that are required:
```shell
export http_proxy=http://hpeproxy.its.hpecorp.net:443/
export https_proxy=http://hpeproxy.its.hpecorp.net:443/

export VAULT_TOKEN=<TOKEN TO VAULT THAT WAS GENERATED BY SCRIPT>
export VAULT_ADDR=http://localhost:8200
```

For Localstack it is required to add one more environment variable:
```shell
export LOCALSTACK_URL=http://localhost:4566
```

* **AWS**

```shell
pytest -sv tests/cvsa_manager --rootdir . -m aws
```
* **Localstack**

```shell
pytest -sv tests/cvsa_manager --rootdir . -m localstack
```

## TL;DR

**Environment Variables for Localstack**
```shell
export http_proxy=http://hpeproxy.its.hpecorp.net:443/
export https_proxy=http://hpeproxy.its.hpecorp.net:443/
export POSTGRESQL_URL='postgres://postgres:example@localhost:5432/atlantia-cvsa-manager?sslmode=disable'
export LOCALSTACK_ADDR=http://localhost
export LOCALSTACK_URL=http://localhost:4566
export ALLOWED_AWS_REGIONS=eu-central-1,eu-north-1
export KAFKA_BROKERS=localhost:9092
export CADENCE_ADDR=localhost:7933
export AWS_SECRET_ACCESS_KEY=test
export AWS_ACCESS_KEY_ID=test
export TEST_REGIONS=eu-central-1,eu-north-1
export VAULT_ADDR=http://127.0.0.1:8200
export AWS_AMI_PREFIX=suse
export VAULT_TOKEN=<VAULT TOKEN>
```

**Environment Variables for AWS**
```shell
export http_proxy=http://hpeproxy.its.hpecorp.net:443/
export https_proxy=http://hpeproxy.its.hpecorp.net:443/
export POSTGRESQL_URL='postgres://postgres:example@localhost:5432/atlantia-cvsa-manager?sslmode=disable'
export ALLOWED_AWS_REGIONS=eu-central-1,eu-north-1
export KAFKA_BROKERS=localhost:9092
export CADENCE_ADDR=localhost:7933
export TEST_REGIONS=eu-central-1,eu-north-1
export VAULT_ADDR=http://127.0.0.1:8200
export AWS_TAGS=managed-by:atlantia-cvsa-manager,hpe-project:Atlantia,hpe-owner:<YOUR NAME>
export VAULT_TOKEN=<VAULT TOKEN>
export AWS_SECRET_ACCESS_KEY=<AWS SECRET>
export AWS_ACCESS_KEY_ID=<AWS SECRET>
```

## Local Setup
Required Python version: 3.10

**Python environment setup**
```shell
cd Medusa
virtualenv -p python3 env
source ./env/bin/activate
pip install -r requirements_backup_and_recovery.txt
```

**Environment Variables for LocalStack**
```shell
export no_proxy=localhost
export POSTGRESQL_URL='postgres://postgres:example@localhost:5432/atlantia-cvsa-manager?sslmode=disable'
export LOCALSTACK_ADDR=http://localhost
export LOCALSTACK_URL=http://localhost:4566
export ALLOWED_AWS_REGIONS=eu-central-1,eu-north-1
export KAFKA_BROKERS=localhost:9092
export CADENCE_ADDR=localhost:7933
export AWS_SECRET_ACCESS_KEY=test
export AWS_ACCESS_KEY_ID=test
export TEST_REGIONS=eu-central-1,eu-north-1
export AWS_AMI_PREFIX=suse
export VAULT_TOKEN=<VAULT  TOKEN>
export VAULT_ADDR=http://127.0.0.1:8200
```
**Run all tests**
```shell
pytest -sv tests/functional/aws_protection/cvsa_manager --rootdir . -m cvsa_localstack
```

**Run single test**
```shell
pytest -sv tests/functional/aws_protection/cvsa_manager --rootdir . -k test_tc27
```

**Troubleshooting**
1. MacBook M1 issue with installing `pyssql`
```shell
brew install freetds openssl
export LDFLAGS="-L/opt/homebrew/opt/freetds/lib -L/opt/homebrew/opt/openssl@3/lib"
export CFLAGS="-I/opt/homebrew/opt/freetds/include"
export CPPFLAGS="-I/opt/homebrew/opt/openssl@3/include"
pip install -r requirements_backup_and_recovery.txt
```