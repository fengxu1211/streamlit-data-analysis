# Intelligent BI Demo

## Deployment Guide

### 1. Prepare EC2 Instance
Create an EC2 with following configuration:

    - Software Image (AMI): Amazon Linux 2023
    - Virtual server type (instance type): t3.large or higher
    - Firewall (security group): Allow 22, 80 port
    - Storage (volumes): 1 volume(s) - 30 GiB

### 2. Config Permission
Bind an IAM Role to your EC2 instance.
And attach an inline policy to this IAM Role with following permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "bedrock:*",
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "*"
        }
    ]
}
```

Make sure you have enabled model access in AWS Console in us-west-2 (美国西部 (俄勒冈州)) region for Claude 2 model.

### 3. Installation
Execute following commands in EC2 with ec2-user. If not this user, you can use following command to switch:

```
sudo su - ec2-user
```

```bash
# Install components
sudo dnf install docker python3-pip git -y && pip3 install docker-compose

# Config components
sudo systemctl enable docker && sudo systemctl start docker && sudo usermod -aG docker $USER && sudo newgrp docker

# Config for OpenSearch
sudo sh -c "echo 'vm.max_map_count=262144' > /etc/sysctl.conf" && sudo sysctl -p

# Clone code
git clone https://github.com/fengxu1211/streamlit-data-analysis.git

# Build docker image locally
cd streamlit-data-analysis && cp .env.template .env && docker-compose build

# Start all services
docker-compose up -d
```

### 4. Initialize MySQL
Execute following commands in EC2.
```
cd initial_data && unzip init_mysql_db.sql.zip && cd ..
docker exec nlq-mysql sh -c "mysql -u root -ppassword -D llm  < /opt/data/init_mysql_db.sql"
```

### 5. Initialize OpenSearch
Wait for at least 3 mins after "docker-compose up" ran

```
docker exec nlq-webserver python opensearch_deploy.py
```

If the script's execution has failed with any error. Please use following command to delete index and rerun the previous command.
```
curl -XDELETE -k -u admin:admin "https://localhost:9200/uba"
```

### 6. Access Streamlit Web UI

Open url in the browser: `http://<your-ec2-public-ip>`

Note: use HTTP instead of HTTPs.
