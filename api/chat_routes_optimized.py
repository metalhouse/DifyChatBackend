"""
Dify聊天流式响应优化版本
基于Dify API文档标准，减少检查点，确保流式传输完整性
"""
from flask import request, jsonify, Response, stream_with_context
import logging
import json
import time
import uuid
import requests
from typing import Iterator, Dict, Any

def create_optimized_chat_stream():
    """
    优化的流式聊天处理 - 基于Dify API文档
    
    主要优化：
    1. 严格按照Dify API文档参数格式
    2. 最小化连接检查，避免中断
    3. 直接转发SSE事件，不做过度处理
    4. 增加容错机制
    """
    
    def optimized_chat_messages():
        """发送聊天消息 - Dify API标准版本"""
        try:
            # 1. 解析请求数据
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body is required'}), 400
            
            # 2. 按照Dify API文档验证必需参数
            query = data.get('query')
            user = data.get('user') 
            
            if not query:
                return jsonify({'error': 'query parameter is required'}), 400
            if not user:
                return jsonify({'error': 'user parameter is required'}), 400
            
            # 3. 构建符合Dify API的请求载荷
            payload = {
                'query': query,
                'user': user,
                'inputs': data.get('inputs', {}),
                'response_mode': data.get('response_mode', 'streaming'),
                'conversation_id': data.get('conversation_id', ''),
                'files': data.get('files', []),
                'auto_generate_name': data.get('auto_generate_name', True)
            }
            
            # 移除空值（符合API最佳实践）
            payload = {k: v for k, v in payload.items() if v is not None and v != ''}
            
            # 4. 处理流式响应
            if payload.get('response_mode') == 'streaming':
                return handle_streaming_response(payload, user)
            else:
                return handle_blocking_response(payload, user)
                
        except Exception as e:
            logging.error(f"Chat message error: {str(e)}")
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
    def handle_streaming_response(payload: Dict[str, Any], user: str) -> Response:
        """
        处理流式响应 - 优化版本
        
        关键优化：
        1. 最小化中间处理
        2. 直接转发Dify的SSE事件
        3. 只在绝对必要时检查连接
        4. 增强错误恢复
        """
        
        def generate_stream():
            stream_id = f"stream_{uuid.uuid4().hex[:12]}"
            chunk_count = 0
            total_bytes = 0
            last_ping_time = time.time()
            dify_response = None
            
            try:
                logging.info(f"[STREAM START] {stream_id} - user={user}")
                
                # 1. 调用Dify API - 使用适当的超时设置
                dify_response = requests.post(
                    url="https://api.dify.ai/v1/chat-messages",  # 需要替换为实际的Dify API端点
                    headers={
                        'Authorization': 'Bearer YOUR_API_KEY',  # 需要替换为实际的API密钥
                        'Content-Type': 'application/json'
                    },
                    json=payload,
                    stream=True,
                    timeout=(30, None)  # 连接超时30秒，读取无超时
                )
                
                if dify_response.status_code != 200:
                    error_msg = f"Dify API error: {dify_response.status_code}"
                    try:
                        error_data = dify_response.json()
                        error_msg = error_data.get('message', error_msg)
                    except:
                        pass
                    
                    # 发送错误事件
                    error_event = {
                        'event': 'error',
                        'data': json.dumps({
                            'status': dify_response.status_code,
                            'message': error_msg,
                            'code': 'dify_api_error'
                        })
                    }
                    yield f"event: {error_event['event']}\\ndata: {error_event['data']}\\n\\n"
                    return
                
                logging.info(f"[STREAM CONNECTED] {stream_id} - Dify API connected successfully")
                
                # 2. 处理流式数据 - 直接转发，最小化处理
                for line in dify_response.iter_lines(decode_unicode=True):
                    if line:
                        chunk_count += 1
                        total_bytes += len(line.encode('utf-8'))
                        
                        # 最少的日志记录，避免影响性能
                        if chunk_count % 20 == 0:  # 每20个chunk记录一次
                            logging.debug(f"[STREAM PROGRESS] {stream_id} - {chunk_count} chunks, {total_bytes} bytes")
                        
                        # 直接转发整行数据，保持Dify的原始格式
                        yield f"{line}\\n"
                        
                        # 简单的事件类型识别（用于日志，不影响转发）
                        if 'event: message_end' in line:
                            logging.info(f"[STREAM END] {stream_id} - message completed")
                        elif 'event: error' in line:
                            logging.warning(f"[STREAM ERROR EVENT] {stream_id} - Dify reported error")
                        
                        # 更新最后接收数据时间
                        last_ping_time = time.time()
                    
                    # 只在长时间无数据时检查连接（避免频繁检查）
                    current_time = time.time()
                    if current_time - last_ping_time > 60:  # 1分钟无数据才检查
                        try:
                            # 简单的客户端连接检查
                            if hasattr(request, 'stream') and hasattr(request.stream, 'closed'):
                                if request.stream.closed:
                                    logging.info(f"[STREAM CLIENT DISCONNECT] {stream_id}")
                                    break
                        except:
                            pass  # 忽略检查错误，继续处理
                        
                        last_ping_time = current_time
                
                # 3. 流结束处理
                logging.info(f"[STREAM COMPLETE] {stream_id} - total: {chunk_count} chunks, {total_bytes} bytes")
                
            except requests.exceptions.Timeout as e:
                logging.error(f"[STREAM TIMEOUT] {stream_id}: {str(e)}")
                timeout_event = {
                    'event': 'error',
                    'data': json.dumps({
                        'message': 'Request timeout - AI processing took too long',
                        'code': 'timeout_error'
                    })
                }
                yield f"event: {timeout_event['event']}\\ndata: {timeout_event['data']}\\n\\n"
                
            except requests.exceptions.ConnectionError as e:
                logging.error(f"[STREAM CONNECTION ERROR] {stream_id}: {str(e)}")
                conn_error_event = {
                    'event': 'error',
                    'data': json.dumps({
                        'message': 'Connection to AI service failed',
                        'code': 'connection_error'
                    })
                }
                yield f"event: {conn_error_event['event']}\\ndata: {conn_error_event['data']}\\n\\n"
                
            except Exception as e:
                logging.error(f"[STREAM UNEXPECTED ERROR] {stream_id}: {str(e)}")
                general_error_event = {
                    'event': 'error',
                    'data': json.dumps({
                        'message': f'Unexpected error: {str(e)}',
                        'code': 'general_error'
                    })
                }
                yield f"event: {general_error_event['event']}\\ndata: {general_error_event['data']}\\n\\n"
                
            finally:
                # 4. 清理资源
                if dify_response:
                    try:
                        dify_response.close()
                        logging.debug(f"[STREAM CLEANUP] {stream_id} - response closed")
                    except:
                        pass
        
        # 5. 创建优化的SSE响应
        response = Response(
            stream_with_context(generate_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',  # 禁用nginx缓冲
                'Access-Control-Allow-Origin': '*',  # 根据需要调整CORS
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )
        
        return response
    
    def handle_blocking_response(payload: Dict[str, Any], user: str) -> Response:
        """处理阻塞式响应"""
        try:
            # 调用Dify API
            response = requests.post(
                url="https://api.dify.ai/v1/chat-messages",  # 需要替换为实际的Dify API端点
                headers={
                    'Authorization': 'Bearer YOUR_API_KEY',  # 需要替换为实际的API密钥
                    'Content-Type': 'application/json'
                },
                json=payload,
                timeout=120  # 阻塞模式2分钟超时
            )
            
            if response.status_code == 200:
                return jsonify(response.json())
            else:
                error_msg = f"Dify API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_msg)
                except:
                    pass
                
                return jsonify({
                    'error': error_msg,
                    'status': response.status_code
                }), response.status_code
                
        except requests.exceptions.Timeout:
            return jsonify({
                'error': 'Request timeout - AI processing took too long',
                'code': 'timeout_error'
            }), 408
            
        except Exception as e:
            return jsonify({
                'error': f'API call failed: {str(e)}',
                'code': 'api_error' 
            }), 500
    
    return optimized_chat_messages

# 示例用法配置
def configure_dify_integration():
    """
    配置Dify集成的示例
    
    在实际使用时需要：
    1. 替换API端点URL
    2. 设置正确的API密钥
    3. 根据需要调整CORS设置
    4. 添加适当的认证中间件
    """
    config = {
        'dify_api_url': 'https://api.dify.ai/v1',  # 替换为实际URL
        'api_key': 'YOUR_DIFY_API_KEY',  # 替换为实际密钥
        'timeout_settings': {
            'connect_timeout': 30,  # 连接超时
            'read_timeout': None,   # 读取超时（流式时无限制）
            'blocking_timeout': 120  # 阻塞模式超时
        },
        'stream_settings': {
            'check_interval': 60,    # 连接检查间隔（秒）
            'log_interval': 20,      # 日志记录间隔（每N个chunk）
            'buffer_size': 8192      # 缓冲区大小
        }
    }
    return config

# 错误码定义（符合Dify API文档）
DIFY_ERROR_CODES = {
    400: {
        'invalid_param': '传入参数异常',
        'app_unavailable': 'App配置不可用', 
        'provider_not_initialize': '无可用模型凭据配置',
        'provider_quota_exceeded': '模型调用额度不足',
        'model_currently_not_support': '当前模型不可用',
        'completion_request_error': '文本生成失败'
    },
    404: '对话不存在',
    500: '服务内部异常'
}
