# 企業級部署指南

本文檔提供 GitHub Monitor 在不同環境下的詳細部署指南。

## 目錄

- [生產環境部署](#生產環境部署)
- [高可用部署](#高可用部署)
- [雲端部署](#雲端部署)
- [CI/CD 整合](#cicd-整合)
- [監控和告警](#監控和告警)

## 生產環境部署

### 1. 服務器準備

#### 最低系統需求

- CPU: 2 核心
- RAM: 2GB
- 硬碟: 10GB
- 操作系統: Ubuntu 20.04 LTS 或更新版本

#### 安裝 Docker

```bash
# 更新系統
sudo apt-get update
sudo apt-get upgrade -y

# 安裝 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 添加當前用戶到 docker 組
sudo usermod -aG docker $USER

# 安裝 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 驗證安裝
docker --version
docker-compose --version
```

### 2. 部署步驟

#### 方案 A: 使用 Git 部署

```bash
# 1. 克隆專案
cd /opt
sudo git clone <repository-url> github-monitor
cd github-monitor

# 2. 配置環境變數
sudo cp .env.example .env
sudo vim .env
# 填入:
# - GITHUB_TOKEN
# - SLACK_WEBHOOK_URL
# - 其他配置

# 3. 配置監控規則
sudo vim config.yaml
# 設置要監控的儲存庫

# 4. 設置權限
sudo chown -R $USER:$USER .

# 5. 部署
make deploy

# 6. 驗證
make status
make health
```

#### 方案 B: 使用預構建映像

```bash
# 1. 創建工作目錄
sudo mkdir -p /opt/github-monitor
cd /opt/github-monitor

# 2. 下載配置文件
curl -O <url-to-config-files>/.env.example
curl -O <url-to-config-files>/config.yaml
curl -O <url-to-config-files>/docker-compose.yml
curl -O <url-to-config-files>/docker-compose.prod.yml

# 3. 配置
cp .env.example .env
vim .env
vim config.yaml

# 4. 拉取並啟動
docker pull your-registry.example.com/github-monitor:latest
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 5. 驗證
docker-compose ps
docker-compose logs -f
```

### 3. 開機自動啟動

#### 使用 systemd

創建服務文件 `/etc/systemd/system/github-monitor.service`:

```ini
[Unit]
Description=GitHub Monitor
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/github-monitor
ExecStart=/usr/local/bin/docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

啟用服務：

```bash
sudo systemctl daemon-reload
sudo systemctl enable github-monitor
sudo systemctl start github-monitor
sudo systemctl status github-monitor
```

### 4. 反向代理設置（可選）

如果需要 Web 界面，可以使用 Nginx：

```nginx
# /etc/nginx/sites-available/github-monitor
server {
    listen 80;
    server_name github-monitor.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

啟用配置：

```bash
sudo ln -s /etc/nginx/sites-available/github-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 高可用部署

### Docker Swarm 集群

#### 1. 初始化 Swarm

```bash
# 在管理節點上
docker swarm init --advertise-addr <MANAGER-IP>

# 記錄輸出的 join token

# 在工作節點上加入
docker swarm join --token <TOKEN> <MANAGER-IP>:2377
```

#### 2. 部署 Stack

```bash
# 創建 overlay 網絡
docker network create --driver overlay github-monitor-net

# 部署服務
docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml github-monitor

# 擴展服務（3 個副本）
docker service scale github-monitor_github-monitor=3

# 查看服務狀態
docker service ls
docker service ps github-monitor_github-monitor
```

#### 3. 滾動更新

```bash
# 更新映像
docker service update --image your-registry.example.com/github-monitor:v2.0 github-monitor_github-monitor

# 回滾
docker service rollback github-monitor_github-monitor
```

### Kubernetes 部署

#### 1. 創建 Namespace

```bash
kubectl create namespace github-monitor
```

#### 2. 創建 Secret

```bash
# GitHub Token
kubectl create secret generic github-token \
  --from-literal=token='ghp_your_token' \
  -n github-monitor

# Slack Webhook
kubectl create secret generic slack-webhook \
  --from-literal=url='https://hooks.slack.com/...' \
  -n github-monitor
```

#### 3. 部署清單

**deployment.yaml**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-monitor
  namespace: github-monitor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: github-monitor
  template:
    metadata:
      labels:
        app: github-monitor
    spec:
      containers:
      - name: github-monitor
        image: your-registry.example.com/github-monitor:latest
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "500m"
            memory: "256Mi"
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-token
              key: token
        - name: SLACK_WEBHOOK_URL
          valueFrom:
            secretKeyRef:
              name: slack-webhook
              key: url
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
        - name: logs
          mountPath: /var/log/github-monitor
      volumes:
      - name: config
        configMap:
          name: github-monitor-config
      - name: logs
        emptyDir: {}
```

**configmap.yaml**:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: github-monitor-config
  namespace: github-monitor
data:
  config.yaml: |
    monitor:
      check_interval: 300
      repositories:
        - owner: "your-org"
          repo: "your-repo"
          branches:
            - main
    # ... 其他配置
```

#### 4. 部署

```bash
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml

# 查看狀態
kubectl get pods -n github-monitor
kubectl logs -f deployment/github-monitor -n github-monitor
```

## 雲端部署

### AWS ECS

#### 1. 創建 ECR 儲存庫

```bash
aws ecr create-repository --repository-name github-monitor

# 登錄 ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# 推送映像
docker tag github-monitor:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/github-monitor:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/github-monitor:latest
```

#### 2. 創建任務定義

**task-definition.json**:

```json
{
  "family": "github-monitor",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "github-monitor",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/github-monitor:latest",
      "essential": true,
      "environment": [],
      "secrets": [
        {
          "name": "GITHUB_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:github-token"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/github-monitor",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 3. 創建服務

```bash
aws ecs create-service \
  --cluster default \
  --service-name github-monitor \
  --task-definition github-monitor \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

### Google Cloud Run

```bash
# 1. 構建並推送到 GCR
gcloud builds submit --tag gcr.io/PROJECT-ID/github-monitor

# 2. 部署到 Cloud Run
gcloud run deploy github-monitor \
  --image gcr.io/PROJECT-ID/github-monitor \
  --platform managed \
  --region us-central1 \
  --set-env-vars GITHUB_TOKEN=secret:github-token:latest \
  --set-env-vars SLACK_WEBHOOK_URL=secret:slack-webhook:latest \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 3
```

### Azure Container Instances

```bash
# 1. 推送到 ACR
az acr build --registry myregistry --image github-monitor:latest .

# 2. 部署容器實例
az container create \
  --resource-group myResourceGroup \
  --name github-monitor \
  --image myregistry.azurecr.io/github-monitor:latest \
  --cpu 1 \
  --memory 1 \
  --environment-variables \
    GITHUB_TOKEN='<token>' \
    SLACK_WEBHOOK_URL='<webhook>' \
  --restart-policy Always
```

## CI/CD 整合

### GitHub Actions

**.github/workflows/deploy.yml**:

```yaml
name: Build and Deploy

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Registry
        uses: docker/login-action@v2
        with:
          registry: your-registry.example.com
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            your-registry.example.com/github-monitor:latest
            your-registry.example.com/github-monitor:${{ github.sha }}

      - name: Deploy to production
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_KEY }}
          script: |
            cd /opt/github-monitor
            docker-compose pull
            docker-compose up -d
```

### GitLab CI/CD

**.gitlab-ci.yml**:

```yaml
stages:
  - build
  - deploy

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

deploy:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache openssh-client
    - eval $(ssh-agent -s)
    - echo "$SSH_PRIVATE_KEY" | ssh-add -
  script:
    - ssh $DEPLOY_USER@$DEPLOY_HOST "cd /opt/github-monitor && docker-compose pull && docker-compose up -d"
  only:
    - main
```

## 監控和告警

### Prometheus + Grafana

**docker-compose.monitoring.yml**:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    ports:
      - "8080:8080"

volumes:
  prometheus-data:
  grafana-data:
```

**prometheus.yml**:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'github-monitor'
    static_configs:
      - targets: ['github-monitor:8080']
```

啟動監控：

```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

訪問 Grafana: http://localhost:3000 (admin/admin)

### ELK Stack 日誌收集

**docker-compose.elk.yml**:

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5000:5000"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

---

更多詳細信息請參考主 [README.md](README.md)
