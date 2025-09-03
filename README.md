# Lakehouse E2E Data Lineage with AWS Strands Agents and MCP

## 📋 System Overview

The Data Lakehouse lineage analysis system is a data lineage analysis tool based on AWS Neptune graph database, providing natural language interaction interface and supporting professional data lineage analysis and governance recommendations.

### 🎯 Core Features
- **Sidebar System Prompts**: Collapsible expert role configuration area
- **Template Operations**: Both system prompts and analysis instructions support template selection
- **Performance Optimization**: Connection reuse, timeout control, progress indication
- **Natural Language Output**: Structured professional analysis reports, non-code output
- **Real-time Monitoring**: Tool call status and performance statistics

## 📋 Prerequisites and Data Preparation

### System Requirements
- **Operating System**: Amazon Linux 2023 (Recommended)
- **Python Version**: 3.10+ (Required)
- **Neptune Instance**: db.r5.large+ (Required)
- **Network**: VPC access to Neptune

### Data Lineage Preparation

Before using this system, you need to prepare data lineage information and write it to the Neptune graph database. Please refer to the following official AWS resources:

#### 📚 Reference Materials

1. **[Exploration and Practice of Building Data Lineage on the Integrated Lake-Warehouse Architecture Based on AWS](https://aws.amazon.com/cn/blogs/china/exploration-and-practice-of-building-data-lineage-on-the-integrated-lake-warehouse-architecture-based-on-aws/)**
   - Detailed introduction on how to build end-to-end data lineage systems in AWS lakehouse architecture

2. **[Building end-to-end data lineage for one-time and complex queries using Amazon Athena, Amazon Redshift, Amazon Neptune and dbt](https://aws.amazon.com/cn/blogs/big-data/building-end-to-end-data-lineage-for-one-time-and-complex-queries-using-amazon-athena-amazon-redshift-amazon-neptune-and-dbt/)**
   - Building data lineage for complex queries using Amazon Athena, Redshift, Neptune, and dbt

#### 🔧 Data Preparation Steps

1. **Design Graph Schema**
   - Define vertex types: data sources, datasets, transformation tasks, output tables, etc.
   - Define edge types: data flow, dependency relationships, transformation relationships, etc.

2. **Data Collection**
   - Extract lineage information from ETL tools
   - Parse SQL queries to obtain table-level and column-level dependencies
   - Collect input-output relationships of data processing jobs

3. **Write to Neptune**
   - Use Gremlin or SPARQL to write lineage data to Neptune
   - Establish appropriate indexes to optimize query performance
   - Validate data integrity and relationship correctness

#### ⚠️ Important Notice

This system is a **data lineage analysis and visualization tool** and does not include data lineage collection and ingestion functionality. Before use, please ensure:

- ✅ Neptune instance is created and configured
- ✅ Lineage data is written to Neptune according to graph schema
- ✅ Network connections and permissions are properly configured
- ✅ Test queries can return lineage relationships normally

## 🚀 Quick Start

### Installation Requirements
- **Operating System**: Amazon Linux 2023 (Recommended)
- **Python Version**: 3.10+ (Required)
- **Neptune Instance**: db.r5.large+ (Required)
- **Network**: VPC access to Neptune

### Amazon Linux 2023 Fast Installation

#### Step 1: System Update and Python Installation
```bash
# Update system packages
sudo yum update -y

# Install Python 3.11 (pre-compiled, no compilation needed)
sudo yum install python3.11 python3.11-pip python3.11-devel -y

# Verify Python version
python3.11 --version  # Should show >= 3.10

# Install Git (if needed)
sudo yum install git -y
```

#### Step 2: Project Deployment
```bash
# Clone project
git clone https://github.com/YOUR_USERNAME/lakehouse-data-lineage-with-aws-strands-agents-and-mcp.git
cd lakehouse-data-lineage-with-aws-strands-agents-and-mcp

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip and install tools
pip install --upgrade pip setuptools wheel

# Install dependencies (use pre-compiled packages, avoid compilation)
pip install --only-binary=all -r requirements.txt
```

#### Step 3: Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables (using vi or nano)
vi .env
```

**Environment Configuration Example**:
```bash
NEPTUNE_ENDPOINT=neptune-db://your-cluster.cluster-xxxxxx.us-east-1.neptune.amazonaws.com
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
```

#### Step 4: Start System
```bash
# Start application
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0

# Or use startup script
python run.py
```

### Usage Workflow

#### Step 1: Configure System Prompts (Sidebar)
- Expand "🎭 System Prompts" area
- Select preset templates or custom roles
- Available templates: Data Lineage Expert, S3 Data Source Expert, Data Impact Expert, etc.

#### Step 2: Set Analysis Instructions (Main Area)
- Select analysis templates: Connection Check, Data Source Statistics, Simple Lineage Analysis, etc.
- Click "📋 Use Template" or manually edit instruction content

#### Step 3: Execute Analysis
- Click "🔍 Execute Analysis" button
- Observe progress indicator (10% → 30% → 50% → 70% → 100%)
- View structured analysis results

## 📊 Usage Scenarios

### 🔍 New User Onboarding
```
System Prompt: Data Lineage Expert
Analysis Instruction: Connection Status Check
Expected Output: Neptune connection status and basic information
Execution Time: 5-10 seconds
```

### 📊 Data Source Inventory
```
System Prompt: S3 Data Source Expert
Analysis Instruction: Data Source Statistics
Expected Output: Data source count and type statistics
Execution Time: 15-25 seconds
```

### 🔄 Lineage Relationship Analysis
```
System Prompt: Data Lineage Expert
Analysis Instruction: Simple Lineage Analysis
Expected Output: Main data flow relationship analysis
Execution Time: 20-35 seconds
```

## 🔧 Amazon Linux 2023 Troubleshooting

### Common Issues
1. **Python version error**: 
   ```bash
   # Ensure using Python 3.11
   python3.11 --version
   which python3.11
   ```

2. **Dependency installation failure**:
   ```bash
   # Install development tools (if pre-compiled packages fail)
   sudo yum groupinstall "Development Tools" -y
   sudo yum install python3.11-devel -y
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

3. **Network connection issues**:
   ```bash
   # Check security group settings
   # Ensure EC2 can access Neptune (port 8182)
   # Ensure browser can access EC2 (port 8501)
   ```

4. **Permission issues**:
   ```bash
   # Create dedicated user for application
   sudo useradd -m neptune-app
   sudo su - neptune-app
   ```

### Performance Optimization
```bash
# Enable pip cache
export PIP_CACHE_DIR=/tmp/pip-cache

# Use faster mirror source
pip config set global.index-url https://pypi.org/simple
```

## 🚀 Production Deployment Recommendations

### EC2 Instance Configuration
- **Instance Type**: t3.medium or higher
- **Storage**: At least 20GB EBS
- **Security Group**: Open port 8501 (Streamlit)
- **IAM Role**: Neptune access permissions

### System Service Configuration
```bash
# Create systemd service file
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

# Enable and start service
sudo systemctl enable neptune-lineage
sudo systemctl start neptune-lineage
sudo systemctl status neptune-lineage
```

## 📈 Performance Metrics
- **Installation Time**: 5-10 minutes (vs 30-60 minutes compilation)
- **Simple queries**: 5-15 seconds
- **Medium queries**: 15-30 seconds
- **Complex queries**: 30-60 seconds
- **Timeout threshold**: 60 seconds automatic termination