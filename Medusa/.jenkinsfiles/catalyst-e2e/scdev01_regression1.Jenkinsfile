pipeline {
    agent {
        label 'ATLAS-QA-NODE'
    }

    options {
        timestamps()
        buildDiscarder logRotator(artifactDaysToKeepStr: '',
                artifactNumToKeepStr: '60',
                daysToKeepStr: '',
                numToKeepStr: '60')
        skipDefaultCheckout()
    }

    triggers {
        cron 'H 15 * * *'
    }

    parameters {
        string(defaultValue: 'master',
                description: 'Default value is master, type your branch name if you want to run build on specific branch',
                name: 'BRANCH_NAME',
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
        CONTAINER_NAME = "atlas-e2e-pipeline-${env.BUILD_NUMBER}-${Math.abs(new Random().nextInt(101))}"
        CONFIG_FILE = 'variables_reg1'
        SERVICE_VERSION = 'service1'
    }

    stages {
        stage('Checkout Repository') {
            steps {
                checkout(
                    [$class: 'GitSCM',
                    branches: [[name: "${params.BRANCH_NAME}"]],
                    extensions: [[$class: 'CloneOption', depth: 1, noTags: false, reference: '', shallow: true, timeout: 30]],
                    userRemoteConfigs: [[credentialsId: 'nmbljenkins', url: 'https://github.hpe.com/nimble/qa_automation.git']]]
                )
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
        stage('Copy public certificate for minio') 
        {
            steps
            {
                withCredentials([file(credentialsId: 'SERVICE1_MINIO_CERTS', variable: 'MINIO_PUBLIC_CERTS')]) {
                sh '''
                cp $MINIO_PUBLIC_CERTS $WORKSPACE/Medusa/minio_certs.crt
                '''
                }
            }
        }
        stage('Run Atlas E2E API Tests') {
            steps {
                withCredentials([string(credentialsId: 'RP_API_KEY_2', variable: 'RP_API_KEY')]){
                    script {
                        echo "Executing a test suite from the Docker Image"
                        def command = "docker run -w /Medusa/tests/catalyst_gateway_e2e --name ${env.CONTAINER_NAME}  --pull always -e RP_API_KEY=$RP_API_KEY -e JENKINS_URL=${env.JENKINS_URL} -e BUILD_URL=${env.BUILD_URL} -e SERVICE_VERSION=${env.SERVICE_VERSION} -e CONFIG_FILE=${env.CONFIG_FILE} -v $WORKSPACE/Medusa:/Medusa hub.docker.hpecorp.net/atlas-qa/e2e-catalyst-gw-mgr python -m pytest -sv -c pytest_reg1.ini --junitxml=logs/junit.xml"
                        if (params.ENABLE_REPORT_PORTAL) {
                            sh "${command} --reportportal /Medusa/tests/catalyst_gateway_e2e/test_scripts/regression1"
                        } else {
                            sh "${command} /Medusa/tests/catalyst_gateway_e2e/test_scripts/regression1"
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

                def testResults = ""

                try {
                    echo "Attempting to extract junit xml report from ${env.CONTAINER_NAME} container:"
                    sh "docker cp ${env.CONTAINER_NAME}:/Medusa/tests/catalyst_gateway_e2e/logs/junit.xml ${WORKSPACE}/${env.BUILD_NUMBER}_junit.xml"
                    def summary = junit allowEmptyResults: true, healthScaleFactor: 0.0, skipPublishingChecks: true, testResults: "${env.BUILD_NUMBER}_junit.xml"
                    testResults = "\n\nTest Summary\n---\nTotal: ${summary.totalCount}\nPassed: ${summary.passCount}\nFailures: ${summary.failCount}\nSkipped: ${summary.skipCount}"
                } catch  (err) {
                    echo "XML test report is not present in container ${env.CONTAINER_NAME}, unable to extract results."
                }

                def opeVersion = ""

                try {
                    echo "Attempting to extract Data Orchestrator version from ${env.CONTAINER_NAME} container:"
                    sh "docker cp ${env.CONTAINER_NAME}:/Medusa/tests/catalyst_gateway_e2e/OPE_version.txt ${WORKSPACE}/${env.BUILD_NUMBER}_OPE_version.txt"
                    opeVersion = readFile "${WORKSPACE}/${env.BUILD_NUMBER}_OPE_version.txt"
                } catch (err) {
                    echo "File with OPE version is not present in ${env.CONTAINER_NAME}, unable to export value."
                }

                try {
                    echo "Attempting to remove ${env.CONTAINER_NAME} container:"
                    sh "docker rm ${env.CONTAINER_NAME}"
                    echo "${env.CONTAINER_NAME} removed."
                } catch (err) {
                    echo "Container ${env.CONTAINER_NAME} does not exist."
                }

                try {
                    echo 'Attempting to delete hub.docker.hpecorp.net/atlas-qa/e2e-catalyst-gw-mgr image:'
                    sh "docker rmi hub.docker.hpecorp.net/atlas-qa/e2e-catalyst-gw-mgr"
                    echo "Removed hub.docker.hpecorp.net/atlas-qa/e2e-catalyst-gw-mgr image."
                } catch (err) {
                    echo "Image hub.docker.hpecorp.net/atlas-qa/e2e-catalyst-gw-mgr does not exist."
                }

                cleanWs()

                if (params.SEND_EMAILS) {
                    def emailSubject = "${env.JOB_NAME} ${env.BUILD_NUMBER} - Status ${currentBuild.result}"
                    def emailBodyTemplate = """
                    Build ran on branch: ${params.BRANCH_NAME}
                    Are logs on Report Portal?: ${params.ENABLE_REPORT_PORTAL}
                    Data Orchestrator version: ${opeVersion}

                    Link to build: ${env.BUILD_URL}
                    Link to console: ${env.BUILD_URL}console
                    Link to artifact: ${env.BUILD_URL}artifact
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
