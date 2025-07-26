"""
聊天室消息加密服务
实现AES256-GCM加密和完整性验证
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class MessageCrypto:
    """消息加密处理类"""
    
    @staticmethod
    def verify_message_hash(content: str, timestamp: str, user_id: str, provided_hash: str) -> bool:
        """
        验证消息完整性
        
        Args:
            content: 消息内容
            timestamp: 时间戳
            user_id: 用户ID
            provided_hash: 提供的哈希值
            
        Returns:
            bool: 是否验证通过
        """
        try:
            # 构造待验证的数据
            data = f"{content}|{timestamp}|{user_id}"
            
            # 计算SHA256哈希
            calculated_hash = hashlib.sha256(data.encode('utf-8')).hexdigest()
            
            # 对比哈希值
            return calculated_hash == provided_hash
            
        except Exception as e:
            logger.error(f"消息完整性验证失败: {e}")
            return False
    
    @staticmethod
    def generate_message_hash(content: str, timestamp: str, user_id: str) -> str:
        """
        生成消息完整性哈希
        
        Args:
            content: 消息内容
            timestamp: 时间戳
            user_id: 用户ID
            
        Returns:
            str: SHA256哈希值
        """
        try:
            data = f"{content}|{timestamp}|{user_id}"
            return hashlib.sha256(data.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"生成消息哈希失败: {e}")
            return ""
    
    @staticmethod
    def prepare_encrypted_message_for_storage(
        content: str, 
        encryption_data: Dict, 
        user_id: str, 
        timestamp: str
    ) -> Dict:
        """
        准备加密消息用于数据库存储
        
        Args:
            content: 原始消息内容
            encryption_data: 加密数据 {iv, ciphertext, tag}
            user_id: 用户ID
            timestamp: 时间戳
            
        Returns:
            Dict: 存储格式的数据
        """
        try:
            # 生成消息完整性哈希
            message_hash = MessageCrypto.generate_message_hash(content, timestamp, user_id)
            
            return {
                "content": json.dumps(encryption_data),  # 将加密数据序列化存储
                "encrypted": True,
                "encryption_iv": encryption_data.get("iv"),
                "encryption_tag": encryption_data.get("tag"),
                "message_hash": message_hash
            }
            
        except Exception as e:
            logger.error(f"准备加密消息存储失败: {e}")
            return {
                "content": "[加密消息存储失败]",
                "encrypted": False
            }
    
    @staticmethod
    def prepare_encrypted_message_for_client(message_record) -> Dict:
        """
        准备发送给客户端的加密消息
        
        Args:
            message_record: 数据库消息记录
            
        Returns:
            Dict: 客户端格式的消息
        """
        try:
            if message_record.encrypted:
                # 解析存储的加密数据
                try:
                    encryption_data = json.loads(message_record.content)
                except json.JSONDecodeError:
                    # 如果解析失败，可能是旧格式或损坏的数据
                    encryption_data = {
                        "iv": message_record.encryption_iv,
                        "ciphertext": "[数据损坏]",
                        "tag": message_record.encryption_tag
                    }
                
                return {
                    "id": message_record.id,
                    "chatroom_id": message_record.chatroom_id,
                    "user_id": message_record.user_id,
                    "user_name": message_record.user_name,
                    "content": "[加密消息]",  # 不发送原始内容
                    "message_type": message_record.message_type,
                    "timestamp": message_record.created_at.isoformat(),
                    "encrypted": True,
                    "encryption_data": encryption_data,
                    "message_hash": message_record.message_hash
                }
            else:
                # 未加密消息
                return {
                    "id": message_record.id,
                    "chatroom_id": message_record.chatroom_id,
                    "user_id": message_record.user_id,
                    "user_name": message_record.user_name,
                    "content": message_record.content,
                    "message_type": message_record.message_type,
                    "timestamp": message_record.created_at.isoformat(),
                    "encrypted": False
                }
                
        except Exception as e:
            logger.error(f"准备客户端消息失败: {e}")
            return {
                "id": getattr(message_record, 'id', 'unknown'),
                "error": "消息格式化失败"
            }
    
    @staticmethod
    def validate_encryption_data(encryption_data: Dict) -> Tuple[bool, str]:
        """
        验证加密数据格式
        
        Args:
            encryption_data: 加密数据字典
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        required_fields = ['iv', 'ciphertext', 'tag']
        
        if not isinstance(encryption_data, dict):
            return False, "加密数据必须是字典格式"
        
        for field in required_fields:
            if field not in encryption_data:
                return False, f"缺少必要字段: {field}"
            
            if not isinstance(encryption_data[field], str):
                return False, f"字段 {field} 必须是字符串"
            
            if len(encryption_data[field]) == 0:
                return False, f"字段 {field} 不能为空"
        
        # 验证IV长度 (AES-256-GCM通常使用96位/12字节的IV)
        try:
            iv_bytes = bytes.fromhex(encryption_data['iv'])
            if len(iv_bytes) != 12:  # 96位 = 12字节
                return False, "IV长度不正确，应为12字节(24个十六进制字符)"
        except ValueError:
            return False, "IV必须是有效的十六进制字符串"
        
        # 验证tag长度 (GCM标签通常为16字节)
        try:
            tag_bytes = bytes.fromhex(encryption_data['tag'])
            if len(tag_bytes) != 16:  # 128位 = 16字节
                return False, "认证标签长度不正确，应为16字节(32个十六进制字符)"
        except ValueError:
            return False, "认证标签必须是有效的十六进制字符串"
        
        return True, ""
    
    @staticmethod
    def validate_message_timestamp(timestamp_str: str, max_age_seconds: int = 300) -> bool:
        """
        验证消息时间戳，防止重放攻击
        
        Args:
            timestamp_str: ISO格式的时间戳字符串
            max_age_seconds: 最大允许的消息年龄(秒)
            
        Returns:
            bool: 时间戳是否有效
        """
        try:
            # 解析时间戳
            message_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            current_time = datetime.utcnow()
            
            # 检查消息是否太旧
            age_seconds = (current_time - message_time).total_seconds()
            
            if age_seconds > max_age_seconds:
                logger.warning(f"消息时间戳过旧: {age_seconds}秒")
                return False
            
            # 检查消息是否来自未来(允许小的时钟偏差)
            if age_seconds < -60:  # 允许1分钟的时钟偏差
                logger.warning(f"消息时间戳来自未来: {age_seconds}秒")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"时间戳验证失败: {e}")
            return False


class MessageSecurityManager:
    """消息安全管理器"""
    
    def __init__(self):
        self.processed_hashes = set()  # 简单的重放攻击防护
        self.max_hash_cache = 10000   # 最大缓存的哈希数量
    
    def is_message_duplicate(self, message_hash: str) -> bool:
        """检查消息是否重复(简单的重放攻击防护)"""
        if message_hash in self.processed_hashes:
            return True
        
        # 添加到已处理集合
        self.processed_hashes.add(message_hash)
        
        # 如果缓存过大，清理一些旧的哈希
        if len(self.processed_hashes) > self.max_hash_cache:
            # 简单的清理策略：清除一半
            old_hashes = list(self.processed_hashes)[:len(self.processed_hashes)//2]
            for old_hash in old_hashes:
                self.processed_hashes.discard(old_hash)
        
        return False
    
    def validate_message_security(
        self, 
        content: str, 
        timestamp: str, 
        user_id: str, 
        message_hash: str,
        encryption_data: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        综合验证消息安全性
        
        Returns:
            Tuple[bool, str]: (是否通过验证, 错误信息)
        """
        # 1. 验证时间戳
        if not MessageCrypto.validate_message_timestamp(timestamp):
            return False, "消息时间戳无效或过期"
        
        # 2. 验证消息完整性
        if not MessageCrypto.verify_message_hash(content, timestamp, user_id, message_hash):
            return False, "消息完整性验证失败"
        
        # 3. 检查重放攻击
        if self.is_message_duplicate(message_hash):
            return False, "检测到重复消息，可能的重放攻击"
        
        # 4. 如果有加密数据，验证加密数据格式
        if encryption_data:
            is_valid, error_msg = MessageCrypto.validate_encryption_data(encryption_data)
            if not is_valid:
                return False, f"加密数据格式错误: {error_msg}"
        
        return True, ""

# 全局消息安全管理器实例
message_security_manager = MessageSecurityManager()
