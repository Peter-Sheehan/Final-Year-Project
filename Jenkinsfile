pipeline {
    agent any

    environment {
        VENV_DIR = "${WORKSPACE}\\venv"  // Define virtual environment directory
    }
    
    stages {
        stage('Verify Python Installation') {
            steps {
                bat 'python --version'
                bat 'pip --version'
            }
        }

        stage('Checkout') {
            steps {
                script {
                    git branch: 'main', url: 'https://github.com/Peter-Sheehan/Final-Year-Project.git'
                    // List directory contents after checkout
                    bat 'dir'
                }
            }
        }
        
        stage('Setup Python Environment') {
            steps {
                script {
                    bat """
                        python -m venv venv
                        call venv\\Scripts\\activate
                    """
                }
            }
        }
        
        stage('Run Dockerfile Linter') {
            steps {
                script {
                    // Verify Dockerfile2 exists
                    bat 'if not exist Dockerfile2 echo Dockerfile2 not found!'
                    bat """
                        call venv\\Scripts\\activate && python lint_cli.py Dockerfile2 --format all --output-dir reports
                    """
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'reports/*.csv', fingerprint: true
        }
        failure {
            echo 'Dockerfile linting failed - critical or high severity issues found'
        }
    }
}
