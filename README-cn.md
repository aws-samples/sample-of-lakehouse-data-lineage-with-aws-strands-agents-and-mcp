# Data Lakehouse数据血缘分析系统

## 📋 系统概述

Data Lakehouse数据血缘分析系统是一个基于AWS Strands Agents和MCP技术以及AWS Neptune图数据库的数据血缘分析工具，提供自然语言交互界面，可以针对现代化湖仓一体架构提供专业的数据血缘分析，数据影响分析和数据治理建议。

### 🎯 核心特性
- **侧边栏系统提示词**: 可折叠的专家角色配置区域
- **模板化操作**: 系统提示词和分析指令都支持模板选择
- **优化性能**: 连接复用、超时控制、进度指示
- **自然语言输出**: 结构化的专业分析报告，非代码输出
- **实时监控**: 工具调用状态和性能统计

## 📚 参考资料

1. **[在基于 Amazon 云平台的湖仓一体架构上构建数据血缘的探索和实践](https://aws.amazon.com/cn/blogs/china/exploration-and-practice-of-building-data-lineage-on-the-integrated-lake-warehouse-architecture-based-on-aws/)**
   - 详细介绍如何在AWS湖仓一体架构中构建端到端的数据血缘系统

2. **[Building end-to-end data lineage for one-time and complex queries using Amazon Athena, Amazon Redshift, Amazon Neptune and dbt](https://aws.amazon.com/cn/blogs/big-data/building-end-to-end-data-lineage-for-one-time-and-complex-queries-using-amazon-athena-amazon-redshift-amazon-neptune-and-dbt/)**
   - 使用Amazon Athena、Redshift、Neptune和dbt构建复杂查询的数据血缘

## 📋 前提条件

### 系统要求
- **操作系统**: Amazon Linux 2023 (推荐)
- **Python版本**: 3.10+ (必需)
- **Neptune实例**: db.r5.large+ (必需)
- **网络**: VPC内访问Neptune
- **原始数据**: `raw-data/` 目录中的血缘数据文件

## 🚀 完整安装指南

### 步骤1: 系统环境设置
```bash
# 更新系统包
sudo yum update -y

# 安装Python 3.11和必需工具
sudo yum install python3.11 python3.11-pip python3.11-devel git -y

# 验证Python安装
python3.11 --version  # 应显示 >= 3.10
```

### 步骤2: 项目部署
```bash
# 克隆项目
git clone https://github.com/aws-samples/sample-of-lakehouse-data-lineage-with-aws-strands-agents-and-mcp.git
cd sample-of-lakehouse-data-lineage-with-aws-strands-agents-and-mcp

# 创建并激活虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 升级pip并安装依赖
pip install --upgrade pip setuptools wheel
pip install --only-binary=all -r requirements.txt

# 安装数据导入所需的额外包
pip install botocore gremlinpython
```

### 步骤3: 环境配置
```bash
# 复制并编辑环境配置
cp .env.example .env
vi .env
```

**环境配置文件 (.env)**:
```bash
NEPTUNE_ENDPOINT=neptune-db://your-cluster.cluster-xxxxxx.us-east-1.neptune.amazonaws.com
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
RAW_DATA_PATH=./raw-data
```

### 步骤4: 数据准备和导入

```bash
# 加载环境变量
source .env

# 运行table级别的数据处理脚本
export NEPTUNE_ENDPOINT="your-neptune-endpoint"
python3 process_lineage.py

# 运行schema级别的数据处理脚本
export NEPTUNE_ENDPOINT="your-neptune-endpoint"
python3 process_lineage_qw.py
```


### 步骤5: 启动应用

#### 5.1 先决条件检查
**启动应用前，请确保：**

1. **安全组配置**:
   ```bash
   # 验证EC2安全组中8501端口已开放
   # 添加入站规则：类型=自定义TCP，端口=8501，来源=0.0.0.0/0（或您的IP范围）
   ```

2. **IAM权限**（最小必需权限）:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "bedrock:InvokeModel",
                   "bedrock:InvokeModelWithResponseStream"
               ],
               "Resource": "arn:aws:bedrock:us-west-2::foundation-model/us.anthropic.claude-sonnet-4-20250514-v1:0"
           },
           {
               "Effect": "Allow",
               "Action": [
                   "neptune-db:ReadDataViaQuery",
                   "neptune-db:QueryStatus",
                   "neptune-db:GetQueryStatus"
               ],
               "Resource": "arn:aws:neptune-db:您的区域:账户ID:cluster/您的Neptune集群名/*"
           }
       ]
   }
   ```
   
   **替换以下占位符：**
   - `账户ID`: 您的AWS账户ID
   - `您的Neptune集群名`: 您的Neptune集群标识符
   - `您的区域`: 您的Neptune集群区域（如us-east-1）
   
   **📍 重要说明：**
   - Claude Sonnet 4模型仅在`us-west-2`区域可用
   - Neptune集群可以部署在任何您选择的区域
   - 跨区域访问：Bedrock调用到`us-west-2`，Neptune调用到您的集群区域

#### 5.2 启动应用
```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 启动Streamlit应用
#for bedrock claude
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0

#for qwen 235b
streamlit run src/app_qw.py --server.port=8501 --server.address=0.0.0.0
```

**⚠️ 重要提醒：**
- 确保EC2安全组允许8501端口的入站流量
- 验证EC2实例具有Bedrock Claude访问权限的IAM角色
- 检查`bedrock:InvokeModelWithResponseStream`权限已授予

### 步骤6: 访问和使用系统
1. 打开浏览器访问 `http://your-server-ip:8501`
2. 在侧边栏配置系统提示词
3. 选择分析模板并执行查询
4. 查看自然语言分析结果

### 使用流程

#### 步骤1: 配置系统提示词（左侧边栏）
- 展开"🎭 系统提示词"区域
- 选择预设模板或自定义角色
- 可选模板：数据血缘分析专家、S3数据源分析专家、数据影响分析专家等

#### 步骤2: 设置分析指令（主区域）
- 选择分析模板：连接状态检查、数据源统计、简单血缘分析等
- 点击"📋 使用模板"或手动编辑指令内容

#### 步骤3: 执行分析
- 点击"🔍 执行分析"按钮
- 观察进度指示器（10% → 30% → 50% → 70% → 100%）
- 查看结构化的分析结果

## 📊 使用场景示例

### 1. 🔍 新用户入门
```
系统提示词: 数据血缘分析专家
分析指令: 连接状态检查
预期输出: Neptune连接状态和基本信息
执行时间: 5-10秒
```

### 2. 📈 数据源统计分析
```
系统提示词: 数据血缘分析专家
分析指令: 统计图中的数据源数量和类型
预期输出: 
- 数据源总数统计
- 按类型分组的数据源分布
- 数据源连接度分析
执行时间: 30-40秒
```

### 3. 🔄 完整血缘路径分析
```
系统提示词: 数据血缘分析专家
分析指令: 分析数据的完整流向路径，识别关键的数据枢纽节点，追踪从原始数据到最终分析结果的完整路径
预期输出:
- 端到端数据流路径图
- 关键数据枢纽节点识别
- 数据转换节点分析
- 完整的数据血缘链路
执行时间: 40-60秒
```

### 4. ⚠️ 影响范围评估
```
系统提示词: 数据影响分析专家
分析指令: 评估核心数据源的影响范围。分析title_basics节点发生变更，会影响哪些下游系统？
执行时间: 45-60秒
```



## 💡 使用技巧

### 📝 最佳实践
1. **查询优化**: 使用具体的节点名称和字段名可以获得更精确的结果
2. **分步分析**: 对于复杂场景，建议先进行基础分析，再深入特定问题
3. **模板组合**: 可以组合使用不同的专家模板获得多角度分析
4. **结果验证**: 重要的分析结果建议通过多次查询进行验证

### 🎯 查询示例模板
- **节点查询**: "分析[节点名]的所有属性和连接关系"
- **路径追踪**: "追踪从[源节点]到[目标节点]的完整数据流路径"
- **影响分析**: "如果[节点/字段]发生变更，会影响哪些下游系统？"
- **统计分析**: "统计[类型]节点的数量和分布情况"

## 🔧 Amazon Linux 2023 故障排除

### 常见问题
1. **Python版本错误**: 
   ```bash
   # 确保使用Python 3.11
   python3.11 --version
   which python3.11
   ```

2. **依赖安装失败**:
   ```bash
   # 安装开发工具 (如果预编译包失败)
   sudo yum groupinstall "Development Tools" -y
   sudo yum install python3.11-devel -y
   
   # 重新安装依赖
   pip install -r requirements.txt
   ```

3. **网络连接问题**:
   ```bash
   # 检查安全组设置
   # 确保EC2可以访问Neptune (端口8182)
   # 确保浏览器可以访问EC2 (端口8501)
   # 验证安全组入站规则：
   aws ec2 describe-security-groups --group-ids sg-xxxxxxxxx
   ```

5. **Bedrock访问问题**:
   ```bash
   # 测试Bedrock访问（Claude Sonnet 4在us-west-2区域）
   aws bedrock list-foundation-models --region us-west-2
   
   # 检查IAM权限
   aws sts get-caller-identity
   
   # 测试特定Claude Sonnet 4模型访问
   aws bedrock invoke-model --model-id us.anthropic.claude-sonnet-4-20250514-v1:0 --body '{"messages":[{"role":"user","content":"test"}],"max_tokens":10}' --region us-west-2 /tmp/test-output.json
   
   # 验证跨区域访问正常工作
   aws bedrock get-foundation-model --model-identifier us.anthropic.claude-sonnet-4-20250514-v1:0 --region us-west-2
   ```

4. **权限问题**:
   ```bash
   # 为应用创建专用用户
   sudo useradd -m neptune-app
   sudo su - neptune-app
   ```

## 📈 性能指标
- **安装时间**: 5-10分钟
- **简单查询**: 5-15秒
- **中等查询**: 15-30秒
- **复杂查询**: 30-60秒
- **超时阈值**: 60秒自动终止

