pipeline {
    agent any
    
    tools{
        maven 'maven_3_6_3'
        jdk 'jdk11'
    }
    
    environment {
        // Docker 私有仓库配置
        DOCKER_REGISTRY = "192.168.10.114:5050"
        // 应用名称
        APP_NAME = "vlm-vla-tracker"
        // MongoDB 数据库名称
        MONGO_DB = "vlm_vla_tracker"
    }

    stages {
        stage('Cleanup Workspace') {
            steps {
                script {
                    deleteDir() // 清理工作空间
                }
            }
        }
        stage('Checkout Code') {
            steps {
                checkout scmGit(branches: [[name: '*/master']], extensions: [], userRemoteConfigs: [[url: 'https://github.com/SHENYY1993/vlm-vla-tracker.git']])
            }
        }
        stage('Build') {
            steps {
                script {
                    // 获取 Git 提交短哈希作为标签
                    COMMIT_HASH = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    
                    // 构建 Docker 镜像
                    sh """
                        echo "Building Docker image with commit hash: ${COMMIT_HASH}"
                        docker build -t ${APP_NAME}:${COMMIT_HASH} .
                        docker tag ${APP_NAME}:${COMMIT_HASH} ${APP_NAME}:latest
                    """
                }
            }
        }
        stage('Push to Registry'){
            steps{
                script {
                    sh """
                        # 登录到私有仓库（如果需要）
                        # docker login ${DOCKER_REGISTRY} -u username -p password
                        
                        # 推送镜像到私有仓库
                        docker tag ${APP_NAME}:${COMMIT_HASH} ${DOCKER_REGISTRY}/${APP_NAME}:${COMMIT_HASH}
                        docker push ${DOCKER_REGISTRY}/${APP_NAME}:${COMMIT_HASH}
                        
                        # 可选：同时标记为 latest 并推送
                        docker tag ${DOCKER_REGISTRY}/${APP_NAME}:${COMMIT_HASH} ${DOCKER_REGISTRY}/${APP_NAME}:latest
                        docker push ${DOCKER_REGISTRY}/${APP_NAME}:latest
                        
                        # 本地保留 latest 标签
                        docker tag ${DOCKER_REGISTRY}/${APP_NAME}:latest ${APP_NAME}:latest
                    """
                }
            }
        }
        stage('Deploy to Production') {
            steps {
                script {
                    sh """
                        # 停止并移除旧容器（如果存在）
                        echo "Stopping existing containers..."
                        docker-compose down || true
                        
                        # 清理旧镜像（可选）
                        docker rmi ${DOCKER_REGISTRY}/${APP_NAME}:${COMMIT_HASH} || true
                        docker rmi ${DOCKER_REGISTRY}/${APP_NAME}:latest || true
                        
                        # 启动新容器
                        echo "Starting new containers..."
                        docker-compose up -d
                        
                        # 等待服务启动
                        sleep 30
                        
                        # 健康检查
                        echo "Performing health check..."
                        curl -f http://localhost:8083/health || exit 1
                        curl -f http://localhost:8000/api/stats || exit 1
                        
                        echo "Deployment completed successfully!"
                    """
                }
            }
        }
    }
    
    post {
        always {
            // 清理 Docker 悬空镜像
            sh 'docker images -q --filter "dangling=true" | xargs -r docker rmi 2>/dev/null || true'
        }
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed!'
        }
    }
}