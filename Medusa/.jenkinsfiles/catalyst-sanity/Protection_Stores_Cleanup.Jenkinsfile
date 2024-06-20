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
        cron ' '
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
        string(defaultValue: '',
                description: 'SHA/COMMIT-ID value to checkout - added to use for PR check',
                name: 'COMMIT_ID')
        choice(
            name: 'CONFIG_FILE',
            choices: ['variables_storeonce','variables_sanity_scdev01','variables_sanity_scint','variables_sanity_prod','variables_storeonce_scint'],
            description: 'Select the variables files to cleanup the stores'
    )
    }

    environment {
        CONTAINER_NAME = "atlas-protection-store-cleanup-${env.BUILD_NUMBER}"
        CONFIG_FILE = "${params.CONFIG_FILE}"
        SERVICE_VERSION = 'service1'
    }
    stages {
        stage('Checkout Repository') {
            steps {
                script {
                    if (params.COMMIT_ID) {
                        checkout([
                            $class: 'GitSCM',
                            branches: [[name: "${params.COMMIT_ID}" ]],
                            extensions: [cloneOption(noTags: false, reference: '', shallow: true, timeout: 30)],
                            userRemoteConfigs: [[url: 'https://github.hpe.com/nimble/qa_automation.git', credentialsId: 'nmbljenkins', refspec: '+refs/pull/*/head:refs/remotes/origin/pr/*']]
                        ])
                    } else {
                        checkout([
                            $class: 'GitSCM',
                            branches: [[name: "${params.BRANCH_NAME}"]],
                            extensions: [cloneOption(noTags: false, reference: '', shallow: true, timeout: 30)],
                            userRemoteConfigs: [[credentialsId: 'nmbljenkins', url: 'https://github.hpe.com/nimble/qa_automation.git']]]
                        )
                    }
                }
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
        stage('Run Protection Stores Cleanup') {
            steps {
                withCredentials([string(credentialsId: 'RP_API_KEY_2', variable: 'RP_API_KEY')]) {
                    script {
                        def command = "docker run -w /Medusa/tests/catalyst_gateway_e2e --name ${env.CONTAINER_NAME} --pull always -e RP_API_KEY=$RP_API_KEY -e JENKINS_URL=${env.JENKINS_URL} -e BUILD_URL=${env.BUILD_URL} -e SERVICE_VERSION=${env.SERVICE_VERSION} -e CONFIG_FILE=${env.CONFIG_FILE} -v $WORKSPACE/Medusa:/Medusa hub.docker.hpecorp.net/atlas-qa/e2e-catalyst-gw-mgr pytest -sv -c pytest_protection_store_cleanup.ini --junitxml=logs/junit.xml"
                        if (params.ENABLE_REPORT_PORTAL) {
                            sh "${command} --reportportal /Medusa/tests/catalyst_gateway_e2e/test_scripts/cleanup_protection_stores/test_cleanup_protection_stores.py"
                        } else {
                            sh "${command} /Medusa/tests/catalyst_gateway_e2e/test_scripts/cleanup_protection_stores/test_cleanup_protection_stores.py"
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
                def summary = ""

                try {
                    echo "Attempting to extract junit xml report from ${env.CONTAINER_NAME} container:"
                    sh "docker cp ${env.CONTAINER_NAME}:/Medusa/tests/catalyst_gateway_e2e/logs/junit.xml ${WORKSPACE}/${env.BUILD_NUMBER}_junit.xml"
                    summary = junit allowEmptyResults: true, healthScaleFactor: 0.0, skipPublishingChecks: true, testResults: "${env.BUILD_NUMBER}_junit.xml"
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
                def run_status = ""
                def color = ""
                if(currentBuild.currentResult == "SUCCESS" && summary.failCount == 0 && summary.skipCount == 0) {
                    run_status = "SUCCESS"
                    color = "good"
                }
                else if(currentBuild.currentResult == "FAILURE") {
                    run_status = "FAILURE"
                    color = "danger"
                }
                else if(summary.totalCount == summary.skipCount) {
                    run_status = "SKIPPED"
                    color = "danger"
                    currentBuild.result = 'UNSTABLE' // In all Skipped scenario if we don't set this here then in jenkins UI, job status will show as Success and green.
                }
                else {
                    run_status = "FAILURE"
                    color = "danger"
                }
                if (params.SEND_EMAILS) {
                    def emailSubject = "${env.JOB_NAME} ${env.BUILD_NUMBER} - Status ${run_status}"
                    def emailBodyTemplate = """
                    Build ran on branch: ${params.BRANCH_NAME}
                    Are logs on Report Portal?: ${params.ENABLE_REPORT_PORTAL}
                    OPE version: ${opeVersion}

                    Link to build: ${env.BUILD_URL}
                    Link to console: ${env.BUILD_URL}console
                    Link to artifact: ${env.BUILD_URL}artifact
                    """.stripIndent()

                    emailBodyTemplate += testResults

                    mail body: emailBodyTemplate, subject: emailSubject, to: params.EMAIL_LIST
                }

                // Send notification to slack
                slackSend (message: "${env.JOB_NAME} ${env.BUILD_NUMBER} - ${run_status}\n${env.BUILD_URL}console\n${testResults}\nOPE version: ${opeVersion}",
                           channel: 'jenkins_notifications',
                           teamDomain: 'hpe-internal',
                           tokenCredentialId: 'slack-notificaitons',
                           color: "${color}",
                           iconEmoji: ':hpe-bot')

            }
        }

        cleanup {
            cleanWs()
        }
    }
}
