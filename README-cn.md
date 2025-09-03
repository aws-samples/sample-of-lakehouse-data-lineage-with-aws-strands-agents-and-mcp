# Data Lakehouse数据血缘分析系统

## 📋 系统概述

Data Lakehouse数据血缘分析系统是一个基于AWS Neptune图数据库的数据血缘分析工具，提供自然语言交互界面，支持专业的数据血缘分析和治理建议。

### 🎯 核心特性
- **侧边栏系统提示词**: 可折叠的专家角色配置区域
- **模板化操作**: 系统提示词和分析指令都支持模板选择
- **优化性能**: 连接复用、超时控制、进度指示
- **自然语言输出**: 结构化的专业分析报告，非代码输出
- **实时监控**: 工具调用状态和性能统计

## 📋 前提条件和数据准备

### 环境要求
- **操作系统**: Amazon Linux 2023 (推荐)
- **Python版本**: 3.10+ (必需)
- **Neptune实例**: db.r5.large+ (必需)
- **网络**: VPC内访问Neptune

### 数据血缘准备

在使用本系统之前，您需要先准备数据血缘信息并写入Neptune图数据库。可以参考以下AWS官方资源：

#### 📚 参考资料

1. **[在基于 Amazon 云平台的湖仓一体架构上构建数据血缘的探索和实践](https://aws.amazon.com/cn/blogs/china/exploration-and-practice-of-building-data-lineage-on-the-integrated-lake-warehouse-architecture-based-on-aws/)**
   - 详细介绍如何在AWS湖仓一体架构中构建端到端的数据血缘系统

2. **[Building end-to-end data lineage for one-time and complex queries using Amazon Athena, Amazon Redshift, Amazon Neptune and dbt](https://aws.amazon.com/cn/blogs/big-data/building-end-to-end-data-lineage-for-one-time-and-complex-queries-using-amazon-athena-amazon-redshift-amazon-neptune-and-dbt/)**
   - 使用Amazon Athena、Redshift、Neptune和dbt构建复杂查询的数据血缘

#### 🔧 数据准备步骤

1. **设计图模式**
   - 定义顶点类型：数据源、数据集、转换任务、输出表等
   - 定义边类型：数据流向、依赖关系、转换关系等

2. **数据采集**
   - 从ETL工具中提取血缘信息
   - 解析SQL查询获取表级和列级依赖
   - 收集数据处理作业的输入输出关系

3. **写入Neptune**
   - 使用Gremlin或SPARQL将血缘数据写入Neptune
   - 建立适当的索引以优化查询性能
   - 验证数据完整性和关系正确性

#### ⚠️ 重要提示

本系统是数据血缘的**分析和可视化工具**，不包含数据血缘的采集和写入功能。在使用前，请确保：

- ✅ Neptune实例已创建并配置
- ✅ 血缘数据已按图模式写入Neptune
- ✅ 网络连接和权限已正确配置
- ✅ 测试查询可以正常返回血缘关系

## 🚀 快速启动

### 系统要求
- **操作系统**: Amazon Linux 2023 (推荐)
- **Python版本**: 3.10+ (必需)
- **Neptune实例**: db.r5.large+ (必需)
- **网络**: VPC内访问Neptune

### Amazon Linux 2023 快速安装

#### 步骤1: 系统更新和Python安装
```bash
# 更新系统包
sudo yum update -y

# 安装Python 3.11 (预编译版本，无需编译)
sudo yum install python3.11 python3.11-pip python3.11-devel -y

# 验证Python版本
python3.11 --version  # 应显示 >= 3.10

# 安装Git (如需要)
sudo yum install git -y
```

#### 步骤2: 项目部署
```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/lakehouse-data-lineage-with-aws-strands-agents-and-mcp.git
cd lakehouse-data-lineage-with-aws-strands-agents-and-mcp

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 升级pip和安装工具
pip install --upgrade pip setuptools wheel

# 安装依赖 (使用预编译包，避免编译)
pip install --only-binary=all -r requirements.txt
```

#### 步骤3: 环境配置
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量 (使用vi或nano)
vi .env
```

**环境变量配置示例**:
```bash
NEPTUNE_ENDPOINT=neptune-db://your-cluster.cluster-xxxxxx.us-east-1.neptune.amazonaws.com
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
```

#### 步骤4: 启动系统
```bash
# 启动应用
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0

# 或使用启动脚本
python run.py
```

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

### 🔍 新用户入门
```
系统提示词: 数据血缘分析专家
分析指令: 连接状态检查
预期输出: Neptune连接状态和基本信息
执行时间: 5-10秒
```

### 📊 数据源盘点
```
系统提示词: S3数据源分析专家
分析指令: 数据源统计
预期输出: 数据源数量和类型统计
执行时间: 15-25秒
```

### 🔄 血缘关系分析
```
系统提示词: 数据血缘分析专家
分析指令: 简单血缘分析
预期输出: 主要数据流关系分析
执行时间: 20-35秒
```

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
   ```

4. **权限问题**:
   ```bash
   # 为应用创建专用用户
   sudo useradd -m neptune-app
   sudo su - neptune-app
   ```

### 性能优化
```bash
# 启用pip缓存
export PIP_CACHE_DIR=/tmp/pip-cache

# 使用更快的镜像源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

## 🚀 生产部署建议

### EC2实例配置
- **实例类型**: t3.medium 或更高
- **存储**: 至少20GB EBS
- **安全组**: 开放8501端口 (Streamlit)
- **IAM角色**: Neptune访问权限

### 系统服务配置
```bash
# 创建systemd服务文件
sudo tee /etc/systemd/system/neptune-lineage.service > /dev/null <<EOF
[Unit]
Description=Neptune Data Lineage Analysis System
After=network.target

[Service]
Type=simple
User=neptune-app
WorkingDirectory=/home/neptune-app/lakehouse-data-lineage-with-aws-strands-agents-and-mcp
Environment=PATH=/home/neptune-app/lakehouse-data-lineage-with-aws-strands-agents-and-mcp/venv/bin
ExecStart=/home/neptune-app/lakehouse-data-lineage-with-aws-strands-agents-and-mcp/venv/bin/streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
sudo systemctl enable neptune-lineage
sudo systemctl start neptune-lineage
sudo systemctl status neptune-lineage
```

## 📈 性能指标
- **安装时间**: 5-10分钟 (vs 30-60分钟编译安装)
- **简单查询**: 5-15秒
- **中等查询**: 15-30秒
- **复杂查询**: 30-60秒
- **超时阈值**: 60秒自动终止