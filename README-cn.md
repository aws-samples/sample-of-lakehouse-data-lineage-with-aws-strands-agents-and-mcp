# Data Lakehouse数据血缘分析系统

## 📋 系统概述

Data Lakehouse数据血缘分析系统是一个基于AWS Neptune图数据库的数据血缘分析工具，提供自然语言交互界面，支持专业的数据血缘分析和治理建议。

### 🎯 核心特性
- **侧边栏系统提示词**: 可折叠的专家角色配置区域
- **模板化操作**: 系统提示词和分析指令都支持模板选择
- **优化性能**: 连接复用、超时控制、进度指示
- **自然语言输出**: 结构化的专业分析报告，非代码输出
- **实时监控**: 工具调用状态和性能统计

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

# 运行数据处理脚本
python3 process_lineage.py

# 验证数据导入
python3 -c "from gremlin_python.driver import client; from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection; import os; conn = DriverRemoteConnection(f'wss://{os.getenv('NEPTUNE_ENDPOINT')}:8182/gremlin', 'g'); g = client.Client(conn, 'g'); print('顶点数:', g.V().count().next()); print('边数:', g.E().count().next()); conn.close()"
```

### 步骤5: 启动应用
```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 启动Streamlit应用
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
```

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

## 📈 性能指标
- **安装时间**: 5-10分钟
- **简单查询**: 5-15秒
- **中等查询**: 15-30秒
- **复杂查询**: 30-60秒
- **超时阈值**: 60秒自动终止

## 📚 参考资料

1. **[在基于 Amazon 云平台的湖仓一体架构上构建数据血缘的探索和实践](https://aws.amazon.com/cn/blogs/china/exploration-and-practice-of-building-data-lineage-on-the-integrated-lake-warehouse-architecture-based-on-aws/)**
   - 详细介绍如何在AWS湖仓一体架构中构建端到端的数据血缘系统

2. **[Building end-to-end data lineage for one-time and complex queries using Amazon Athena, Amazon Redshift, Amazon Neptune and dbt](https://aws.amazon.com/cn/blogs/big-data/building-end-to-end-data-lineage-for-one-time-and-complex-queries-using-amazon-athena-amazon-redshift-amazon-neptune-and-dbt/)**
   - 使用Amazon Athena、Redshift、Neptune和dbt构建复杂查询的数据血缘