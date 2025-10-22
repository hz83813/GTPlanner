"""
Agent Function Calling工具包装器

将现有的子Agent节点直接包装为OpenAI Function Calling工具，
保持现有流程逻辑不变，只是提供Function Calling接口。
"""


from typing import Dict, List, Any, Optional

# 导入现有的子Agent流程
from agent.subflows.short_planning.flows.short_planning_flow import ShortPlanningFlow
from agent.subflows.research.flows.research_flow import ResearchFlow
# DesignFlow 在 _execute_design 中动态导入


def get_agent_function_definitions() -> List[Dict[str, Any]]:
    """
    获取所有Agent工具的Function Calling定义

    Returns:
        OpenAI Function Calling格式的工具定义列表
    """
    # 检查JINA_API_KEY是否可用
    from utils.config_manager import get_jina_api_key
    import os

    jina_api_key = get_jina_api_key() or os.getenv("JINA_API_KEY")
    # 确保API密钥不为空且不是占位符
    has_jina_api_key = bool(jina_api_key and jina_api_key.strip() and not jina_api_key.startswith("@format"))

    # 基础工具定义
    tools = [
        {
            "type": "function",
            "function": {
                "name": "short_planning",
                "description": "定义和细化项目范围的核心工具，支持两个阶段的规划：\n1. **初始规划阶段** (planning_stage='initial')：专注于需求分析和功能定义，不涉及技术选型\n2. **技术规划阶段** (planning_stage='technical')：在调用工具推荐后，整合推荐的技术栈和工具选择\n\n此工具旨在根据用户反馈被**重复调用**，直到与用户就项目范围达成最终共识。当用户提出修改意见时，应使用`improvement_points`参数来更新范围。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_requirements": {
                            "type": "string",
                            "description": "用户的原始需求描述或新的需求补充"
                        },
                        "improvement_points": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "需要改进的点或新的需求"
                        },
                        "planning_stage": {
                            "type": "string",
                            "enum": ["initial", "technical"],
                            "description": "规划阶段：'initial'表示初始需求规划阶段，不涉及技术选型；'technical'表示技术规划阶段，需要整合推荐的技术栈和工具"
                        }
                    },
                    "required": ["user_requirements"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "tool_recommend",
                "description": "『技术实现』阶段的**第一步**。基于在『范围确认』阶段已达成共识的项目范围，为项目推荐平台支持的API或库。它是`research`工具的**强制前置步骤**。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "查询文本，描述需要的工具功能或技术需求"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回的推荐工具数量，默认5个",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20
                        },
                        "tool_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["PYTHON_PACKAGE", "APIS"]
                            },
                            "description": "工具类型过滤列表，可选值：PYTHON_PACKAGE（Python包）、APIS（API服务）"
                        },
                        "use_llm_filter": {
                            "type": "boolean",
                            "description": "是否使用大模型筛选，默认true",
                            "default": True
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    # 如果有JINA_API_KEY，添加research工具
    if has_jina_api_key:
        research_tool = {
            "type": "function",
            "function": {
                "name": "research",
                "description": "(可选工具) 用于对`tool_recommend`推荐的技术栈进行深入的可行性或实现方案调研。**必须**在`tool_recommend`成功调用之后才能使用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "需要调研的关键词列表，例如：['rag', '数据库设计']"
                        },
                        "focus_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "调研关注点，例如：['技术选型', '性能优化', '最佳实践', '架构设计']"
                        },
                        "project_context": {
                            "type": "string",
                            "description": "项目背景信息，帮助调研更有针对性"
                        }
                    },
                    "required": ["keywords", "focus_areas"]
                }
            }
        }
        tools.append(research_tool)

    # 添加design工具
    design_tool = {
        "type": "function",
        "function": {
            "name": "design",
            "description": "生成系统设计文档（design.md）。这是一个原子化的工具，所有需要的信息都通过参数显式传入。如果之前调用了 short_planning、tool_recommend 或 research，可以将它们的结果作为可选参数传入，以生成更完善的设计文档。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_requirements": {
                        "type": "string",
                        "description": "用户的项目需求描述（必需）"
                    },
                    "project_planning": {
                        "type": "string",
                        "description": "项目规划内容（可选）。如果之前调用了 short_planning，可以将其结果传入"
                    },
                    "recommended_tools": {
                        "type": "string",
                        "description": "推荐工具信息（可选）。如果之前调用了 tool_recommend，可以将其结果的 JSON 字符串传入"
                    },
                    "research_findings": {
                        "type": "string",
                        "description": "技术调研结果（可选）。如果之前调用了 research，可以将其结果的 JSON 字符串传入"
                    }
                },
                "required": ["user_requirements"]
            }
        }
    }
    tools.append(design_tool)

    return tools


async def execute_agent_tool(tool_name: str, arguments: Dict[str, Any], shared: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    执行Agent工具
    
    Args:
        tool_name: 工具名称
        arguments: 工具参数
        
    Returns:
        工具执行结果
    """
    try:
        # 确保 shared 字典存在
        if shared is None:
            shared = {}

        if tool_name == "short_planning":
            return await _execute_short_planning(arguments, shared)
        elif tool_name == "tool_recommend":
            return await _execute_tool_recommend(arguments, shared)
        elif tool_name == "research":
            return await _execute_research(arguments, shared)
        elif tool_name == "design":
            return await _execute_design(arguments, shared)
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }



async def _execute_short_planning(arguments: Dict[str, Any], shared: Dict[str, Any] = None) -> Dict[str, Any]:
    """执行短期规划 - 基于项目状态和用户需求，支持不同规划阶段"""
    user_requirements = arguments.get("user_requirements", "")
    improvement_points = arguments.get("improvement_points", [])
    planning_stage = arguments.get("planning_stage", "initial")  # 默认为初始阶段

    # 验证planning_stage参数
    if planning_stage not in ["initial", "technical"]:
        return {
            "success": False,
            "error": "planning_stage must be either 'initial' or 'technical'"
        }

    # 从shared字典中获取之前的规划结果
    previous_planning = ""
    if shared and "short_planning" in shared:
        previous_planning_data = shared["short_planning"]
        if isinstance(previous_planning_data, str):
            previous_planning = previous_planning_data

    # 如果是技术规划阶段，检查是否已有工具推荐结果（可选）
    # 注意：tool_recommend 可能返回空结果（没有合适的工具），这是正常情况
    has_tool_recommendations = shared and shared.get("recommended_tools")
    if planning_stage == "technical" and shared:
        # 记录工具推荐状态，但不强制要求
        tool_recommend_status = "已获取工具推荐" if has_tool_recommendations else "未找到合适工具或未调用工具推荐"
        shared["tool_recommend_status"] = tool_recommend_status

    # 如果没有用户需求且没有改进点，但有shared上下文，则可以继续执行
    if not user_requirements and not improvement_points and not shared:
        return {
            "success": False,
            "error": "user_requirements or improvement_points is required when no project context is available"
        }

    try:
        # 直接在shared字典中添加工具参数，避免数据隔离
        if shared is None:
            shared = {}

        # 添加工具参数到shared字典
        shared["user_requirements"] = user_requirements
        shared["previous_planning"] = previous_planning
        shared["improvement_points"] = improvement_points
        shared["planning_stage"] = planning_stage  # 添加规划阶段参数

        # 如果没有明确的用户需求，但有推荐工具，基于现有状态进行规划优化
        if not user_requirements and shared.get("recommended_tools"):
            shared["user_requirements"] = "基于推荐工具优化项目规划"

        # 直接使用shared字典执行流程，确保状态传递
        flow = ShortPlanningFlow()
        result = await flow.run_async(shared)

        # 检查流程是否成功完成（返回"planning_complete"表示成功）
        if result == "planning_complete":
            # 从shared字典中获取结果（PocketFlow已经直接修改了shared）
            short_planning = shared.get("short_planning", {})

            return {
                "success": True,
                "result": short_planning,
                "tool_name": "short_planning"
            }
        else:
            # 流程失败或返回错误
            error_msg = shared.get('planning_error', shared.get('short_planning_flow_error', f"短期规划执行失败，返回值: {result}"))
            return {
                "success": False,
                "error": error_msg,
                "tool_name": "short_planning"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"短期规划执行异常: {str(e)}"
        }


async def _execute_tool_recommend(arguments: Dict[str, Any], shared: Dict[str, Any] = None) -> Dict[str, Any]:
    """执行工具推荐 - 使用智能索引管理器确保索引可用"""
    query = arguments.get("query", "")
    top_k = arguments.get("top_k", 5)
    tool_types = arguments.get("tool_types", [])
    use_llm_filter = arguments.get("use_llm_filter", True)

    # 参数验证
    if not query:
        return {
            "success": False,
            "error": "query is required and cannot be empty"
        }

    try:
        # 1. 使用智能索引管理器确保索引存在
        from agent.utils.tool_index_manager import ensure_tool_index

        # 确保索引存在（智能检测，只在必要时重建）
        index_name = await ensure_tool_index(
            tools_dir="tools",
            force_reindex=False,  # 不强制重建，让管理器智能判断
            shared=shared
        )

        print(f"✅ 索引已就绪: {index_name}")

        # 2. 执行工具推荐
        from agent.nodes.node_tool_recommend import NodeToolRecommend
        recommend_node = NodeToolRecommend()

        # 直接在shared字典中添加工具参数，避免数据隔离
        if shared is None:
            shared = {}

        # 添加工具参数到shared字典
        shared["query"] = query
        shared["top_k"] = top_k
        shared["index_name"] = index_name  # 使用索引管理器返回的索引名
        shared["tool_types"] = tool_types
        shared["min_score"] = 0.1
        shared["use_llm_filter"] = use_llm_filter

        # 执行推荐节点流程（异步），直接使用shared字典
        prep_result = await recommend_node.prep_async(shared)
        if "error" in prep_result:
            return {
                "success": False,
                "error": prep_result["error"]
            }

        exec_result = await recommend_node.exec_async(prep_result)

        # 后处理：结果会直接写入shared字典
        await recommend_node.post_async(shared, prep_result, exec_result)

        return {
            "success": True,
            "result": {
                "recommended_tools": exec_result["recommended_tools"],
                "total_found": exec_result["total_found"],
                "search_time_ms": exec_result["search_time"],
                "query_used": exec_result["query_used"],
                "index_name": index_name
            },
            "tool_name": "tool_recommend"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"工具推荐执行异常: {str(e)}"
        }


async def _execute_research(arguments: Dict[str, Any], shared: Dict[str, Any] = None) -> Dict[str, Any]:
    """执行技术调研 - 使用ResearchFlow"""
    # 检查JINA_API_KEY环境变量
    from utils.config_manager import get_jina_api_key
    import os

    jina_api_key = get_jina_api_key() or os.getenv("JINA_API_KEY")
    # 确保API密钥不为空且不是占位符
    if not jina_api_key or not jina_api_key.strip() or jina_api_key.startswith("@format"):
        return {
            "success": False,
            "error": "❌ Research工具未启用：缺少JINA_API_KEY环境变量。请设置JINA_API_KEY后重试。",
            "tool_name": "research",
            "disabled_reason": "missing_jina_api_key"
        }

    keywords = arguments.get("keywords", [])
    focus_areas = arguments.get("focus_areas", [])
    project_context = arguments.get("project_context", "")

    # 参数验证
    if not keywords:
        return {
            "success": False,
            "error": "keywords is required and cannot be empty"
        }

    if not focus_areas:
        return {
            "success": False,
            "error": "focus_areas is required and cannot be empty"
        }

    try:
        # 使用完整的ResearchFlow
     

        # 直接在shared字典中添加工具参数，避免数据隔离
        if shared is None:
            shared = {}

        # 添加工具参数到shared字典
        shared["research_keywords"] = keywords
        shared["focus_areas"] = focus_areas
        shared["project_context"] = project_context

        # 直接使用shared字典执行流程，确保状态传递
        flow = ResearchFlow()
        success = await flow.run_async(shared)

        if success:
            # 从shared字典中获取结果（PocketFlow已经直接修改了shared）
            research_findings = shared.get("research_findings", {})

            return {
                "success": True,
                "result": research_findings,
                "tool_name": "research",
                "keywords_processed": len(keywords),
                "focus_areas": focus_areas
            }
        else:
            error_msg = shared.get('research_error', "研究流程执行失败")
            return {
                "success": False,
                "error": error_msg,
                "tool_name": "research"
            }

    except Exception as e:
        print(f"❌ 技术调研执行失败: {e}")
        return {
            "success": False,
            "error": f"Research execution failed: {str(e)}"
        }





async def _execute_design(arguments: Dict[str, Any], shared: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    执行设计 - 原子化工具，所有参数显式传入
    
    参数：
    - user_requirements: 必需，用户需求描述
    - project_planning: 可选，项目规划内容（如果之前调用了 short_planning）
    - recommended_tools: 可选，推荐工具信息（JSON 字符串）
    - research_findings: 可选，技术调研结果（JSON 字符串）
    """
    import json
    
    # 验证必需参数
    user_requirements = arguments.get("user_requirements")
    if not user_requirements:
        return {
            "success": False,
            "error": "user_requirements is required"
        }
    
    # 获取可选参数（显式传入，不从 shared 读取）
    project_planning = arguments.get("project_planning", "")
    recommended_tools_str = arguments.get("recommended_tools", "")
    research_findings_str = arguments.get("research_findings", "")
    
    # 解析 JSON 字符串
    recommended_tools = []
    if recommended_tools_str:
        try:
            recommended_tools = json.loads(recommended_tools_str)
        except:
            pass
    
    research_findings = {}
    if research_findings_str:
        try:
            research_findings = json.loads(research_findings_str)
        except:
            pass
    
    try:
        # 创建独立的流程 shared 字典（不污染全局 shared）
        flow_shared = {
            "user_requirements": user_requirements,
            "short_planning": project_planning,  # 向后兼容字段名
            "recommended_tools": recommended_tools,
            "research_findings": research_findings,
            "language": shared.get("language") if shared else None,  # 保留全局配置
            "streaming_session": shared.get("streaming_session") if shared else None  # 🔑 关键：传递 streaming_session
        }
        
        # 使用新的统一 DesignFlow
        from agent.subflows.design.flows.design_flow import DesignFlow
        flow = DesignFlow()
        
        print("🎨 生成设计文档...")
        
        # 执行流程
        result = await flow.run_async(flow_shared)
        
        # 从流程 shared 中获取结果
        agent_design_document = flow_shared.get("agent_design_document", "")
        
        # 如果全局 shared 存在，将结果同步回去（供后续使用）
        if shared:
            shared["agent_design_document"] = agent_design_document
            shared["documentation"] = agent_design_document
        
        # 判断成功
        if result and agent_design_document:
            return {
                "success": True,
                "message": "✅ 设计文档生成成功",
                "document": agent_design_document,
                "tool_name": "design"
            }
        else:
            error_msg = flow_shared.get('design_flow_error') or "设计文档生成失败：未生成文档"
            return {
                "success": False,
                "error": error_msg
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"设计执行异常: {str(e)}"
        }


def get_tool_by_name(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    根据名称获取工具定义
    
    Args:
        tool_name: 工具名称
        
    Returns:
        工具定义或None
    """
    tools = get_agent_function_definitions()
    for tool in tools:
        if tool["function"]["name"] == tool_name:
            return tool
    return None


def validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证工具参数
    
    Args:
        tool_name: 工具名称
        arguments: 参数字典
        
    Returns:
        验证结果 {"valid": bool, "errors": List[str]}
    """
    tool_def = get_tool_by_name(tool_name)
    if not tool_def:
        return {"valid": False, "errors": [f"Unknown tool: {tool_name}"]}
    
    errors = []
    required_params = tool_def["function"]["parameters"].get("required", [])
    
    # 检查必需参数
    for param in required_params:
        if param not in arguments:
            errors.append(f"Missing required parameter: {param}")
    
    return {"valid": len(errors) == 0, "errors": errors}


# 便捷函数
async def call_short_planning(
    user_requirements: str = "",
    improvement_points: List[str] = None,
    planning_stage: str = "initial"
) -> Dict[str, Any]:
    """便捷的短期规划调用 - 自动使用项目状态中的数据

    Args:
        user_requirements: 用户需求描述
        improvement_points: 改进点列表
        planning_stage: 规划阶段，'initial'或'technical'
    """
    arguments = {}
    if user_requirements:
        arguments["user_requirements"] = user_requirements
    if improvement_points:
        arguments["improvement_points"] = improvement_points
    if planning_stage:
        arguments["planning_stage"] = planning_stage

    return await execute_agent_tool("short_planning", arguments)


async def call_research(keywords: List[str], focus_areas: List[str], project_context: str = "") -> Dict[str, Any]:
    """便捷的技术调研调用 - 基于关键词和关注点"""
    return await execute_agent_tool("research", {
        "keywords": keywords,
        "focus_areas": focus_areas,
        "project_context": project_context
    })


async def call_tool_recommend(
    query: str,
    top_k: int = 5,
    tool_types: List[str] = None,
    use_llm_filter: bool = True
) -> Dict[str, Any]:
    """便捷的工具推荐调用"""
    arguments = {
        "query": query,
        "top_k": top_k,
        "use_llm_filter": use_llm_filter
    }
    if tool_types:
        arguments["tool_types"] = tool_types

    return await execute_agent_tool("tool_recommend", arguments)


async def call_design(
    user_requirements: str,
    project_planning: str = None,
    recommended_tools: str = None,
    research_findings: str = None
) -> Dict[str, Any]:
    """便捷的设计文档生成调用 - 原子化工具

    Args:
        user_requirements: 用户需求描述（必需）
        project_planning: 项目规划内容（可选）
        recommended_tools: 推荐工具信息 JSON 字符串（可选）
        research_findings: 技术调研结果 JSON 字符串（可选）
    """
    arguments = {"user_requirements": user_requirements}
    if project_planning:
        arguments["project_planning"] = project_planning
    if recommended_tools:
        arguments["recommended_tools"] = recommended_tools
    if research_findings:
        arguments["research_findings"] = research_findings
    return await execute_agent_tool("design", arguments)
