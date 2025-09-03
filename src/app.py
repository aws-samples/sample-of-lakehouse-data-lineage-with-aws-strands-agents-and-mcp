import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Ensure AWS region is set
if not os.getenv('AWS_DEFAULT_REGION'):
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
if not os.getenv('AWS_REGION'):
    os.environ['AWS_REGION'] = 'us-west-2'

import streamlit as st
from strands import Agent
import json
import time
from datetime import datetime

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

def check_neptune_connection():
    """Check Neptune connection status"""
    try:
        from awslabs.amazon_neptune_mcp_server.server import get_status
        status = get_status()
        return True, status
    except Exception as e:
        return False, str(e)

def get_mcp_client():
    """Get or create MCP client with connection reuse"""
    if st.session_state.mcp_client is None:
        try:
            from mcp import stdio_client, StdioServerParameters
            from strands.tools.mcp import MCPClient
            
            # Create Neptune MCP client with timeout
            st.session_state.mcp_client = MCPClient(lambda: stdio_client(
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
        except Exception as e:
            st.error(f"MCP客户端初始化失败: {str(e)}")
            return None
    
    return st.session_state.mcp_client

def main():
    # Header
    st.markdown('<div class="main-header">🔍 Lakehouse E2E data lineage with AWS Strands agents and MCP</div>', unsafe_allow_html=True)
    
    # Check Neptune connection
    if st.session_state.neptune_status is None:
        with st.spinner("检查Neptune连接状态..."):
            connected, status = check_neptune_connection()
            st.session_state.neptune_status = {"connected": connected, "status": status}
    
    # Sidebar for system configuration and monitoring
    with st.sidebar:
        st.header("⚙️ 系统配置")
        
        # Environment status
        st.subheader("环境状态")
        aws_region = os.getenv('AWS_DEFAULT_REGION', 'Not Set')
        neptune_endpoint = os.getenv('NEPTUNE_ENDPOINT', 'Not Set')
        
        st.write(f"**AWS Region:** {aws_region}")
        st.write(f"**Neptune Endpoint:** {neptune_endpoint[:50]}...") if len(neptune_endpoint) > 50 else st.write(f"**Neptune Endpoint:** {neptune_endpoint}")
        
        # Neptune connection status
        st.subheader("Neptune连接状态")
        if st.session_state.neptune_status:
            if st.session_state.neptune_status["connected"]:
                st.success(f"✅ 连接正常: {st.session_state.neptune_status['status']}")
            else:
                st.error(f"❌ 连接失败: {st.session_state.neptune_status['status'][:100]}...")
        
        if st.button("🔄 重新检查连接"):
            st.session_state.neptune_status = None
            st.session_state.mcp_client = None  # Reset MCP client
            st.rerun()
        
        # System Prompt Section (Collapsible)
        with st.expander("🎭 系统提示词", expanded=False):
            # Predefined system prompts
            system_prompt_templates = {
                "自定义": "",
                "数据血缘分析专家": "你是数据血缘分析专家，使用Neptune图数据库分析数据流向和依赖关系。请提供简洁明确的分析结果。",
                "S3数据源分析专家": "你是S3数据源分析专家，识别和分类所有S3数据源。请提供结构化的分析报告。",
                "数据影响分析专家": "你是数据影响分析专家，评估数据变更的下游影响。请重点关注关键风险点。",
                "数据治理专家": "你是数据治理专家，提供数据管理和质量改进建议。请提供可操作的建议。",
                "图数据库架构师": "你是图数据库架构师，分析Neptune图的模式和结构。请提供技术架构分析。"
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
            
            # Store custom prompt
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

    # Main content area - Single column for user instruction
    st.header("💬 数据血缘分析")
    
    # Timeout warning
    st.markdown("""
    <div class="timeout-warning">
        ⏱️ <strong>性能提示</strong>: 复杂查询可能需要30-60秒，请耐心等待。如果超过2分钟无响应，请刷新页面重试。
    </div>
    """, unsafe_allow_html=True)
    
    # User instruction area (full width)
    st.subheader("📝 分析指令")
    
    # Simplified instruction templates for better performance
    instruction_templates = {
        "连接状态检查": "检查Neptune图数据库的连接状态",
        "图模式概览": "获取图数据库的基本模式信息",
        "数据源统计": "统计图中的数据源数量和类型",
        "关键节点识别": "识别图中连接度最高的关键节点",
        "简单血缘分析": "分析主要的数据流关系",
        "基础影响评估": "评估核心数据源的影响范围"
    }
    
    # Template selection
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
        help="描述您希望进行的具体分析任务（建议使用简单明确的指令）"
    )
    
    # Action buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("🔍 执行分析", type="primary"):
            # Get system prompt from sidebar
            system_prompt = st.session_state.get('system_prompt_input', '')
            if system_prompt.strip() and user_instruction.strip():
                if st.session_state.neptune_status and st.session_state.neptune_status["connected"]:
                    asyncio.run(execute_analysis_async(system_prompt, user_instruction))
                else:
                    st.error("Neptune连接未建立，请先检查连接状态")
            else:
                st.warning("请在左侧边栏设置系统提示词，并输入分析指令")
    
    with col2:
        if st.button("⏹️ 停止分析"):
            # This is a UI hint, actual stopping would require more complex implementation
            st.warning("请刷新页面停止当前分析")
    
    with col3:
        if st.button("🗑️ 清空结果"):
            st.session_state.analysis_results = None
            st.rerun()
    
    # Results display
    st.header("📊 分析结果")
    if 'analysis_results' in st.session_state and st.session_state.analysis_results:
        # Display results with proper formatting
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

async def execute_analysis_async(system_prompt, user_instruction):
    """Execute analysis with timeout and error handling"""
    try:
        # Add tool call record
        call_record = {
            'tool': 'strands_agent_final',
            'status': 'running',
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'instruction': user_instruction
        }
        st.session_state.tool_calls.append(call_record)
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("正在执行分析..."):
            start_time = time.time()
            
            try:
                # Update progress
                progress_bar.progress(10)
                status_text.text("初始化MCP客户端...")
                
                # Get MCP client
                mcp_client = get_mcp_client()
                if mcp_client is None:
                    raise Exception("MCP客户端初始化失败")
                
                progress_bar.progress(30)
                status_text.text("连接Neptune数据库...")
                
                # Use MCP client context with timeout
                async def run_with_timeout():
                    with mcp_client:
                        tools = mcp_client.list_tools_sync()
                        
                        progress_bar.progress(50)
                        status_text.text("创建分析Agent...")
                        
                        # Initialize agent with user's system prompt
                        agent = Agent(
                            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
                            tools=tools,
                            system_prompt=system_prompt + " 请提供简洁明确的分析结果，避免过于详细的技术细节。"
                        )
                        
                        progress_bar.progress(70)
                        status_text.text("执行数据分析...")
                        
                        # Execute analysis with simplified instruction
                        simplified_instruction = f"请简要{user_instruction}，重点关注关键信息。"
                        result = agent(simplified_instruction)
                        
                        return result
                
                # Run with timeout (60 seconds)
                result = await asyncio.wait_for(run_with_timeout(), timeout=60.0)
                
                progress_bar.progress(100)
                status_text.text("分析完成！")
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Update call record
                call_record['status'] = 'success'
                call_record['duration'] = duration
                
                # Extract result content properly
                result_content = str(result) if hasattr(result, '__str__') else "分析完成"
                
                # Store results
                st.session_state.analysis_results = result_content
                
                # Add to history
                st.session_state.query_history.append({
                    'system_prompt': system_prompt,
                    'instruction': user_instruction,
                    'result': result_content,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': duration
                })
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                st.success(f"分析执行成功！耗时 {duration:.2f} 秒")
                st.rerun()
                
            except asyncio.TimeoutError:
                progress_bar.empty()
                status_text.empty()
                call_record['status'] = 'timeout'
                st.error("⏱️ 分析超时（60秒），请尝试简化查询指令或刷新页面重试")
                st.session_state.analysis_results = "**超时错误**: 查询执行时间超过60秒，请尝试使用更简单的分析指令。"
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                call_record['status'] = 'error'
                call_record['error'] = str(e)
                st.error(f"分析执行失败: {str(e)}")
                st.session_state.analysis_results = f"**错误:** {str(e)}"
                
    except Exception as e:
        st.error(f"系统错误: {str(e)}")

if __name__ == "__main__":
    main()
