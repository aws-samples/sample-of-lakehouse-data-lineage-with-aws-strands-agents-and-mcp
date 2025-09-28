# Lakehouse Data Lineage with AWS Strands Agents and MCP

## 📋 System Overview

The Data Lakehouse data lineage analysis system is a data lineage analysis tool built on AWS Strands Agents and MCP technology with AWS Neptune graph database, providing natural language interaction interface and delivering professional data lineage analysis, data impact analysis, and data governance recommendations for modern lakehouse architectures.

### 🎯 Core Features
- **Sidebar System Prompts**: Collapsible expert role configuration area
- **Template Operations**: Both system prompts and analysis instructions support template selection
- **Performance Optimization**: Connection reuse, timeout control, progress indication
- **Natural Language Output**: Structured professional analysis reports, non-code output
- **Real-time Monitoring**: Tool call status and performance statistics

## 📚 Reference Materials

1. **[Exploration and Practice of Building Data Lineage on the Integrated Lake-Warehouse Architecture Based on AWS](https://aws.amazon.com/cn/blogs/china/exploration-and-practice-of-building-data-lineage-on-the-integrated-lake-warehouse-architecture-based-on-aws/)**
   - Detailed introduction on how to build end-to-end data lineage systems in AWS lakehouse architecture

2. **[Building end-to-end data lineage for one-time and complex queries using Amazon Athena, Amazon Redshift, Amazon Neptune and dbt](https://aws.amazon.com/cn/blogs/big-data/building-end-to-end-data-lineage-for-one-time-and-complex-queries-using-amazon-athena-amazon-redshift-amazon-neptune-and-dbt/)**
   - Building data lineage for complex queries using Amazon Athena, Redshift, Neptune, and dbt

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

# Run table-level data processing script
export NEPTUNE_ENDPOINT="your-neptune-endpoint"
python3 process_lineage.py

# Run schema-level data processing script
export NEPTUNE_ENDPOINT="your-neptune-endpoint"
python3 process_lineage_qw.py
```

### Step 5: Start Application

#### 5.1 Prerequisites Check
**Before starting the application, ensure:**

1. **Security Group Configuration**:
   ```bash
   # Verify port 8501 is open in EC2 security group
   # Add inbound rule: Type=Custom TCP, Port=8501, Source=0.0.0.0/0 (or your IP range)
   ```

2. **IAM Permissions** (Minimum Required):
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
               "Resource": "arn:aws:neptune-db:YOUR-REGION:ACCOUNT-ID:cluster/YOUR-NEPTUNE-CLUSTER/*"
           }
       ]
   }
   ```
   
   **Replace the following placeholders:**
   - `ACCOUNT-ID`: Your AWS account ID
   - `YOUR-NEPTUNE-CLUSTER`: Your Neptune cluster identifier
   - `YOUR-REGION`: Your Neptune cluster region (e.g., us-east-1)
   
   **📍 Important Notes:**
   - Claude Sonnet 4 model is only available in `us-west-2` region
   - Neptune cluster can be in any region where you deployed it
   - Cross-region access: Bedrock calls go to `us-west-2`, Neptune calls go to your cluster region

#### 5.2 Start Application
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Start Streamlit application
# For Bedrock Claude
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0

# For Qwen 235B
streamlit run src/app_qw.py --server.port=8501 --server.address=0.0.0.0
```

**⚠️ Important Notes:**
- Ensure EC2 security group allows inbound traffic on port 8501
- Verify EC2 instance has IAM role with Bedrock Claude access permissions
- Check that `bedrock:InvokeModelWithResponseStream` permission is granted

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
- Select analysis templates: Connection Status Check, Data Source Statistics, Simple Lineage Analysis, etc.
- Click "📋 Use Template" or manually edit instruction content

#### Step 3: Execute Analysis
- Click "🔍 Execute Analysis" button
- Observe progress indicator (10% → 30% → 50% → 70% → 100%)
- View structured analysis results

## 📊 Usage Scenarios

### 1. 🔍 New User Onboarding
```
System Prompt: Data Lineage Expert
Analysis Instruction: Connection Status Check
Expected Output: Neptune connection status and basic information
Execution Time: 5-10 seconds
```

### 2. 📈 Data Source Statistical Analysis
```
System Prompt: Data Lineage Expert
Analysis Instruction: Count and categorize data sources in the graph
Expected Output: 
- Total data source statistics
- Data source distribution by type
- Data source connectivity analysis
Execution Time: 30-40 seconds
```

### 3. 🔄 Complete Lineage Path Analysis
```
System Prompt: Data Lineage Expert
Analysis Instruction: Analyze complete data flow paths, identify key data hub nodes, and trace the complete path from raw data to final analysis results
Expected Output:
- End-to-end data flow path diagram
- Key data hub node identification
- Data transformation node analysis
- Complete data lineage chain paths
Execution Time: 40-60 seconds
```

### 4. ⚠️ Impact Scope Assessment
```
System Prompt: Data Impact Expert
Analysis Instruction: Assess the impact scope of core data sources. Analyze which downstream systems would be affected if title_basics node changes?
Execution Time: 45-60 seconds
```


## 💡 Usage Tips

### 📝 Best Practices
1. **Query Optimization**: Use specific node names and field names for more accurate results
2. **Step-by-step Analysis**: For complex scenarios, start with basic analysis then dive into specific issues
3. **Template Combination**: Combine different expert templates for multi-perspective analysis
4. **Result Validation**: Validate important analysis results through multiple queries

### 🎯 Query Example Templates
- **Node Query**: "Analyze all properties and connections of [node-name]"
- **Path Tracing**: "Trace the complete data flow path from [source-node] to [target-node]"
- **Impact Analysis**: "If [node/field] changes, which downstream systems would be affected?"
- **Statistical Analysis**: "Count and analyze the distribution of [type] nodes"

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
   # Verify security group inbound rules:
   aws ec2 describe-security-groups --group-ids sg-xxxxxxxxx
   ```

5. **Bedrock access issues**:
   ```bash
   # Test Bedrock access (Claude Sonnet 4 in us-west-2 region)
   aws bedrock list-foundation-models --region us-west-2
   
   # Check IAM permissions
   aws sts get-caller-identity
   
   # Test specific Claude Sonnet 4 model access
   aws bedrock invoke-model --model-id us.anthropic.claude-sonnet-4-20250514-v1:0 --body '{"messages":[{"role":"user","content":"test"}],"max_tokens":10}' --region us-west-2 /tmp/test-output.json
   
   # Verify cross-region access works normally
   aws bedrock get-foundation-model --model-identifier us.anthropic.claude-sonnet-4-20250514-v1:0 --region us-west-2
   ```

4. **Permission issues**:
   ```bash
   # Create dedicated user for application
   sudo useradd -m neptune-app
   sudo su - neptune-app
   ```

## 📈 Performance Metrics
- **Installation time**: 5-10 minutes
- **Simple queries**: 5-15 seconds
- **Medium queries**: 15-30 seconds
- **Complex queries**: 30-60 seconds
- **Timeout threshold**: 60 seconds automatic termination issues**:
   ```bash
   # Test Bedrock access (Claude Sonnet 4 is in us-west-2)
   aws bedrock list-foundation-models --region us-west-2
   
   # Check IAM permissions
   aws sts get-caller-identity
   
   # Test specific Claude Sonnet 4 model access
   aws bedrock invoke-model --model-id us.anthropic.claude-sonnet-4-20250514-v1:0 --body '{"messages":[{"role":"user","content":"test"}],"max_tokens":10}' --region us-west-2 /tmp/test-output.json
   
   # Verify cross-region access works
   aws bedrock get-foundation-model --model-identifier us.anthropic.claude-sonnet-4-20250514-v1:0 --region us-west-2
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

