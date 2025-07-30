import asyncio
from flask import request, jsonify, Response, stream_with_context
from app.services.auth_service import login_required
from app.services.dify_service import DifyService
from app.utils.logger import logger
from . import chat_bp
import time
import uuid

@chat_bp.route('/messages', methods=['POST'])
@login_required
def chat_messages():
    """发送聊天消息"""
    try:
        data = request.get_json()
        user = request.user
        agent_id = data.get('agent_id')
        messages = data.get('messages')
        response_mode = data.get('response_mode', 'streaming')
        
        # 参数校验
        if not agent_id or not messages:
            return jsonify({'error': '缺少必要参数'}), 400
        
        # 日志记录
        logger.info(f"Received chat message request: user={user}, agent={agent_id}, messages={messages}")
        
        dify_service = DifyService()
        payload = {
            "user_id": user,
            "agent_id": agent_id,
            "messages": messages
        }
        
        # 如果是流式响应
        if response_mode == 'streaming':
            def generate():
                stream_id = f"stream_{uuid.uuid4().hex[:20]}"
                buffer = []
                last_flush_time = time.time()
                last_heartbeat_time = time.time()
                chunk_count = 0
                total_bytes = 0
                
                try:
                    logger.info(f"[STREAM CREATE] {stream_id} - user={user}, agent={agent_id}")
                    
                    # 设置较短的超时时间
                    response = dify_service.make_request(
                        'POST', 
                        f'/chat-messages',
                        json=payload,
                        stream=True,
                        timeout=300  # 5分钟超时
                    )
                    
                    logger.info(f"[STREAM START] {stream_id}: 开始流式请求")
                    
                    # 立即发送初始响应
                    yield "data: {}\n\n"
                    
                    for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                        if chunk:
                            chunk_count += 1
                            chunk_size = len(chunk.encode('utf-8'))
                            total_bytes += chunk_size
                            
                            logger.debug(f"[STREAM CHUNK] {stream_id}: chunk {chunk_count}")
                            
                            # 处理原始数据
                            if 'event: ping' in chunk:
                                logger.debug(f"[STREAM RAW TEXT] {stream_id}: event: ping...")
                                # 转发ping事件到前端
                                yield f"data: {chunk}\n\n"
                                last_heartbeat_time = time.time()
                                continue
                            
                            # 添加到缓冲区
                            buffer.append(chunk)
                            
                            # 强制刷新条件
                            current_time = time.time()
                            should_flush = (
                                len(buffer) >= 5 or  # 每5个块刷新
                                (current_time - last_flush_time) > 1.0 or  # 每1秒刷新
                                'event: message_end' in chunk or  # 消息结束
                                'event: error' in chunk  # 错误发生
                            )
                            
                            if should_flush and buffer:
                                content = ''.join(buffer)
                                yield content
                                logger.debug(f"[STREAM FLUSH] {stream_id} - flushed buffer at chunk {chunk_count}")
                                buffer.clear()
                                last_flush_time = current_time
                            
                            # 定期发送心跳
                            if current_time - last_heartbeat_time > 5:  # 每5秒发送心跳
                                heartbeat = "data: {\"event\": \"ping\"}\n\n"
                                yield heartbeat
                                logger.debug(f"[STREAM HEARTBEAT] {stream_id}")
                                last_heartbeat_time = current_time
                            
                            # 进度日志
                            if chunk_count % 10 == 0:
                                logger.debug(f"[STREAM PROGRESS] {stream_id} - processed {chunk_count} chunks, {total_bytes} bytes")
                    
                    # 刷新剩余缓冲区
                    if buffer:
                        content = ''.join(buffer)
                        yield content
                        logger.debug(f"[STREAM FINAL FLUSH] {stream_id} - flushed remaining buffer")
                    
                    logger.info(f"[STREAM COMPLETE] {stream_id} - total chunks: {chunk_count}, bytes: {total_bytes}")
                    
                except Exception as e:
                    logger.error(f"[STREAM ERROR] {stream_id}: {str(e)}")
                    error_msg = {
                        "event": "error",
                        "message": str(e),
                        "code": "stream_error"
                    }
                    yield f"data: {json.dumps(error_msg)}\n\n"
                finally:
                    logger.debug(f"[STREAM CLEANUP] {stream_id}: 响应连接已关闭")
                    # 清理资源
                    dify_service.clear_cache(user, agent_id)
            
            # 返回流式响应，设置正确的响应头
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',  # 禁用nginx缓冲
                    'Connection': 'keep-alive',
                    'Transfer-Encoding': 'chunked'
                }
            )
        
        # 非流式响应逻辑
        else:
            response = dify_service.make_request('POST', '/chat-messages', json=payload)
            return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Chat message error: {str(e)}")
        return jsonify({'error': str(e)}), 500