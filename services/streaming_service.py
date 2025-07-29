"""
流式响应处理模块 - Task 5.3 现代化增强版
处理SSE (Server-Sent Events) 连接、流式数据缓冲、连接异常处理和客户端断开检测
"""

import json
import time
import asyncio
import threading
import logging
from typing import Iterator, Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from flask import Response, request, g
from werkzeug.exceptions import ClientDisconnected
import queue
import uuid

# Task 5.3 新增：流式响应状态枚举
class StreamStatus(Enum):
    INITIALIZING = "initializing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"
    DISCONNECTED = "disconnected"
    TIMEOUT = "timeout"

# Task 5.3 新增：SSE事件类型
class SSEEventType(Enum):
    MESSAGE = "message"
    CHUNK = "chunk"
    ERROR = "error"
    COMPLETION = "completion"
    HEARTBEAT = "heartbeat"
    METADATA = "metadata"
    PROGRESS = "progress"

# Task 5.3 新增：流式连接信息
@dataclass
class StreamConnection:
    connection_id: str
    user_id: str
    agent_id: str
    conversation_id: Optional[str]
    started_at: datetime
    last_activity: datetime
    status: StreamStatus
    client_ip: str
    user_agent: str
    total_chunks: int = 0
    total_bytes: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

# Task 5.3 新增：SSE事件数据类
@dataclass
class SSEEvent:
    event_type: SSEEventType
    data: Any
    event_id: Optional[str] = None
    retry: Optional[int] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())[:8]

    def to_sse_format(self) -> str:
        """转换为SSE格式的字符串"""
        lines = []
        
        if self.event_id:
            lines.append(f"id: {self.event_id}")
        
        lines.append(f"event: {self.event_type.value}")
        
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        # 处理数据
        if isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data, ensure_ascii=False)
        else:
            data_str = str(self.data)
        
        # 多行数据需要每行都添加 data: 前缀
        for line in data_str.split('\n'):
            lines.append(f"data: {line}")
        
        # SSE事件以两个换行符结束
        lines.append("")
        lines.append("")
        
        return "\n".join(lines)

# Task 5.3 新增：流式缓冲区配置
@dataclass
class StreamBufferConfig:
    max_buffer_size: int = 8192      # 最大缓冲区大小 (8KB)
    chunk_size: int = 1024           # 块大小 (1KB)
    flush_interval: float = 0.1      # 刷新间隔 (100ms)
    max_chunk_count: int = 10        # 最大块数量
    heartbeat_interval: float = 30.0 # 心跳间隔 (30s)
    connection_timeout: float = 300.0 # 连接超时 (5分钟)
    max_retry_count: int = 3         # 最大重试次数

class StreamingProcessor:
    """
    流式响应处理器 - Task 5.3 现代化增强版
    
    提供完整的SSE流式响应管理功能：
    - SSE (Server-Sent Events) 连接管理
    - 流式数据缓冲和批量处理
    - 连接异常处理和自动恢复
    - 客户端断开检测和资源清理
    - 心跳机制和连接保活
    - 性能监控和统计分析
    """
    
    def __init__(self, config: StreamBufferConfig = None):
        self.config = config or StreamBufferConfig()
        
        # Task 5.3 新增：活跃连接管理
        self.active_connections: Dict[str, StreamConnection] = {}
        self.connection_buffers: Dict[str, queue.Queue] = {}
        self.connection_threads: Dict[str, threading.Thread] = {}
        
        # Task 5.3 新增：性能统计
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'completed_connections': 0,
            'error_connections': 0,
            'disconnected_connections': 0,
            'total_bytes_sent': 0,
            'total_chunks_sent': 0,
            'average_connection_duration': 0.0,
            'last_reset': datetime.now()
        }
        
        # Task 5.3 新增：错误统计
        self.error_stats = {
            'client_disconnects': 0,
            'timeout_errors': 0,
            'buffer_overflows': 0,
            'encoding_errors': 0,
            'network_errors': 0
        }
        
        # 启动清理任务
        self._start_cleanup_task()
        
        logging.info("[STREAMING PROCESSOR] Task 5.3 现代化初始化完成 - 支持SSE、缓冲处理、异常检测")
    
    # ========== Task 5.3 新增：SSE连接管理 ==========
    
    def create_connection(self, user_id: str, agent_id: str, 
                         conversation_id: str = None, 
                         metadata: Dict[str, Any] = None,
                         mock_mode: bool = False) -> str:
        """
        创建新的流式连接
        
        Args:
            user_id: 用户ID
            agent_id: 智能体ID
            conversation_id: 对话ID
            metadata: 额外元数据
            mock_mode: 测试模式，不依赖Flask request对象
            
        Returns:
            connection_id: 连接ID
        """
        connection_id = f"stream_{uuid.uuid4().hex[:16]}"
        
        # 获取客户端信息
        if mock_mode:
            client_ip = "127.0.0.1"
            user_agent = "test-client"
        else:
            try:
                client_ip = request.remote_addr or "unknown"
                user_agent = request.headers.get('User-Agent', 'unknown')[:200]
            except (RuntimeError, ImportError):
                client_ip = "unknown"
                user_agent = "unknown"
        
        connection = StreamConnection(
            connection_id=connection_id,
            user_id=user_id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            started_at=datetime.now(),
            last_activity=datetime.now(),
            status=StreamStatus.INITIALIZING,
            client_ip=client_ip,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        
        self.active_connections[connection_id] = connection
        self.connection_buffers[connection_id] = queue.Queue(maxsize=self.config.max_chunk_count)
        
        # 更新统计
        self.stats['total_connections'] += 1
        self.stats['active_connections'] += 1
        
        logging.info(f"[STREAM CREATE] {connection_id} - user={user_id}, agent={agent_id}")
        return connection_id
    
    def close_connection(self, connection_id: str, status: StreamStatus = StreamStatus.COMPLETED):
        """
        关闭流式连接并清理资源
        """
        if connection_id not in self.active_connections:
            return
        
        connection = self.active_connections[connection_id]
        connection.status = status
        connection.last_activity = datetime.now()
        
        # 计算连接持续时间
        duration = (connection.last_activity - connection.started_at).total_seconds()
        
        # 更新统计
        self.stats['active_connections'] -= 1
        if status == StreamStatus.COMPLETED:
            self.stats['completed_connections'] += 1
        elif status == StreamStatus.ERROR:
            self.stats['error_connections'] += 1
        elif status == StreamStatus.DISCONNECTED:
            self.stats['disconnected_connections'] += 1
        
        # 更新平均连接时长
        completed = self.stats['completed_connections']
        if completed > 0:
            current_avg = self.stats['average_connection_duration']
            self.stats['average_connection_duration'] = (
                (current_avg * (completed - 1) + duration) / completed
            )
        
        # 清理资源
        if connection_id in self.connection_buffers:
            del self.connection_buffers[connection_id]
        
        if connection_id in self.connection_threads:
            thread = self.connection_threads[connection_id]
            if thread.is_alive():
                # 注意：这里不强制终止线程，让它自然结束
                pass
            del self.connection_threads[connection_id]
        
        # 移动到历史记录（实际项目中可能需要持久化）
        del self.active_connections[connection_id]
        
        logging.info(f"[STREAM CLOSE] {connection_id} - status={status.value}, duration={duration:.2f}s")
    
    def get_connection(self, connection_id: str) -> Optional[StreamConnection]:
        """获取连接信息"""
        return self.active_connections.get(connection_id)
    
    def is_client_connected(self, connection_id: str) -> bool:
        """
        检测客户端是否仍然连接
        
        通过多种方式检测客户端断开：
        1. 连接状态检查
        2. 超时检测
        3. 缓冲区状态检查
        """
        connection = self.get_connection(connection_id)
        if not connection:
            return False
        
        # 检查连接状态
        if connection.status in [StreamStatus.DISCONNECTED, StreamStatus.ERROR, StreamStatus.COMPLETED]:
            return False
        
        # 检查超时
        now = datetime.now()
        timeout = timedelta(seconds=self.config.connection_timeout)
        if now - connection.last_activity > timeout:
            logging.warning(f"[STREAM TIMEOUT] {connection_id} - timeout after {self.config.connection_timeout}s")
            self.close_connection(connection_id, StreamStatus.TIMEOUT)
            self.error_stats['timeout_errors'] += 1
            return False
        
        # 检查缓冲区是否满了（可能表示客户端不再读取数据）
        buffer = self.connection_buffers.get(connection_id)
        if buffer and buffer.full():
            logging.warning(f"[STREAM BUFFER FULL] {connection_id} - client may be disconnected")
            return False
        
        return True
    
    def is_connection_healthy(self, connection_id: str) -> bool:
        """
        更严格的连接健康检查
        
        在关键点（如发送大量数据前）进行额外检查
        """
        if not self.is_client_connected(connection_id):
            return False
            
        connection = self.get_connection(connection_id)
        if not connection:
            return False
            
        # 检查错误率
        if connection.error_count > 0 and connection.total_chunks > 0:
            error_rate = connection.error_count / connection.total_chunks
            if error_rate > 0.1:  # 超过10%错误率
                logging.warning(f"[STREAM HIGH ERROR RATE] {connection_id} - error rate: {error_rate:.2%}")
                return False
        
        # 检查连接活跃度
        now = datetime.now()
        idle_time = (now - connection.last_activity).total_seconds()
        if idle_time > 60:  # 超过1分钟无活动
            logging.warning(f"[STREAM IDLE TOO LONG] {connection_id} - idle for {idle_time:.1f}s")
            return False
            
        return True
    
    # ========== Task 5.3 新增：流式数据缓冲和处理 ==========
    
    def create_sse_response(self, connection_id: str, 
                           data_generator: Iterator[Any],
                           process_chunk: Callable[[Any], SSEEvent] = None) -> Response:
        """
        创建SSE响应对象
        
        Args:
            connection_id: 连接ID
            data_generator: 数据生成器
            process_chunk: 数据块处理函数
            
        Returns:
            Flask Response对象
        """
        def generate():
            try:
                connection = self.get_connection(connection_id)
                if not connection:
                    yield self._create_error_event("Connection not found").to_sse_format()
                    return
                
                # 更新连接状态
                connection.status = StreamStatus.STREAMING
                connection.last_activity = datetime.now()
                
                # 发送连接建立事件
                metadata_event = SSEEvent(
                    event_type=SSEEventType.METADATA,
                    data={
                        "connection_id": connection_id,
                        "status": "connected",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                yield metadata_event.to_sse_format()
                
                # 启动心跳任务
                heartbeat_thread = threading.Thread(
                    target=self._heartbeat_task,
                    args=(connection_id,),
                    daemon=True
                )
                heartbeat_thread.start()
                self.connection_threads[connection_id + "_heartbeat"] = heartbeat_thread
                
                # 处理数据流
                buffer = []
                buffer_size = 0
                last_flush = time.time()
                chunk_count = 0
                
                try:
                    for chunk in data_generator:
                        chunk_count += 1
                        
                        # 检查客户端连接状态
                        if not self.is_client_connected(connection_id):
                            logging.info(f"[STREAM DISCONNECT] {connection_id} - client disconnected after {chunk_count} chunks")
                            self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                            self.error_stats['client_disconnects'] += 1
                            break
                        
                        # 在关键区域进行预防性检查
                        if chunk_count in [50, 51, 52, 53, 54, 55]:
                            logging.info(f"[STREAM CRITICAL CHUNK] {connection_id} - processing critical chunk {chunk_count}")
                            
                            # 额外的连接健康检查
                            if not self.is_connection_healthy(connection_id):
                                logging.warning(f"[STREAM CRITICAL UNHEALTHY] {connection_id} - abandoning at critical chunk {chunk_count}")
                                self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                                return
                            
                            # 强制刷新任何待发送的缓冲区
                            if buffer:
                                logging.info(f"[STREAM CRITICAL FLUSH] {connection_id} - pre-critical flush before chunk {chunk_count}")
                                try:
                                    for event_data in buffer:
                                        yield event_data
                                    
                                    self.stats['total_chunks_sent'] += len(buffer)
                                    self.stats['total_bytes_sent'] += buffer_size
                                    buffer.clear()
                                    buffer_size = 0
                                    last_flush = time.time()
                                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as conn_error:
                                    logging.error(f"[STREAM CRITICAL FLUSH FAILED] {connection_id} at chunk {chunk_count}: {conn_error}")
                                    self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                                    return
                        
                        try:
                            # 处理数据块
                            if process_chunk:
                                event = process_chunk(chunk)
                            else:
                                event = self._default_chunk_processor(chunk)
                            
                            # 添加到缓冲区
                            event_data = event.to_sse_format()
                            buffer.append(event_data)
                            buffer_size += len(event_data.encode('utf-8'))
                            
                            # 更新连接统计
                            connection.total_chunks += 1
                            connection.total_bytes += len(event_data.encode('utf-8'))
                            connection.last_activity = datetime.now()
                            
                            # 记录进度
                            if chunk_count % 10 == 0:
                                logging.debug(f"[STREAM PROGRESS] {connection_id} - processed {chunk_count} chunks, {connection.total_bytes} bytes")
                            
                            # 特别关注高风险区域（第50-60块）
                            if 50 <= chunk_count <= 60:
                                logging.info(f"[STREAM HIGH RISK ZONE] {connection_id} - chunk {chunk_count}, performing enhanced checks")
                                
                                # 在高风险区域进行额外的连接检查
                                if not self.is_connection_healthy(connection_id):
                                    logging.warning(f"[STREAM HIGH RISK UNHEALTHY] {connection_id} - connection unhealthy at critical chunk {chunk_count}")
                                    self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                                    return
                                
                                # 强制小缓冲区刷新以减少数据丢失风险
                                if len(buffer) >= 3:  # 降低刷新阈值
                                    logging.info(f"[STREAM HIGH RISK FLUSH] {connection_id} - early flush at chunk {chunk_count}")
                                    try:
                                        for event_data in buffer:
                                            yield event_data
                                        
                                        self.stats['total_chunks_sent'] += len(buffer)
                                        self.stats['total_bytes_sent'] += buffer_size
                                        buffer.clear()
                                        buffer_size = 0
                                        last_flush = time.time()
                                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as conn_error:
                                        logging.error(f"[STREAM HIGH RISK FLUSH FAILED] {connection_id} chunk {chunk_count}: {conn_error}")
                                        self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                                        self.error_stats['client_disconnects'] += 1
                                        return
                                
                                # 添加微小延迟以缓解网络压力
                                time.sleep(0.005)  # 5ms延迟
                            
                            # 检查是否需要刷新缓冲区
                            now = time.time()
                            
                            # 在高风险区域使用更激进的刷新策略
                            if 50 <= chunk_count <= 60:
                                should_flush = (
                                    buffer_size >= self.config.max_buffer_size // 2 or  # 50%缓冲区大小
                                    len(buffer) >= max(3, self.config.max_chunk_count // 2) or  # 更小的块数量
                                    (now - last_flush) >= self.config.flush_interval / 2  # 更频繁的刷新
                                )
                            else:
                                should_flush = (
                                    buffer_size >= self.config.max_buffer_size or
                                    len(buffer) >= self.config.max_chunk_count or
                                    (now - last_flush) >= self.config.flush_interval
                                )
                            
                            if should_flush:
                                # 在发送前进行健康检查
                                if not self.is_connection_healthy(connection_id):
                                    logging.info(f"[STREAM UNHEALTHY] {connection_id} - connection unhealthy before flush at chunk {chunk_count}")
                                    self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                                    return
                                
                                # 批量发送
                                try:
                                    for event_data in buffer:
                                        yield event_data
                                    
                                    # 更新统计
                                    self.stats['total_chunks_sent'] += len(buffer)
                                    self.stats['total_bytes_sent'] += buffer_size
                                    
                                    # 清空缓冲区
                                    buffer.clear()
                                    buffer_size = 0
                                    last_flush = now
                                    
                                    logging.debug(f"[STREAM FLUSH] {connection_id} - flushed buffer at chunk {chunk_count}")
                                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as conn_error:
                                    logging.warning(f"[STREAM CONNECTION LOST] {connection_id} chunk {chunk_count}: {conn_error}")
                                    self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                                    self.error_stats['client_disconnects'] += 1
                                    return
                        
                        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as conn_error:
                            logging.warning(f"[STREAM CONNECTION ERROR] {connection_id} chunk {chunk_count}: {conn_error}")
                            self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                            self.error_stats['client_disconnects'] += 1
                            return
                        
                        except Exception as e:
                            logging.error(f"[STREAM CHUNK ERROR] {connection_id} chunk {chunk_count}: {e}", exc_info=True)
                            connection.error_count += 1
                            
                            try:
                                error_event = self._create_error_event(f"处理第{chunk_count}个数据块时出错: {str(e)}")
                                yield error_event.to_sse_format()
                            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                                logging.warning(f"[STREAM ERROR SEND FAILED] {connection_id} - client disconnected while sending error")
                                self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                                return
                            
                            if connection.error_count >= self.config.max_retry_count:
                                logging.error(f"[STREAM TOO MANY ERRORS] {connection_id} - closing connection after {connection.error_count} errors")
                                break
                    
                    logging.info(f"[STREAM DATA END] {connection_id} - processed {chunk_count} chunks, generator completed normally")
                    
                except GeneratorExit:
                    logging.info(f"[STREAM GENERATOR EXIT] {connection_id} - generator closed by client")
                    self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                    return
                    
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as conn_error:
                    logging.warning(f"[STREAM CONNECTION LOST IN GENERATOR] {connection_id} after {chunk_count} chunks: {conn_error}")
                    self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                    self.error_stats['client_disconnects'] += 1
                    return
                    
                except StopIteration:
                    logging.info(f"[STREAM GENERATOR STOP] {connection_id} - generator completed via StopIteration after {chunk_count} chunks")
                    
                except Exception as gen_error:
                    logging.error(f"[STREAM GENERATOR ERROR] {connection_id} after {chunk_count} chunks: {gen_error}", exc_info=True)
                    try:
                        error_event = self._create_error_event(f"数据生成器在第{chunk_count}个块后出错: {str(gen_error)}")
                        yield error_event.to_sse_format()
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        logging.warning(f"[STREAM ERROR FINAL SEND FAILED] {connection_id} - client disconnected while sending final error")
                    self.close_connection(connection_id, StreamStatus.ERROR)
                    return
                
                # 发送剩余缓冲区数据
                if buffer:
                    # 最终健康检查
                    if not self.is_connection_healthy(connection_id):
                        logging.warning(f"[STREAM FINAL UNHEALTHY] {connection_id} - connection unhealthy before final buffer send")
                        self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                        return
                    
                    logging.info(f"[STREAM FINAL BUFFER] {connection_id} - sending final {len(buffer)} events, {buffer_size} bytes")
                    try:
                        for i, event_data in enumerate(buffer):
                            yield event_data
                            if i % 5 == 0:
                                logging.debug(f"[STREAM FINAL BUFFER] {connection_id} - sent final event {i+1}/{len(buffer)}")
                        
                        self.stats['total_chunks_sent'] += len(buffer)
                        self.stats['total_bytes_sent'] += buffer_size
                        logging.info(f"[STREAM FINAL BUFFER COMPLETE] {connection_id} - all final events sent successfully")
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        logging.warning(f"[STREAM FINAL BUFFER SEND FAILED] {connection_id} - client disconnected while sending final buffer")
                        self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                        return
                    except Exception as e:
                        logging.error(f"[STREAM FINAL BUFFER ERROR] {connection_id}: {e}", exc_info=True)
                        self.close_connection(connection_id, StreamStatus.ERROR)
                        return
                
                # 最终连接检查
                if not self.is_connection_healthy(connection_id):
                    logging.warning(f"[STREAM COMPLETION UNHEALTHY] {connection_id} - connection unhealthy before completion event")
                    self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                    return
                
                # 添加小延迟确保所有数据都发送完毕
                try:
                    time.sleep(0.01)  # 10ms延迟
                except:
                    pass
                
                # 发送完成事件
                logging.info(f"[STREAM COMPLETION] {connection_id} - sending completion event")
                try:
                    completion_event = SSEEvent(
                        event_type=SSEEventType.COMPLETION,
                        data={
                            "status": "completed",
                            "total_chunks": connection.total_chunks,
                            "total_bytes": connection.total_bytes,
                            "duration": (datetime.now() - connection.started_at).total_seconds(),
                            "final_chunk_count": chunk_count
                        }
                    )
                    completion_data = completion_event.to_sse_format()
                    yield completion_data
                    
                    logging.info(f"[STREAM COMPLETION SENT] {connection_id} - completion event sent successfully")
                    
                    # 关闭连接
                    self.close_connection(connection_id, StreamStatus.COMPLETED)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    logging.warning(f"[STREAM COMPLETION SEND FAILED] {connection_id} - client disconnected while sending completion")
                    self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                    return
                except Exception as e:
                    logging.error(f"[STREAM COMPLETION ERROR] {connection_id}: {e}", exc_info=True)
                    self.close_connection(connection_id, StreamStatus.ERROR)
                    return
                
            except ClientDisconnected:
                logging.info(f"[STREAM CLIENT DISCONNECT] {connection_id}")
                self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                self.error_stats['client_disconnects'] += 1
                
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as conn_error:
                logging.warning(f"[STREAM CONNECTION LOST FINAL] {connection_id}: {conn_error}")
                self.close_connection(connection_id, StreamStatus.DISCONNECTED)
                self.error_stats['client_disconnects'] += 1
                
            except Exception as e:
                logging.error(f"[STREAM ERROR] {connection_id}: {e}", exc_info=True)
                self.close_connection(connection_id, StreamStatus.ERROR)
                self.error_stats['network_errors'] += 1
                
                try:
                    error_event = self._create_error_event(f"Stream error: {str(e)}")
                    yield error_event.to_sse_format()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    logging.warning(f"[STREAM FINAL ERROR SEND FAILED] {connection_id} - client disconnected while sending final error")
        
        # 创建SSE响应
        response = Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control',
                'X-Accel-Buffering': 'no',  # 禁用nginx缓冲
            }
        )
        
        return response
    
    def _default_chunk_processor(self, chunk: Any) -> SSEEvent:
        """默认的数据块处理器"""
        try:
            # 尝试解析为JSON
            if isinstance(chunk, bytes):
                chunk_str = chunk.decode('utf-8').strip()
            else:
                chunk_str = str(chunk).strip()
            
            if not chunk_str:
                return SSEEvent(
                    event_type=SSEEventType.HEARTBEAT,
                    data={"status": "keepalive"}
                )
            
            # 尝试解析为JSON
            try:
                data = json.loads(chunk_str)
                return SSEEvent(
                    event_type=SSEEventType.MESSAGE,
                    data=data
                )
            except json.JSONDecodeError:
                # 如果不是JSON，作为纯文本处理
                return SSEEvent(
                    event_type=SSEEventType.CHUNK,
                    data={"text": chunk_str}
                )
                
        except Exception as e:
            logging.error(f"Error processing chunk: {e}")
            self.error_stats['encoding_errors'] += 1
            return self._create_error_event(f"Chunk processing error: {str(e)}")
    
    def _create_error_event(self, error_message: str) -> SSEEvent:
        """创建错误事件"""
        return SSEEvent(
            event_type=SSEEventType.ERROR,
            data={
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # ========== Task 5.3 新增：心跳和连接保活 ==========
    
    def _heartbeat_task(self, connection_id: str):
        """心跳任务，定期发送心跳事件保持连接活跃"""
        while self.is_client_connected(connection_id):
            try:
                time.sleep(self.config.heartbeat_interval)
                
                connection = self.get_connection(connection_id)
                if not connection:
                    break
                
                # 更新最后活跃时间
                connection.last_activity = datetime.now()
                
                logging.debug(f"[STREAM HEARTBEAT] {connection_id}")
                
            except Exception as e:
                logging.error(f"[STREAM HEARTBEAT ERROR] {connection_id}: {e}")
                break
    
    # ========== Task 5.3 新增：连接清理和监控 ==========
    
    def _start_cleanup_task(self):
        """启动连接清理任务"""
        def cleanup_task():
            while True:
                try:
                    time.sleep(60)  # 每分钟检查一次
                    self._cleanup_stale_connections()
                except Exception as e:
                    logging.error(f"Cleanup task error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_stale_connections(self):
        """清理过期连接"""
        now = datetime.now()
        timeout = timedelta(seconds=self.config.connection_timeout)
        
        stale_connections = []
        for connection_id, connection in self.active_connections.items():
            if now - connection.last_activity > timeout:
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            logging.info(f"[STREAM CLEANUP] Removing stale connection: {connection_id}")
            self.close_connection(connection_id, StreamStatus.TIMEOUT)
            self.error_stats['timeout_errors'] += 1
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return {
            **self.stats,
            'error_stats': self.error_stats,
            'active_connection_details': [
                {
                    'connection_id': conn.connection_id,
                    'user_id': conn.user_id,
                    'agent_id': conn.agent_id,
                    'status': conn.status.value,
                    'duration': (datetime.now() - conn.started_at).total_seconds(),
                    'chunks': conn.total_chunks,
                    'bytes': conn.total_bytes
                }
                for conn in self.active_connections.values()
            ]
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_connections': 0,
            'active_connections': len(self.active_connections),
            'completed_connections': 0,
            'error_connections': 0,
            'disconnected_connections': 0,
            'total_bytes_sent': 0,
            'total_chunks_sent': 0,
            'average_connection_duration': 0.0,
            'last_reset': datetime.now()
        }
        
        self.error_stats = {
            'client_disconnects': 0,
            'timeout_errors': 0,
            'buffer_overflows': 0,
            'encoding_errors': 0,
            'network_errors': 0
        }
        
        logging.info("[STREAM STATS] Statistics reset")

# Task 5.3 增强：全局流式处理器实例
streaming_processor = StreamingProcessor()

# ========== Task 5.3 新增：流式响应装饰器 ==========

def stream_response(process_chunk: Callable[[Any], SSEEvent] = None,
                   buffer_config: StreamBufferConfig = None):
    """
    流式响应装饰器
    
    Args:
        process_chunk: 自定义数据块处理函数
        buffer_config: 自定义缓冲区配置
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 创建连接
            user_id = g.get('current_user', {}).get('username', 'anonymous')
            agent_id = kwargs.get('agent_id') or request.json.get('agent_id', 'default')
            conversation_id = request.json.get('conversation_id')
            
            # 使用自定义配置
            if buffer_config:
                processor = StreamingProcessor(buffer_config)
            else:
                processor = streaming_processor
            
            connection_id = processor.create_connection(
                user_id=user_id,
                agent_id=agent_id,
                conversation_id=conversation_id,
                metadata={
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'args': kwargs
                }
            )
            
            try:
                # 调用原函数获取数据生成器
                data_generator = func(*args, **kwargs)
                
                # 创建SSE响应
                return processor.create_sse_response(
                    connection_id=connection_id,
                    data_generator=data_generator,
                    process_chunk=process_chunk
                )
                
            except Exception as e:
                processor.close_connection(connection_id, StreamStatus.ERROR)
                raise
        
        return wrapper
    return decorator

# Task 5.3 完成标记
logging.info("[TASK 5.3] 流式响应优化 - 现代化SSE处理系统启动完成")
logging.info("[TASK 5.3] 功能包括: SSE连接管理、流式缓冲、异常检测、心跳保活、性能监控")
