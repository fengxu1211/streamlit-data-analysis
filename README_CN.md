# 智能BI演示

## 部署指南

### 1. 准备EC2实例
创建具有以下配置的EC2实例:

    - 软件镜像(AMI): Amazon Linux 2023
    - 虚拟服务器类型(实例类型): t3.large或更高
    - 防火墙(安全组): 允许22, 80端口 
    - 存储(卷): 1个卷 - 30 GiB

### 2. 配置权限  
为您的EC2实例绑定IAM角色。
并为此IAM角色附加以下权限的内联策略:
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

确保您已在us-west-2(美国西部(俄勒冈州))区域的AWS控制台中为Claude 2模型和Amazon Titan嵌入模型启用了模型访问。

### 3. 安装
在EC2中，以ec2-user用户SSH登录，在会话下执行以下命令。 如果不是此用户,您可以使用以下命令切换:

```
sudo su - ec2-user
```

```bash
# 安装组件
sudo dnf install docker python3-pip git -y && pip3 install docker-compose

# 修复docker的python包装器7.0 SSL版本问题
pip3 install docker==6.1.3 

# 配置组件
sudo systemctl enable docker && sudo systemctl start docker && sudo usermod -aG docker $USER

exit

# 以用户ec2-user打开一个新终端会话

# 配置 OpenSearch
sudo sh -c "echo 'vm.max_map_count=262144' > /etc/sysctl.conf" && sudo sysctl -p

# 克隆代码
git clone https://github.com/fengxu1211/streamlit-data-analysis.git

# 在本地构建docker镜像
cd streamlit-data-analysis && cp .env.template .env && docker-compose build

# 启动所有服务
docker-compose up -d
```

### 4. 初始化MySQL
在EC2中执行以下命令。
```
cd initial_data && unzip init_mysql_db.sql.zip && cd ..
docker exec nlq-mysql sh -c "mysql -u root -ppassword -D llm  < /opt/data/init_mysql_db.sql"
```

### 5. 初始化OpenSearch  
“docker-compose up”运行后至少等待3分钟

5.1 通过创建新索引来初始化示例数据的索引
```
docker exec nlq-webserver python opensearch_deploy.py
```

(可选)

5.2 通过创建新索引来初始化自定义数据的索引
```
docker exec nlq-webserver python opensearch_deploy.py custom
```
或者 5.3 通过追加现有索引来初始化自定义数据
```
docker exec nlq-webserver python opensearch_deploy.py custom false
```

如果脚本执行因任何错误而失败。 请使用以下命令删除索引并重新运行上一个命令。
```  
curl -XDELETE -k -u admin:admin "https://localhost:9200/uba"
```

### 6. 创建新的数据源配置文件（可选）
```
docker exec -it nlq-webserver python deployment/generate_new_profile.py
```

### 7. 访问Streamlit Web UI

在浏览器中打开网址: `http://<your-ec2-public-ip>` 

注意:使用 HTTP 而不是 HTTPS。
