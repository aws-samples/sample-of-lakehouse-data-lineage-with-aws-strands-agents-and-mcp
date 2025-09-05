# Lakehouse E2E Data Lineage with AWS Strands Agents and MCP

## 📋 System Overview

The Data Lakehouse lineage analysis system is a data lineage analysis tool based on AWS Neptune graph database, providing natural language interaction interface and supporting professional data lineage analysis and governance recommendations.

### 🎯 Core Features
- **Sidebar System Prompts**: Collapsible expert role configuration area
- **Template Operations**: Both system prompts and analysis instructions support template selection
- **Performance Optimization**: Connection reuse, timeout control, progress indication
- **Natural Language Output**: Structured professional analysis reports, non-code output
- **Real-time Monitoring**: Tool call status and performance statistics

## 📋 Prerequisites

### System Requirements
- **Operating System**: Amazon Linux 2023 (Recommended)
- **Python Version**: 3.10+ (Required)
- **Neptune Instance**: db.r5.large+ (Required)
- **Network**: VPC access to Neptune
- **Raw Data**: Lineage data files in `raw-data/` directory

## 🚀 Complete Setup Guide

### Step 1: System Environment Setup
```bash
# Update system packages
sudo yum update -y

# Install Python 3.11 and required tools
sudo yum install python3.11 python3.11-pip python3.11-devel git -y

# Verify Python installation
python3.11 --version  # Should show >= 3.10
```

### Step 2: Project Deployment
```bash
# Clone project
git clone https://github.com/aws-samples/sample-of-lakehouse-data-lineage-with-aws-strands-agents-and-mcp.git
cd sample-of-lakehouse-data-lineage-with-aws-strands-agents-and-mcp

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip setuptools wheel
pip install --only-binary=all -r requirements.txt

# Install additional packages for data ingestion
pip install botocore gremlinpython
```

### Step 3: Environment Configuration
```bash
# Copy and edit environment configuration
cp .env.example .env
vi .env
```

**Environment Configuration (.env file)**:
```bash
NEPTUNE_ENDPOINT=neptune-db://your-cluster.cluster-xxxxxx.us-east-1.neptune.amazonaws.com
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
RAW_DATA_PATH=./raw-data
```

### Step 4: Data Preparation and Ingestion

```bash
# Load environment variables
source .env

# Run data processing script
python3 process_lineage.py

# Verify data ingestion
python3 -c "from gremlin_python.driver import client; from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection; import os; conn = DriverRemoteConnection(f'wss://{os.getenv('NEPTUNE_ENDPOINT')}:8182/gremlin', 'g'); g = client.Client(conn, 'g'); print('Vertices:', g.V().count().next()); print('Edges:', g.E().count().next()); conn.close()"
```

### Step 5: Start Application
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Start Streamlit application
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
```

### Step 6: Access and Use System
1. Open browser and navigate to `http://your-server-ip:8501`
2. Configure system prompts in the sidebar
3. Select analysis templates and execute queries
4. View natural language analysis results

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

## 📈 Performance Metrics
- **Installation Time**: 5-10 minutes
- **Simple queries**: 5-15 seconds
- **Medium queries**: 15-30 seconds
- **Complex queries**: 30-60 seconds
- **Timeout threshold**: 60 seconds automatic termination

## 📚 Reference Materials

1. **[Exploration and Practice of Building Data Lineage on the Integrated Lake-Warehouse Architecture Based on AWS](https://aws.amazon.com/cn/blogs/china/exploration-and-practice-of-building-data-lineage-on-the-integrated-lake-warehouse-architecture-based-on-aws/)**
   - Detailed introduction on how to build end-to-end data lineage systems in AWS lakehouse architecture

2. **[Building end-to-end data lineage for one-time and complex queries using Amazon Athena, Amazon Redshift, Amazon Neptune and dbt](https://aws.amazon.com/cn/blogs/big-data/building-end-to-end-data-lineage-for-one-time-and-complex-queries-using-amazon-athena-amazon-redshift-amazon-neptune-and-dbt/)**
   - Building data lineage for complex queries using Amazon Athena, Redshift, Neptune, and dbt
