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


# ========== 新增API端点 ==========

@require_auth()
@require_permissions(['send_messages'])
@auto_refresh_token()
def api_message_feedback(message_id):
    """发送消息反馈（点赞/点踩）"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 获取消息ID
        
        if not message_id:
            return ResponseBuilder.error(
                error_code=ErrorCode.MISSING_PARAMETER,
                message="消息ID是必需的"
            )
        
        # 3. 请求验证
        try:
            from utils.request_validator import MessageFeedbackRequest
            feedback_request = validate_and_convert(request.get_json(), MessageFeedbackRequest)
        except ValidationError as e:
            return ResponseBuilder.validation_error(e.errors)
        
        # 4. 发送反馈
        resp, status = dify_service.send_message_feedback(
            message_id=message_id,
            rating=feedback_request.rating,
            content=feedback_request.content,
            username=username
        )
        
        # 5. 处理响应
        if status == 200:
            logging.info(f"[MESSAGE FEEDBACK] user={username}, message={message_id}, rating={feedback_request.rating}")
            
            return ResponseBuilder.success(
                data=resp,
                message="反馈提交成功"
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '反馈提交失败')
            )
        
    except Exception as e:
        logging.error(f"[MESSAGE FEEDBACK ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="反馈提交异常"
        )


@require_auth()
@require_permissions(['view_conversations'])
@auto_refresh_token()
def api_suggested_questions(message_id):
    """获取下一轮建议问题列表"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 获取消息ID
        
        if not message_id:
            return ResponseBuilder.error(
                error_code=ErrorCode.MISSING_PARAMETER,
                message="消息ID是必需的"
            )
        
        # 3. 获取建议问题
        resp, status = dify_service.get_suggested_questions(
            message_id=message_id,
            username=username
        )
        
        # 4. 处理响应
        if status == 200:
            suggestions = resp.get('data', [])
            
            logging.info(f"[SUGGESTED QUESTIONS] user={username}, message={message_id}, count={len(suggestions)}")
            
            return ResponseBuilder.success(
                data=suggestions,
                message="获取建议问题成功"
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '获取建议问题失败')
            )
        
    except Exception as e:
        logging.error(f"[SUGGESTED QUESTIONS ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取建议问题异常"
        )


@require_auth()
@require_permissions(['delete_conversations'])
@auto_refresh_token()
def api_delete_conversation(conversation_id):
    """删除对话"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 获取对话ID
        
        if not conversation_id:
            return ResponseBuilder.error(
                error_code=ErrorCode.MISSING_PARAMETER,
                message="对话ID是必需的"
            )
        
        # 3. 删除对话
        resp, status = dify_service.delete_conversation(
            conversation_id=conversation_id,
            username=username
        )
        
        # 4. 处理响应
        if status == 204 or status == 200:  # Dify返回204 No Content
            # 清除相关缓存
            dify_service.invalidate_user_cache(username)
            
            logging.info(f"[DELETE CONVERSATION] user={username}, conversation={conversation_id}")
            
            return ResponseBuilder.success(
                message="对话删除成功"
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '对话删除失败')
            )
        
    except Exception as e:
        logging.error(f"[DELETE CONVERSATION ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="对话删除异常"
        )


@require_auth()
@require_permissions(['edit_conversations'])
@auto_refresh_token()
def api_rename_conversation(conversation_id):
    """重命名对话"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 获取对话ID
        
        if not conversation_id:
            return ResponseBuilder.error(
                error_code=ErrorCode.MISSING_PARAMETER,
                message="对话ID是必需的"
            )
        
        # 3. 请求验证
        try:
            from utils.request_validator import ConversationRenameRequest
            rename_request = validate_and_convert(request.get_json(), ConversationRenameRequest)
        except ValidationError as e:
            return ResponseBuilder.validation_error(e.errors)
        
        # 4. 重命名对话
        resp, status = dify_service.rename_conversation(
            conversation_id=conversation_id,
            name=rename_request.name,
            auto_generate=rename_request.auto_generate,
            username=username
        )
        
        # 5. 处理响应
        if status == 200:
            # 清除相关缓存
            dify_service.invalidate_user_cache(username)
            
            logging.info(f"[RENAME CONVERSATION] user={username}, conversation={conversation_id}, "
                        f"name={rename_request.name}, auto={rename_request.auto_generate}")
            
            return ResponseBuilder.success(
                data=resp,
                message="对话重命名成功"
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '对话重命名失败')
            )
        
    except Exception as e:
        logging.error(f"[RENAME CONVERSATION ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="对话重命名异常"
        )


@require_auth()
@require_permissions(['send_messages'])
@auto_refresh_token()
def api_audio_to_text():
    """语音转文字"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 检查文件上传
        if 'file' not in request.files:
            return ResponseBuilder.error(
                error_code=ErrorCode.MISSING_PARAMETER,
                message="音频文件是必需的"
            )
        
        file = request.files['file']
        if file.filename == '':
            return ResponseBuilder.error(
                error_code=ErrorCode.MISSING_PARAMETER,
                message="请选择音频文件"
            )
        
        # 3. 验证文件类型
        allowed_extensions = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm']
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return ResponseBuilder.error(
                error_code=ErrorCode.INVALID_FIELD_VALUE,
                message=f"不支持的音频格式，支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 4. 转换语音
        resp, status = dify_service.audio_to_text(
            file_data=file,
            username=username
        )
        
        # 5. 处理响应
        if status == 200:
            text = resp.get('text', '')
            
            logging.info(f"[AUDIO TO TEXT] user={username}, file={file.filename}, text_length={len(text)}")
            
            return ResponseBuilder.success(
                data={"text": text},
                message="语音转文字成功"
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '语音转文字失败')
            )
        
    except Exception as e:
        logging.error(f"[AUDIO TO TEXT ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="语音转文字异常"
        )


@require_auth()
@require_permissions(['send_messages'])
@auto_refresh_token()
def api_text_to_audio():
    """文字转语音"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 请求验证
        try:
            from utils.request_validator import TextToAudioRequest
            audio_request = validate_and_convert(request.get_json(), TextToAudioRequest)
        except ValidationError as e:
            return ResponseBuilder.validation_error(e.errors)
        
        # 3. 转换语音
        resp, status = dify_service.text_to_audio(
            message_id=audio_request.message_id,
            text=audio_request.text,
            username=username
        )
        
        # 4. 处理响应
        if status == 200:
            logging.info(f"[TEXT TO AUDIO] user={username}, message_id={audio_request.message_id}, "
                        f"text_length={len(audio_request.text or '')}")
            
            # 对于音频响应，我们需要特殊处理
            from flask import Response
            return Response(
                resp,
                mimetype='audio/wav',
                headers={
                    'Content-Disposition': 'attachment; filename=audio.wav'
                }
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '文字转语音失败')
            )
        
    except Exception as e:
        logging.error(f"[TEXT TO AUDIO ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="文字转语音异常"
        )


@require_auth()
@require_permissions(['view_conversations'])
@auto_refresh_token()
def api_messages_history():
    """获取会话历史消息"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 获取查询参数
        conversation_id = request.args.get('conversation_id')
        if not conversation_id:
            return ResponseBuilder.error(
                error_code=ErrorCode.MISSING_PARAMETER,
                message="对话ID是必需的"
            )
        
        first_id = request.args.get('first_id')
        limit = min(int(request.args.get('limit', 20)), 100)  # 限制最大100
        
        # 3. 获取历史消息
        resp, status = dify_service.get_messages_history(
            conversation_id=conversation_id,
            username=username,
            first_id=first_id,
            limit=limit
        )
        
        # 4. 处理响应
        if status == 200:
            messages = resp.get('data', [])
            has_more = resp.get('has_more', False)
            
            logging.info(f"[MESSAGES HISTORY] user={username}, conversation={conversation_id}, "
                        f"count={len(messages)}, has_more={has_more}")
            
            # 构建分页信息
            pagination = PaginationInfo(
                page=1,  # 历史消息使用滚动加载，不是传统分页
                page_size=limit,
                total=len(messages),
                total_pages=1
            )
            pagination.has_next = has_more
            
            return ResponseBuilder.success(
                data=messages,
                message="获取历史消息成功",
                pagination=pagination
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '获取历史消息失败')
            )
        
    except Exception as e:
        logging.error(f"[MESSAGES HISTORY ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取历史消息异常"
        )


@require_auth()
@require_permissions(['view_app_info'])
@auto_refresh_token()
def api_app_info():
    """获取应用基本信息"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        # 2. 获取应用信息
        resp, status = dify_service.get_app_info()
        
        # 3. 处理响应
        if status == 200:
            logging.info(f"[APP INFO] user={current_user['username']}")
            
            return ResponseBuilder.success(
                data=resp,
                message="获取应用信息成功"
            )
        else:
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=resp.get('message', '获取应用信息失败')
            )
        
    except Exception as e:
        logging.error(f"[APP INFO ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取应用信息异常"
        )

@require_auth()
@require_permissions(['send_messages', 'create_conversations'])
@auto_refresh_token()
def api_chat_messages():
    """标准Dify聊天消息API - 创建对话消息"""
    try:
        # 1. 获取当前用户
        current_user, error_response = _get_current_user()
        if error_response:
            return error_response
        
        username = current_user['username']
        
        # 2. 解析请求数据
        try:
            request_data = request.get_json()
            if not request_data:
                return ResponseBuilder.error(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="请求体不能为空"
                )
            
            # 验证必需参数
            query = request_data.get('query')
            if not query:
                return ResponseBuilder.error(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="query参数是必需的"
                )
                
            user = request_data.get('user')
            if not user:
                return ResponseBuilder.error(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="user参数是必需的"
                )
                
            # 可选参数
            inputs = request_data.get('inputs', {})
            response_mode = request_data.get('response_mode', 'blocking')
            conversation_id = request_data.get('conversation_id', '')
            files = request_data.get('files', [])
            auto_generate_name = request_data.get('auto_generate_name', True)
            
        except Exception as e:
            return ResponseBuilder.error(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=f"请求数据解析失败: {str(e)}"
            )
        
        # 3. 调用Dify API
        try:
            resp, status = dify_service.make_request(
                'POST', '/chat-messages', 
                json_data={
                    'query': query,
                    'user': user,
                    'inputs': inputs,
                    'response_mode': response_mode,
                    'conversation_id': conversation_id,
                    'files': files,
                    'auto_generate_name': auto_generate_name
                }, 
                agent_id=None  # 使用默认代理
            )
            
            logging.info(f"[CHAT MESSAGE] Dify response: status={status}, type(resp)={type(resp)}")
            
            if status == 200:
                logging.info(f"[CHAT MESSAGE] user={username}, conversation_id={resp.get('conversation_id', 'new')}")
                
                # 返回标准格式的响应
                response_data = {
                    'event': resp.get('event', 'message'),
                    'task_id': resp.get('task_id', ''),
                    'id': resp.get('id', ''),
                    'message_id': resp.get('message_id', resp.get('id', '')),
                    'conversation_id': resp.get('conversation_id', ''),
                    'mode': resp.get('mode', 'chat'),
                    'answer': resp.get('answer', ''),
                    'metadata': resp.get('metadata', {}),
                    'created_at': resp.get('created_at', 0)
                }
                
                return jsonify(response_data)
            else:
                # 处理错误响应
                error_message = "发送消息失败"
                if isinstance(resp, dict):
                    error_message = resp.get('message', error_message)
                
                return ResponseBuilder.error(
                    error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                    message=error_message
                )
                
        except Exception as e:
            logging.error(f"[CHAT MESSAGE ERROR] {e}", exc_info=True)
            return ResponseBuilder.error(
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                message=f"调用Dify API失败: {str(e)}"
            )
        
    except Exception as e:
        logging.error(f"[CHAT MESSAGE ERROR] {e}", exc_info=True)
        return ResponseBuilder.error(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="发送消息异常"
        )

