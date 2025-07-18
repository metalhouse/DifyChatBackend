"""
聊天相关的API路由 (标准化版本)
"""
from flask import request, jsonify, g, Response
import logging

from utils.response_builder import ResponseBuilder, ErrorCode, PaginationInfo
from utils.request_validator import (
    ChatMessageRequest, ConversationListRequest, ConversationCreateRequest,
    validate_and_convert, ValidationError
)
from auth.decorators import require_auth, require_permissions, check_agent_access, auto_refresh_token
from services.dify_service import dify_service

def _get_current_user():
    """获取当前用户信息的辅助函数"""
    current_user = getattr(g, 'current_user', None)
    if not current_user:
        return None, ResponseBuilder.error(
            error_code=ErrorCode.AUTHENTICATION_REQUIRED,
            message="用户认证信息缺失"
        )
    return current_user, None

@require_auth()
@require_permissions(['access_agents'])
@auto_refresh_token()
def api_agents():
    """获取用户可用智能体列表"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 解析查询参数
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        
        # 3. 获取智能体列表
        agents = dify_service.get_user_agents(username, use_cache=use_cache)
        
        # 4. 应用过滤条件
        if search:
            agents = [
                agent for agent in agents 
                if search.lower() in agent.get('name', '').lower() 
                or search.lower() in agent.get('description', '').lower()
            ]
        
        if category:
            agents = [
                agent for agent in agents 
                if agent.get('category', '').lower() == category.lower()
            ]
        
        # 5. 分页处理
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 20)), 100)  # 限制最大页面大小
        
        total = len(agents)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_agents = agents[start_idx:end_idx]
        
        # 6. 构建分页信息
        pagination = PaginationInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size
        )
        
        logging.info(f"[GET AGENTS] user={username}, count={len(paginated_agents)}/{total}")
        
        return ResponseBuilder.success(
            data=paginated_agents,
            message="获取智能体列表成功",
            pagination=pagination
        )
        
    except Exception as e:
        logging.error(f"[GET AGENTS ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取智能体列表异常"
        )

@require_auth()
@require_permissions(['view_conversations'])
@auto_refresh_token()
def api_conversations():
    """获取会话列表（支持缓存）"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 请求验证
        try:
            request_data = {
                'page': request.args.get('page', 1),
                'page_size': request.args.get('page_size', 20),
                'agent_id': request.args.get('agent_id'),
                'search': request.args.get('search')
            }
            conversation_request = validate_and_convert(request_data, ConversationListRequest)
        except ValidationError as e:
            return ResponseBuilder.validation_error(e.errors)
        
        # 3. 检查智能体访问权限
        if conversation_request.agent_id:
            # 使用装饰器检查智能体访问权限
            @check_agent_access('agent_id')
            def _check_access():
                return True
            
            try:
                g.request_args = {'agent_id': conversation_request.agent_id}
                _check_access()
            except Exception:
                return ResponseBuilder.error(
                    error_code=ErrorCode.ACCESS_DENIED,
                    message="无权访问指定智能体"
                )
        
        # 4. 构建请求参数
        params = {
            'user': username,
            'last_id': request.args.get('last_id'),
            'limit': conversation_request.page_size,
            'sort_by': request.args.get('sort_by'),
        }
        params = {k: v for k, v in params.items() if v is not None}
        
        # 5. 检查是否使用缓存
        use_cache = request.args.get('no_cache', '').lower() not in ('true', '1', 'yes')
        
        # 6. 获取对话列表
        resp, status = dify_service.get_conversations(
            username=username, 
            agent_id=conversation_request.agent_id, 
            params=params, 
            use_cache=use_cache
        )
        
        # 7. 处理响应
        if status == 200:
            # Dify API成功响应，直接使用data字段
            conversations = resp.get('data', [])
            
            # 应用搜索过滤
            if conversation_request.search:
                search_term = conversation_request.search.lower()
                conversations = [
                    conv for conv in conversations
                    if search_term in conv.get('name', '').lower()
                    or search_term in conv.get('summary', '').lower()
                ]
            
            # 构建分页信息
            pagination = PaginationInfo(
                page=conversation_request.page,
                page_size=conversation_request.page_size,
                total=len(conversations),
                total_pages=(len(conversations) + conversation_request.page_size - 1) // conversation_request.page_size
            )
            
            logging.info(f"[GET CONVERSATIONS] user={username}, agent={conversation_request.agent_id}, "
                        f"count={len(conversations)}")
            
            return ResponseBuilder.success(
                data=conversations,
                message="获取对话列表成功",
                pagination=pagination
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '获取对话列表失败')
            )
        
    except Exception as e:
        logging.error(f"[GET CONVERSATIONS ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取对话列表异常"
        )

@require_auth()
@require_permissions(['send_messages'])
@auto_refresh_token()
def api_chat():
    """发送对话消息（发送后清除缓存）"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 请求验证
        try:
            chat_request = validate_and_convert(request.get_json(), ChatMessageRequest)
        except ValidationError as e:
            return ResponseBuilder.validation_error(e.errors)
        
        # 3. 检查智能体访问权限
        @check_agent_access('agent_id')
        def _check_access():
            return True
        
        try:
            g.request_args = {'agent_id': chat_request.agent_id}
            _check_access()
        except Exception:
            return ResponseBuilder.error(
                error_code=ErrorCode.ACCESS_DENIED,
                message="无权访问指定智能体"
            )
        
        # 4. 构建请求负载
        payload = {
            'query': chat_request.message,
            'inputs': chat_request.inputs or {},
            'response_mode': 'streaming' if chat_request.stream else 'blocking',
            'user': username,
            'conversation_id': chat_request.conversation_id,
            'files': chat_request.files,
            'auto_generate_name': chat_request.auto_generate_name
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        
        # 5. 发送消息
        if chat_request.stream:
            # 流式响应
            def stream():
                try:
                    resp, _ = dify_service.make_request(
                        'POST', '/chat-messages', json_data=payload, 
                        stream=True, agent_id=chat_request.agent_id
                    )
                    
                    for line in resp.iter_lines():
                        if line:
                            yield line + b'\n'
                finally:
                    # 清除用户对话缓存
                    dify_service.invalidate_user_cache(username, chat_request.agent_id)
                    logging.info(f"[CHAT STREAM] user={username}, agent={chat_request.agent_id} - 缓存已清除")
                    
            return Response(stream(), content_type='text/event-stream')
        else:
            # 阻塞式响应
            resp, status = dify_service.make_request(
                'POST', '/chat-messages', json_data=payload, agent_id=chat_request.agent_id
            )
            
            # 6. 处理响应
            if status == 200:
                # 清除相关缓存
                dify_service.invalidate_user_cache(username, chat_request.agent_id)
                
                logging.info(f"[CHAT SUCCESS] user={username}, agent={chat_request.agent_id}")
                
                return ResponseBuilder.success(
                    data=resp,
                    message="消息发送成功"
                )
            else:
                error_code = ErrorCode.EXTERNAL_SERVICE_ERROR
                if status == 400:
                    error_code = ErrorCode.INVALID_REQUEST
                elif status == 401:
                    error_code = ErrorCode.AUTHENTICATION_FAILED
                elif status == 403:
                    error_code = ErrorCode.ACCESS_DENIED
                elif status == 429:
                    error_code = ErrorCode.RATE_LIMITED
                
                return ResponseBuilder.error(
                    error_code=error_code,
                    message=resp.get('message', '消息发送失败')
                )
        
    except Exception as e:
        logging.error(f"[CHAT ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="消息发送异常"
        )

@require_auth()
@require_permissions(['create_conversations'])
@auto_refresh_token()
def api_create_conversation():
    """创建新对话"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 请求验证
        try:
            conversation_request = validate_and_convert(request.get_json(), ConversationCreateRequest)
        except ValidationError as e:
            return ResponseBuilder.validation_error(e.errors)
        
        # 3. 检查智能体访问权限
        @check_agent_access('agent_id')
        def _check_access():
            return True
        
        try:
            g.request_args = {'agent_id': conversation_request.agent_id}
            _check_access()
        except Exception:
            return ResponseBuilder.error(
                error_code=ErrorCode.ACCESS_DENIED,
                message="无权访问指定智能体"
            )
        
        # 4. 创建对话逻辑（这里需要根据实际Dify API实现）
        # 当前假设通过发送第一条消息来创建对话
        payload = {
            'query': conversation_request.first_message,
            'inputs': conversation_request.inputs or {},
            'response_mode': 'blocking',
            'user': username,
            'auto_generate_name': True
        }
        
        resp, status = dify_service.make_request(
            'POST', '/chat-messages', json_data=payload, agent_id=conversation_request.agent_id
        )
        
        # 5. 处理响应
        if status == 200:
            # 清除相关缓存
            dify_service.invalidate_user_cache(username, conversation_request.agent_id)
            
            logging.info(f"[CREATE CONVERSATION] user={username}, agent={conversation_request.agent_id}")
            
            return ResponseBuilder.success(
                data=resp,
                message="对话创建成功"
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '对话创建失败')
            )
        
    except Exception as e:
        logging.error(f"[CREATE CONVERSATION ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="对话创建异常"
        )
