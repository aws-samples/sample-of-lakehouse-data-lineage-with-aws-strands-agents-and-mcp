import os
import sys
import asyncio
import uuid
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Ensure AWS region is set
if not os.getenv('AWS_DEFAULT_REGION'):
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
if not os.getenv('AWS_REGION'):
    os.environ['AWS_REGION'] = 'us-west-2'

import streamlit as st
from openai import OpenAI

# Page configuration
st.set_page_config(
    page_title="Lakehouse E2E data lineage with AWS Strands agents and MCP",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .tool-status {
        padding: 0.5rem;
        border-radius: 0.5rem;
        margin: 0.25rem 0;
    }
    .tool-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .tool-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .tool-running {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .timeout-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .sidebar-section {
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'tool_calls' not in st.session_state:
    st.session_state.tool_calls = []
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'neptune_status' not in st.session_state:
    st.session_state.neptune_status = None
if 'mcp_client' not in st.session_state:
    st.session_state.mcp_client = None
if 'qwen_client' not in st.session_state:
    st.session_state.qwen_client = None

def check_neptune_connection():
    """Check Neptune connection status"""
    try:
        neptune_endpoint = os.environ.get('NEPTUNE_ENDPOINT')
        if not neptune_endpoint:
            return False, "NEPTUNE_ENDPOINT 环境变量未设置"
        
        try:
            from awslabs.amazon_neptune_mcp_server.server import get_status
            status = get_status()
            return True, f"Neptune MCP 服务正常: {status}"
        except ImportError:
            return False, "Neptune MCP 服务器模块未安装"
        except Exception as mcp_error:
            return True, f"Neptune 端点已配置，但MCP检查失败: {str(mcp_error)[:50]}..."
    except Exception as e:
        return False, f"连接检查失败: {str(e)}"

def get_mcp_client():
    """Get or create MCP client"""
    try:
        from mcp import stdio_client, StdioServerParameters
        from strands.tools.mcp import MCPClient
        
        mcp_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command="python", 
                args=["-m", "awslabs.amazon_neptune_mcp_server.server"],
                env={
                    'NEPTUNE_ENDPOINT': os.environ.get('NEPTUNE_ENDPOINT'),
                    'AWS_REGION': os.environ.get('AWS_REGION'),
                    'AWS_DEFAULT_REGION': os.environ.get('AWS_DEFAULT_REGION')
                }
            )
        ))
        return mcp_client
    except Exception as e:
        st.error(f"MCP客户端初始化失败: {str(e)}")
        return None

def get_qwen_client():
    """Get or create Qwen API client"""
    if st.session_state.qwen_client is None:
        try:
            api_key = os.getenv('DASHSCOPE_API_KEY')
            if not api_key:
                st.error("请设置环境变量 DASHSCOPE_API_KEY")
                return None
            
            st.session_state.qwen_client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
        except Exception as e:
            st.error(f"Qwen客户端初始化失败: {str(e)}")
            return None
    
    return st.session_state.qwen_client

def create_enhanced_claude_agent(system_prompt, mcp_client):
    """Create enhanced agent with comprehensive data source analysis and impact assessment"""
    try:
        qwen_client = get_qwen_client()
        if not qwen_client:
            raise ValueError("Qwen API客户端初始化失败")
        
        class EnhancedClaudeAgent:
            def __init__(self, qwen_client, mcp_client, system_prompt):
                self.qwen_client = qwen_client
                self.mcp_client = mcp_client
                self.system_prompt = system_prompt
                self.tool_call_log = []
            
            def call_mcp_tool(self, tool_name, arguments=None):
                """Call MCP tool and log the process - backend logging + sidebar monitoring"""
                try:
                    # Backend logging
                    self.tool_call_log.append(f"调用工具: {tool_name}")
                    if arguments:
                        self.tool_call_log.append(f"参数: {arguments}")
                    
                    # Sidebar monitoring - add to session state
                    st.session_state.tool_calls.append({
                        'tool': tool_name,
                        'status': 'running',
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    })
                    
                    result = self.mcp_client.call_tool_sync(
                        tool_use_id=str(uuid.uuid4()),
                        name=tool_name,
                        arguments=arguments or {}
                    )
                    
                    if result.get('status') == 'success':
                        self.tool_call_log.append(f"调用状态: 成功")
                        # Update sidebar status
                        st.session_state.tool_calls[-1]['status'] = 'success'
                        
                        if result.get('content'):
                            content = result['content'][0].get('text', '{}')
                            try:
                                return json.loads(content)
                            except:
                                return content
                    else:
                        self.tool_call_log.append(f"调用状态: 失败 - {result}")
                        # Update sidebar status
                        st.session_state.tool_calls[-1]['status'] = 'error'
                        return None
                        
                except Exception as e:
                    self.tool_call_log.append(f"调用异常: {str(e)}")
                    # Update sidebar status
                    if st.session_state.tool_calls:
                        st.session_state.tool_calls[-1]['status'] = 'error'
                    return None
            
            def execute_comprehensive_analysis(self, user_instruction):
                """Execute comprehensive analysis with enhanced data source detection"""
                self.tool_call_log = []
                analysis_data = {}
                instruction_lower = user_instruction.lower()
                
                # For connection check, ONLY execute get_graph_status - strict matching
                if "连接状态检查" in instruction_lower:
                    self.tool_call_log.append("检测到连接状态检查指令，仅执行get_graph_status")
                    status_result = self.call_mcp_tool('get_graph_status')
                    if status_result:
                        analysis_data['graph_status'] = status_result
                    return analysis_data
                
                # For graph overview, ONLY execute get_graph_status and get_graph_schema - strict matching
                if "图模式概览" in instruction_lower:
                    self.tool_call_log.append("检测到图模式概览指令，仅执行get_graph_status和get_graph_schema")
                    status_result = self.call_mcp_tool('get_graph_status')
                    if status_result:
                        analysis_data['graph_status'] = status_result
                    
                    schema_result = self.call_mcp_tool('get_graph_schema')
                    if schema_result:
                        analysis_data['graph_schema'] = schema_result
                    return analysis_data
                
                # Step 1: Check graph status
                status_result = self.call_mcp_tool('get_graph_status')
                if status_result:
                    analysis_data['graph_status'] = status_result
                
                # Step 2: Get graph schema
                schema_result = self.call_mcp_tool('get_graph_schema')
                if schema_result:
                    analysis_data['graph_schema'] = schema_result
                
                # Step 3: Enhanced data source analysis
                queries = self.get_enhanced_queries(user_instruction)
                
                for query_name, query_info in queries.items():
                    query = query_info['query']
                    query_type = query_info.get('type', 'opencypher')
                    
                    if query_type == 'gremlin':
                        result = self.call_mcp_tool('run_gremlin_query', {'query': query})
                    else:
                        result = self.call_mcp_tool('run_opencypher_query', {'query': query})
                    
                    if result:
                        analysis_data[query_name] = result
                
                return analysis_data
            
            def get_enhanced_queries(self, instruction):
                """Get enhanced queries based on Claude's successful patterns"""
                instruction_lower = instruction.lower()
                queries = {}
                
                # For connection check and graph overview, only return empty queries (status/schema check is handled separately)
                if "连接状态检查" in instruction_lower or "图模式概览" in instruction_lower:
                    return queries
                
                # Basic statistics - using dataset nodes like Claude
                queries['数据集总数'] = {
                    'query': "MATCH (d:dataset) RETURN COUNT(d) AS 数据集总数",
                    'type': 'opencypher'
                }
                
                queries['数据流关系总数'] = {
                    'query': "MATCH ()-[r:data_flow]->() RETURN COUNT(r) AS 数据流关系总数",
                    'type': 'opencypher'
                }
                
                # Include data source analysis for comprehensive results
                queries['数据源系统分布'] = {
                    'query': """MATCH (d:dataset) 
                               RETURN d.source_system as source_system, 
                                      d.dataset_type as dataset_type, 
                                      count(*) as count 
                               ORDER BY source_system, dataset_type""",
                    'type': 'opencypher'
                }
                
                queries['数据源总体统计'] = {
                    'query': """MATCH (d:dataset) 
                               RETURN count(*) as total_datasets, 
                                      count(DISTINCT d.source_system) as source_systems_count,
                                      collect(DISTINCT d.source_system) as source_systems,
                                      collect(DISTINCT d.dataset_type) as dataset_types""",
                    'type': 'opencypher'
                }
                
                # Lineage path analysis - Claude's pattern
                if any(keyword in instruction_lower for keyword in ["血缘", "路径", "流向", "lineage", "追踪"]):
                    queries['所有数据集信息'] = {
                        'query': """MATCH (d:dataset)
                                   RETURN d.node_name, d.dataset_type, d.source_system
                                   ORDER BY d.dataset_type""",
                        'type': 'opencypher'
                    }
                    
                    queries['数据流向关系'] = {
                        'query': """MATCH (source:dataset)-[r:data_flow]->(target:dataset)
                                   RETURN source.node_name as 源数据, 
                                          target.node_name as 目标数据,
                                          r.edge_type as 转换类型""",
                        'type': 'opencypher'
                    }
                    
                    queries['完整血缘路径'] = {
                        'query': """MATCH path = (start:dataset)-[:data_flow*]->(end:dataset)
                                   WHERE NOT ()-[:data_flow]->(start)
                                   RETURN [node in nodes(path) | node.node_name] as 数据路径,
                                          length(path) as 路径长度
                                   ORDER BY 路径长度 DESC""",
                        'type': 'opencypher'
                    }
                
                # Hub node analysis - using Gremlin like Claude
                if any(keyword in instruction_lower for keyword in ["枢纽", "关键", "hub", "key", "识别"]):
                    queries['节点连接度分析'] = {
                        'query': """g.V().hasLabel('dataset')
                                   .project('dataset_name', 'in_degree', 'out_degree', 'total_degree')
                                   .by('node_name')
                                   .by(inE('data_flow').count())
                                   .by(outE('data_flow').count())
                                   .by(bothE('data_flow').count())
                                   .order().by('total_degree', desc).limit(10)""",
                        'type': 'gremlin'
                    }
                
                # Schema analysis for specific nodes
                if any(keyword in instruction_lower for keyword in ["schema", "模式", "字段", "列"]):
                    queries['数据集列信息'] = {
                        'query': """MATCH (d:dataset)-[:has_column]->(c:column) 
                                   RETURN d.node_name as dataset_name, 
                                          c.column_name, 
                                          c.data_type, 
                                          c.nullable 
                                   ORDER BY d.node_name, c.column_name""",
                        'type': 'opencypher'
                    }
                
                # Impact analysis - Claude's approach
                if any(keyword in instruction_lower for keyword in ["影响", "变更", "下游", "impact", "date"]):
                    queries['数据源影响范围'] = {
                        'query': """MATCH (source:dataset)
                                   OPTIONAL MATCH (source)-[:data_flow*1..]->(downstream:dataset)
                                   WITH source, count(DISTINCT downstream) as 下游影响数量
                                   RETURN source.node_name as 核心数据源,
                                          source.dataset_type as 类型,
                                          source.source_system as 源系统,
                                          下游影响数量
                                   ORDER BY 下游影响数量 DESC
                                   LIMIT 10""",
                        'type': 'opencypher'
                    }
                    
                    # Field-level impact analysis for date fields
                    if "date" in instruction_lower:
                        queries['字段级影响分析'] = {
                            'query': """MATCH (source:dataset {node_name: 's3://sales-forecast-demo-new/raw-data/sales_data.csv'})
                                       MATCH (source)-[:data_flow*1..3]->(downstream:dataset)
                                       MATCH (downstream)-[:has_column]->(col:column)
                                       WHERE col.column_name CONTAINS 'date' OR col.column_name CONTAINS 'time' 
                                       RETURN downstream.node_name, col.column_name, col.data_type""",
                            'type': 'opencypher'
                        }
                
                return queries
            
            def __call__(self, user_message):
                try:
                    instruction_lower = user_message.lower()
                    
                    # Execute comprehensive analysis
                    analysis_data = self.execute_comprehensive_analysis(user_message)
                    
                    # For connection check and graph overview, return simple formatted results without MCP process
                    if "连接状态检查" in instruction_lower:
                        return f"""### 📊 连接状态检查结果
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

### 📋 总结
已成功检查Neptune图数据库连接状态。"""
                    
                    if "图模式概览" in instruction_lower:
                        return f"""### 📊 图模式概览结果
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

### 📋 总结
已成功获取图数据库基本模式信息。"""
                    
                    # For other scenarios, use full AI analysis without showing MCP process in frontend
                    analysis_prompt = f"""基于以下查询结果数据，生成专业的数据血缘分析报告：

## 用户需求
{user_message}

## 查询结果数据
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

请按照以下格式生成分析报告：

### 📊 关键统计信息
- 数据集总数和类型分布
- 数据源系统统计
- 数据流关系数量

### 🎯 核心发现
- 数据架构特征
- 关键数据流模式
- 重要节点识别

### 💡 分析洞察
- 数据血缘路径分析
- 影响范围评估（如果相关）
- 风险点识别

### 📋 总结和建议
- 提供简洁的结论
- 给出可操作的建议

请使用中文回复，确保分析的准确性和专业性。不要在分析结果中显示MCP工具调用过程。"""
                    
                    # Call Qwen3-235B
                    response = self.qwen_client.chat.completions.create(
                        model="qwen3-235b-a22b-instruct-2507",
                        messages=[
                            {"role": "system", "content": self.system_prompt + " 请提供专业的数据血缘分析，重点关注数据架构和血缘关系。"},
                            {"role": "user", "content": analysis_prompt}
                        ],
                        temperature=0.7,
                        max_tokens=3000
                    )
                    
                    ai_analysis = response.choices[0].message.content
                    
                    return ai_analysis
                    
                except Exception as e:
                    return f"分析执行失败: {str(e)}"
        
        return EnhancedClaudeAgent(qwen_client, mcp_client, system_prompt)
        
    except Exception as e:
        raise ValueError(f"Agent创建失败: {str(e)}")

def main():
    # Header
    st.markdown('<div class="main-header">🔍 Lakehouse E2E data lineage with AWS Strands agents and MCP</div>', unsafe_allow_html=True)
    
    # Check Neptune connection
    if st.session_state.neptune_status is None:
        with st.spinner("检查Neptune连接状态..."):
            connected, status = check_neptune_connection()
            st.session_state.neptune_status = {"connected": connected, "status": status}
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ 系统配置")
        
        # Environment status
        st.subheader("环境状态")
        aws_region = os.getenv('AWS_DEFAULT_REGION', 'Not Set')
        neptune_endpoint = os.getenv('NEPTUNE_ENDPOINT', 'Not Set')
        dashscope_key = os.getenv('DASHSCOPE_API_KEY', 'Not Set')
        
        st.write(f"**AWS Region:** {aws_region}")
        st.write(f"**Neptune Endpoint:** {neptune_endpoint[:50]}...") if len(neptune_endpoint) > 50 else st.write(f"**Neptune Endpoint:** {neptune_endpoint}")
        st.write(f"**Qwen API Key:** {'sk-***' + dashscope_key[-4:] if dashscope_key != 'Not Set' and len(dashscope_key) > 4 else dashscope_key}")
        
        # Neptune connection status
        st.subheader("Neptune连接状态")
        if st.session_state.neptune_status:
            if st.session_state.neptune_status["connected"]:
                st.success(f"✅ 连接正常: {st.session_state.neptune_status['status']}")
            else:
                st.error(f"❌ 连接失败: {st.session_state.neptune_status['status'][:100]}...")
        
        # System Prompt Section
        with st.expander("🎭 系统提示词", expanded=False):
            system_prompt_templates = {
                "数据血缘分析专家": "你是数据血缘分析专家，使用Neptune图数据库分析数据流向和依赖关系。请提供简洁明确的分析结果，确保完整统计所有数据源类型。",
                "自定义": ""
            }
            
            selected_template = st.selectbox("选择模板", list(system_prompt_templates.keys()))
            
            if selected_template != "自定义":
                default_prompt = system_prompt_templates[selected_template]
            else:
                default_prompt = st.session_state.get('custom_system_prompt', '')
            
            system_prompt = st.text_area(
                "系统提示词内容",
                value=default_prompt,
                height=120,
                help="定义AI助手的角色和专业领域",
                key="system_prompt_input"
            )
            
            if selected_template == "自定义":
                st.session_state.custom_system_prompt = system_prompt
        
        # Tool monitoring
        st.header("📊 工具调用监控")
        if st.session_state.tool_calls:
            for i, call in enumerate(reversed(st.session_state.tool_calls[-5:])):  # Show last 5
                status_class = f"tool-{call['status']}"
                st.markdown(f"""
                <div class="tool-status {status_class}">
                    <strong>{call['tool']}</strong><br>
                    Status: {call['status']}<br>
                    Time: {call['timestamp']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("暂无工具调用记录")
        
        # Performance statistics
        st.header("📈 性能统计")
        if st.session_state.tool_calls:
            total_calls = len(st.session_state.tool_calls)
            successful_calls = len([call for call in st.session_state.tool_calls if call['status'] == 'success'])
            success_rate = (successful_calls / total_calls) * 100 if total_calls > 0 else 0
            
            st.metric("成功率", f"{success_rate:.1f}%")
            st.metric("总调用次数", total_calls)
            st.metric("成功次数", successful_calls)
        else:
            st.info("暂无性能数据")
    
    # Main content area
    st.header("💬 数据血缘分析")
    
    st.markdown("""
    <div class="timeout-warning">
        ⏱️ <strong>性能提示</strong>: 复杂查询可能需要30-60秒，请耐心等待。如果超过2分钟无响应，请刷新页面重试。
    </div>
    """, unsafe_allow_html=True)
    
    # User instruction area
    st.subheader("📝 分析指令")
    
    # Updated instruction templates based on Claude's scenarios
    instruction_templates = {
        "数据源统计": "统计图中的数据源数量和类型",
        "数据血缘追踪": "追踪从原始数据到最终分析结果的完整路径",
        "关键枢纽节点识别": "识别关键的数据枢纽节点",
        "数据源影响范围评估": "评估核心数据源的影响范围",
        "字段级影响分析": "如果raw-data/sales_data.csv的date发生变更，会影响哪些下游系统的哪些字段.",
        "数据治理建议": "基于数据血缘分析，提供数据治理建议：1. 数据质量监控点建议 2. 关键数据资产保护策略 3. 数据血缘文档化建议 4. 合规性检查要点",
        "完整血缘分析报告": "生成完整的数据血缘分析报告，包括执行摘要、数据架构概览、关键发现和洞察、风险评估、改进建议"
    }
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_instruction_template = st.selectbox("选择分析模板", list(instruction_templates.keys()))
    
    with col2:
        if st.button("📋 使用模板"):
            st.session_state.user_instruction = instruction_templates[selected_instruction_template]
    
    user_instruction = st.text_area(
        "分析指令内容",
        value=st.session_state.get('user_instruction', instruction_templates[selected_instruction_template]),
        height=120,
        help="描述您希望进行的具体分析任务"
    )
    
    # Action buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("🔍 执行分析", type="primary"):
            system_prompt = st.session_state.get('system_prompt_input', '')
            if system_prompt.strip() and user_instruction.strip():
                if st.session_state.neptune_status and st.session_state.neptune_status["connected"]:
                    qwen_client = get_qwen_client()
                    if qwen_client:
                        asyncio.run(execute_enhanced_analysis(system_prompt, user_instruction))
                    else:
                        st.error("Qwen API客户端未初始化，请检查DASHSCOPE_API_KEY环境变量")
                else:
                    st.error("Neptune连接未建立，请先检查连接状态")
            else:
                st.warning("请在左侧边栏设置系统提示词，并输入分析指令")
    
    with col2:
        if st.button("🔄 清理会话"):
            st.session_state.mcp_client = None
            if 'analysis_results' in st.session_state:
                del st.session_state.analysis_results
            st.success("会话已清理")
            st.rerun()
    
    with col3:
        if st.button("🗑️ 清空结果"):
            st.session_state.analysis_results = None
            st.rerun()
    
    # Results display
    st.header("📊 分析结果")
    if 'analysis_results' in st.session_state and st.session_state.analysis_results:
        st.markdown(st.session_state.analysis_results)
    else:
        st.info("暂无分析结果，请执行分析以查看结果。")
    
    # Query history
    if st.session_state.query_history:
        with st.expander("📚 查询历史"):
            for i, query in enumerate(reversed(st.session_state.query_history[-5:])):
                st.write(f"**{query['timestamp']}** - 耗时: {query['duration']:.2f}秒")
                st.write(f"系统提示词: {query.get('system_prompt', 'N/A')[:50]}...")
                st.write(f"指令: {query['instruction'][:100]}...")
                if query['duration'] > 30:
                    st.write("⚠️ 查询时间较长")
                st.divider()

async def execute_enhanced_analysis(system_prompt, user_instruction):
    """Execute enhanced analysis with comprehensive data source detection"""
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("正在执行优化分析..."):
            start_time = time.time()
            
            try:
                progress_bar.progress(10)
                status_text.text("初始化MCP客户端...")
                
                mcp_client = get_mcp_client()
                if mcp_client is None:
                    raise Exception("MCP客户端初始化失败")
                
                progress_bar.progress(30)
                status_text.text("创建优化Agent...")
                
                async def run_enhanced_analysis():
                    with mcp_client:
                        agent = create_enhanced_claude_agent(
                            system_prompt=system_prompt,
                            mcp_client=mcp_client
                        )
                        
                        progress_bar.progress(50)
                        status_text.text("执行优化MCP工具调用序列...")
                        
                        result = agent(user_instruction)
                        return result
                
                result = await asyncio.wait_for(run_enhanced_analysis(), timeout=120.0)
                
                progress_bar.progress(100)
                status_text.text("分析完成！")
                
                end_time = time.time()
                duration = end_time - start_time
                
                st.session_state.analysis_results = str(result)
                
                # Add to history
                st.session_state.query_history.append({
                    'system_prompt': system_prompt,
                    'instruction': user_instruction,
                    'result': str(result),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': duration
                })
                
                progress_bar.empty()
                status_text.empty()
                
                st.success(f"优化分析执行成功！耗时 {duration:.2f} 秒")
                st.rerun()
                
            except asyncio.TimeoutError:
                progress_bar.empty()
                status_text.empty()
                st.error("⏱️ 分析超时（120秒），请尝试简化查询指令")
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"分析执行失败: {str(e)}")
                
    except Exception as e:
        st.error(f"系统错误: {str(e)}")

if __name__ == "__main__":
    main()
