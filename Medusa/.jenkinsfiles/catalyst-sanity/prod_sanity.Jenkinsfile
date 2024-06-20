pipeline {
    agent {
        label 'ATLAS-QA-NODE'
    }

    options {
        timestamps()
        buildDiscarder logRotator(artifactDaysToKeepStr: '',
                artifactNumToKeepStr: '20',
                daysToKeepStr: '',
                numToKeepStr: '20')
        skipDefaultCheckout()
        disableConcurrentBuilds()
    }

    triggers {
        cron 'H 12 * * *'
    }

    parameters {
        string(defaultValue: 'master',
                description: 'Default value is master, type your branch name if you want to run build on specific branch',
                name: 'BRANCH_NAME',
                trim: true)
        string(defaultValue: 'refs/tags/s1-prod-may2024-v1',
                description: 'Default value is tags/s1-prod-may2024-v1, type your tag name if you want to run build using a specific tag',
                name: 'TAG',
                trim: true)
        booleanParam(defaultValue: true,
                description: 'Send emails with the build status (true) or not (false)',
                name: 'SEND_EMAILS')
        string(defaultValue: 'service1-psg-qa@hpe.com',
                description: 'Email address list to specify who should receive email about current build',
                name: 'EMAIL_LIST')
        booleanParam(defaultValue: true,
                description: 'Run test suite with (true) or without (false) using Report Portal flag',
                name: 'ENABLE_REPORT_PORTAL')
    }

    environment {
        CONTAINER_NAME = "atlas-sanity-prod-${env.BUILD_NUMBER}"
        CONFIG_FILE = 'variables_sanity_prod'
        SERVICE_VERSION = 'service1'
    }
    stages {
        stage('Fetch Git Tags') {
            steps {
                script {
                    try {
                        dir("${env.WORKSPACE}")
                        {
                            checkout(
                                [$class: 'GitSCM',
                                branches: [[name: "${params.TAG}"]],
                                extensions: [[$class: 'CloneOption', depth: 1, noTags: false, reference: '', shallow: true, timeout: 30]],
                                userRemoteConfigs: [[credentialsId: 'nmbljenkins', url: 'https://github.hpe.com/nimble/qa_automation.git']]]
                            )
                        }
                    } catch (Exception e) {
                            echo "Error: ${e}"
                    }
                }
                echo "Successfully checked out Git tag: ${params.TAG}"
            }
        }
        stage('Read and Update Passwords') {
            steps
            {
                withCredentials([file(credentialsId: 'SERVICE1_CREDS_SECRET_FILE', variable: 'SANITY_CREDS')]) {
                    script {
                        // reading the secret file
                        def envContent = readFile(env.SANITY_CREDS).trim()
                        def lines = envContent.tokenize('\n')
                        // adding each key and it's value in environment
                        lines.each { line ->
                            def (key, value) = line.tokenize('=')
                            env."$key" = value
                        }
                    }
                    // updating INI file with respective environment variables
                    sh '''
                    python3 $WORKSPACE/Medusa/utils/config_updator.py $WORKSPACE/Medusa/configs/service1/$CONFIG_FILE.ini
                    '''
                }
            }
        }
        stage('Run Sanity Tests') {
            steps {
                withCredentials([string(credentialsId: 'RP_API_KEY_2', variable: 'RP_API_KEY')]) {
                    script {
                        def command = "docker run -w /Medusa/tests/catalyst_gateway_e2e --name ${env.CONTAINER_NAME} --pull always -e RP_API_KEY=$RP_API_KEY -e JENKINS_URL=${env.JENKINS_URL} -e BUILD_URL=${env.BUILD_URL} -e SERVICE_VERSION=${env.SERVICE_VERSION} -e CONFIG_FILE=${env.CONFIG_FILE} -v $WORKSPACE/Medusa:/Medusa hub.docker.hpecorp.net/atlas-qa/e2e-catalyst-gw-mgr pytest -m full -sv -c pytest_sanity_prod.ini --junitxml=logs/junit.xml"
                        if (params.ENABLE_REPORT_PORTAL) {
                            sh "${command} --reportportal /Medusa/tests/catalyst_gateway_e2e/test_sanity/test_sanity_full.py"
                        } else {
                            sh "${command} /Medusa/tests/catalyst_gateway_e2e/test_sanity/test_sanity_full.py"
                        }
                    }
                }
            }
        }
    }
    post {
        always {
            script {
                try {
                    echo "Attempting to stop ${env.CONTAINER_NAME} container:"
                    sh "docker stop ${env.CONTAINER_NAME}"
                    echo "${env.CONTAINER_NAME} stopped."
                } catch (err) {
                    echo "Container ${env.CONTAINER_NAME} is not running."
                }

                try {
                    echo "Attempting to extract test logs from ${env.CONTAINER_NAME} container:"
                    sh "docker cp ${env.CONTAINER_NAME}:/Medusa/tests/catalyst_gateway_e2e/logs/test_run.log ${WORKSPACE}/${env.BUILD_NUMBER}_test_run.log"
                    archiveArtifacts artifacts: "${env.BUILD_NUMBER}_test_run.log", followSymlinks: false
                } catch (err) {
                    echo "Logs are not present in container ${env.CONTAINER_NAME}, unable to export artifact."
                }

                def opeVersion = ""

                try {
                    echo "Attempting to extract Data Orchestrator version from ${env.CONTAINER_NAME} container:"
                    sh "docker cp ${env.CONTAINER_NAME}:/Medusa/tests/catalyst_gateway_e2e/OPE_version.txt ${WORKSPACE}/${env.BUILD_NUMBER}_OPE_version.txt"
                    opeVersion = readFile "${WORKSPACE}/${env.BUILD_NUMBER}_OPE_version.txt"
                } catch (err) {
                    echo "File with OPE version is not present in ${env.CONTAINER_NAME}, unable to export value."
                }

                def testResults = ""

                try {
                    echo "Attempting to extract junit xml report from ${env.CONTAINER_NAME} container:"
                    sh "docker cp ${env.CONTAINER_NAME}:/Medusa/tests/catalyst_gateway_e2e/logs/junit.xml ${WORKSPACE}/${env.BUILD_NUMBER}_junit.xml"
                    def summary = junit allowEmptyResults: true, healthScaleFactor: 0.0, skipPublishingChecks: true, testResults: "${env.BUILD_NUMBER}_junit.xml"
                    testResults = "\n\nTest Summary\n---\nTotal: ${summary.totalCount}\nPassed: ${summary.passCount}\nFailures: ${summary.failCount}\nSkipped: ${summary.skipCount}"
                } catch  (err) {
                    echo "XML test report is not present in container ${env.CONTAINER_NAME}, unable to extract results."
                }

                try {
                    echo "Attempting to remove ${env.CONTAINER_NAME} container:"
                    sh "docker rm ${env.CONTAINER_NAME}"
                    echo "${env.CONTAINER_NAME} removed."
                } catch (err) {
                    echo "Container ${env.CONTAINER_NAME} does not exist."
                }

                try {
                    echo "Attempting to remove dangling images using 'docker image prune -f'"
                    sh "docker image prune -f"
                    echo "Removed dangling images"
                } catch (err) {
                    echo "Failed to remove dangling images from the system"
                }

                cleanWs()

                if (params.SEND_EMAILS) {
                    def emailSubject = "${env.JOB_NAME} ${env.BUILD_NUMBER} - Status ${currentBuild.result}"
                    def buildDesc = "http://reportportal.lab.nimblestorage.com:8080/"
                    // Note: pyTest API run updates build description to have ReportPortal launch URL.
                    // If description exists, using it for notification text.
                    if (currentBuild.description) {
                        buildDesc = "${currentBuild.description}"
                    }
                    def emailBodyTemplate = """
                    Build ran on branch: ${params.BRANCH_NAME}
                    Are logs on Report Portal?: ${params.ENABLE_REPORT_PORTAL}
                    OPE version: ${opeVersion}

                    Link to build: ${env.BUILD_URL}
                    Link to console: ${env.BUILD_URL}console
                    Link to artifact: ${env.BUILD_URL}artifact

                    Link to ReportPortal: ${buildDesc} (testuser1/testuser1)
                    """.stripIndent()

                    emailBodyTemplate += testResults

                    mail body: emailBodyTemplate, subject: emailSubject, to: params.EMAIL_LIST
                }

                color = ""
                if(currentBuild.currentResult == "SUCCESS") {
                    color = "good"
                }
                else if(currentBuild.currentResult == "FAILURE") {
                    color = "danger"
                }
                else {
                     color = "warning"
                }

                // Send notification to slack
                slackSend (message: "${env.JOB_NAME} ${env.BUILD_NUMBER} - ${currentBuild.result}\n${env.BUILD_URL}console\n${testResults}\nOPE version: ${opeVersion}",
                           channel: 'jenkins_notifications',
                           teamDomain: 'hpe-internal',
                           tokenCredentialId: 'slack-notificaitons',
                           color: "${color}",
                           iconEmoji: ':hpe-bot')

            }
        }
    }
}
