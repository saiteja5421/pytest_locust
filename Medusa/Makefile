# Commands
PYTHON = python -m
PYTEST = pytest -sv
EXECUTE_PERMISSION = chmod +x
DOCKER_RUN = docker run --rm -e
NO_PROXY = no_proxy=$no_proxy,127.0.0.1,localhost,.nimblestorage.com,10.0.0.0/8,192.0.0.0/8,172.0.0.0/8,10.226.67.255

# Test/Lint files
E2E_TEST_SUITE = e2e-tests/test_scripts/
SANITY_TEST_SUITE = e2e-tests/test_sanity/
LINT_FILE = lint.sh

# Docker Test Image
# Note - Make sure to have a pre-built image to use for testing
DOCKER_TEST_IMG = e2e-catalyst-gw-mgr:v1.0


# .PHONY defines parts of the makefile that are not dependant on any specific file
# This is most often used to store functions
.PHONY = help lint e2e-tests clean

# This target is executed whenever we just type `make`
.DEFAULT_GOAL = help

# The @ makes sure that the command itself isn't echoed in the terminal
help:
	@echo ""
	@echo "Usage: make [TARGET]"
	@echo 'Targets:'
	@echo "  lint"
	@echo "  e2e-tests"
	@echo "  docker-test"
	@echo "  sanity-tests"
	@echo "  docker-sanity-test"
	@echo ""

lint:
	@${EXECUTE_PERMISSION} ${LINT_FILE}
	@./${LINT_FILE}

.PHONY: e2e-tests
e2e-tests:
	${PYTEST} ${E2E_TEST_SUITE}

docker-e2e-test:
	${DOCKER_RUN} ${NO_PROXY} ${DOCKER_TEST_IMG} ${PYTHON} ${PYTEST} ${E2E_TEST_SUITE}

sanity-tests:
	${PYTEST} ${SANITY_TEST_SUITE}

docker-sanity-test:
	${DOCKER_RUN} ${NO_PROXY} ${DOCKER_TEST_IMG} ${PYTHON} ${PYTEST} ${SANITY_TEST_SUITE}


# In this context, the *.project pattern means "anything that has the .project extension"
# clean:
# 	rm -r *.project