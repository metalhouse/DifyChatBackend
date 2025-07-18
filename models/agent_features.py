"""
智能体功能配置数据模型

该模块定义了智能体功能配置的数据结构和验证逻辑，
用于管理不同智能体支持的功能开关。
"""

from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field, validator
from enum import Enum
import json
import os
from datetime import datetime
from pathlib import Path


class AgentFeatureType(str, Enum):
    """智能体功能类型枚举"""
    SUGGESTED_QUESTIONS = "suggested_questions"    # 问题建议
    FILE_UPLOAD = "file_upload"                   # 文件上传
    TEXT_TO_AUDIO = "text_to_audio"               # 文字转语音
    AUDIO_TO_TEXT = "audio_to_text"               # 语音转文字
    MESSAGE_FEEDBACK = "message_feedback"         # 消息反馈
    CONVERSATION_RENAME = "conversation_rename"   # 对话重命名
    MESSAGE_ANNOTATION = "message_annotation"     # 消息标注
    RETRIEVAL = "retrieval"                       # 知识检索
    CITATION = "citation"                         # 引用显示


class AgentFeatureConfig(BaseModel):
    """单个智能体功能配置"""
    agent_id: str = Field(..., description="智能体ID")
    agent_name: str = Field(..., description="智能体名称")
    enabled_features: Set[AgentFeatureType] = Field(
        default_factory=set,
        description="启用的功能列表"
    )
    disabled_features: Set[AgentFeatureType] = Field(
        default_factory=set,
        description="明确禁用的功能列表"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="最后更新时间"
    )
    updated_by: Optional[str] = Field(None, description="更新者")
    notes: Optional[str] = Field(None, description="配置备注")

    @validator('enabled_features', 'disabled_features')
    def validate_feature_overlap(cls, v, values):
        """验证启用和禁用功能不能重叠"""
        if 'enabled_features' in values:
            enabled = values['enabled_features']
            if isinstance(v, set) and v & enabled:
                raise ValueError("功能不能同时在启用和禁用列表中")
        return v

    def is_feature_enabled(self, feature: AgentFeatureType) -> bool:
        """检查功能是否启用"""
        if feature in self.disabled_features:
            return False
        return feature in self.enabled_features

    def enable_feature(self, feature: AgentFeatureType) -> None:
        """启用功能"""
        self.enabled_features.add(feature)
        self.disabled_features.discard(feature)
        self.last_updated = datetime.now()

    def disable_feature(self, feature: AgentFeatureType) -> None:
        """禁用功能"""
        self.disabled_features.add(feature)
        self.enabled_features.discard(feature)
        self.last_updated = datetime.now()

    def get_feature_summary(self) -> Dict[str, bool]:
        """获取功能启用状态摘要"""
        return {
            feature.value: self.is_feature_enabled(feature)
            for feature in AgentFeatureType
        }


class AgentFeatureManager:
    """智能体功能配置管理器"""
    
    def __init__(self, config_file: str = None):
        # 如果没有指定文件，尝试从config加载，否则使用默认值
        if config_file is None:
            try:
                # 尝试导入配置
                import sys
                sys.path.append(str(Path(__file__).parent.parent))
                from config import Config
                config = Config()
                # 假设agent_features.json在同一目录下
                data_dir = Path(config.database.data_dir)
                self.config_file = str(data_dir / "agent_features.json")
            except:
                # 如果导入失败，使用默认路径
                self.config_file = "agent_features.json"
        else:
            self.config_file = config_file
            
        self._configs: Dict[str, AgentFeatureConfig] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        """从文件加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for agent_id, config_data in data.items():
                        # 转换datetime字符串
                        if 'last_updated' in config_data:
                            config_data['last_updated'] = datetime.fromisoformat(
                                config_data['last_updated'].replace('Z', '+00:00')
                            )
                        self._configs[agent_id] = AgentFeatureConfig(**config_data)
            except Exception as e:
                print(f"Warning: Failed to load agent features config: {e}")
                self._configs = {}

    def _save_configs(self) -> None:
        """保存配置到文件"""
        try:
            data = {}
            for agent_id, config in self._configs.items():
                config_dict = config.dict()
                # 转换datetime为字符串
                config_dict['last_updated'] = config.last_updated.isoformat()
                # 转换Set为List以便JSON序列化
                config_dict['enabled_features'] = list(config.enabled_features)
                config_dict['disabled_features'] = list(config.disabled_features)
                data[agent_id] = config_dict
                
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error: Failed to save agent features config: {e}")
            raise

    def get_agent_config(self, agent_id: str) -> Optional[AgentFeatureConfig]:
        """获取智能体配置"""
        return self._configs.get(agent_id)

    def set_agent_config(self, config: AgentFeatureConfig) -> None:
        """设置智能体配置"""
        self._configs[config.agent_id] = config
        self._save_configs()

    def create_agent_config(
        self,
        agent_id: str,
        agent_name: str,
        enabled_features: Optional[List[AgentFeatureType]] = None,
        updated_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> AgentFeatureConfig:
        """创建新的智能体配置"""
        config = AgentFeatureConfig(
            agent_id=agent_id,
            agent_name=agent_name,
            enabled_features=set(enabled_features or []),
            updated_by=updated_by,
            notes=notes
        )
        self.set_agent_config(config)
        return config

    def update_agent_features(
        self,
        agent_id: str,
        enabled_features: List[AgentFeatureType],
        updated_by: Optional[str] = None
    ) -> Optional[AgentFeatureConfig]:
        """更新智能体功能配置"""
        config = self.get_agent_config(agent_id)
        if not config:
            return None
            
        config.enabled_features = set(enabled_features)
        config.disabled_features = set(AgentFeatureType) - set(enabled_features)
        config.last_updated = datetime.now()
        if updated_by:
            config.updated_by = updated_by
            
        self.set_agent_config(config)
        return config

    def is_feature_enabled(self, agent_id: str, feature: AgentFeatureType) -> bool:
        """检查智能体是否启用了特定功能"""
        config = self.get_agent_config(agent_id)
        if not config:
            # 默认行为：如果没有配置，返回False（保守策略）
            return False
        return config.is_feature_enabled(feature)

    def get_enabled_features(self, agent_id: str) -> Set[AgentFeatureType]:
        """获取智能体启用的所有功能"""
        config = self.get_agent_config(agent_id)
        if not config:
            return set()
        return config.enabled_features

    def list_all_agents(self) -> List[AgentFeatureConfig]:
        """列出所有智能体配置"""
        return list(self._configs.values())

    def delete_agent_config(self, agent_id: str) -> bool:
        """删除智能体配置"""
        if agent_id in self._configs:
            del self._configs[agent_id]
            self._save_configs()
            return True
        return False

    def get_feature_statistics(self) -> Dict[str, int]:
        """获取功能使用统计"""
        stats = {feature.value: 0 for feature in AgentFeatureType}
        for config in self._configs.values():
            for feature in config.enabled_features:
                stats[feature.value] += 1
        return stats


# 全局管理器实例
agent_feature_manager = AgentFeatureManager()


# API请求/响应模型
class AgentFeatureUpdateRequest(BaseModel):
    """智能体功能更新请求"""
    agent_name: Optional[str] = Field(None, description="智能体名称")
    enabled_features: List[AgentFeatureType] = Field(
        default_factory=list,
        description="启用的功能列表"
    )
    notes: Optional[str] = Field(None, description="配置备注")


class AgentFeatureResponse(BaseModel):
    """智能体功能配置响应"""
    agent_id: str
    agent_name: str
    enabled_features: List[str]
    disabled_features: List[str]
    last_updated: str
    updated_by: Optional[str]
    notes: Optional[str]
    feature_summary: Dict[str, bool]

    @classmethod
    def from_config(cls, config: AgentFeatureConfig) -> "AgentFeatureResponse":
        """从配置对象创建响应"""
        return cls(
            agent_id=config.agent_id,
            agent_name=config.agent_name,
            enabled_features=[f.value for f in config.enabled_features],
            disabled_features=[f.value for f in config.disabled_features],
            last_updated=config.last_updated.isoformat(),
            updated_by=config.updated_by,
            notes=config.notes,
            feature_summary=config.get_feature_summary()
        )


class AgentFeatureListResponse(BaseModel):
    """智能体功能配置列表响应"""
    agents: List[AgentFeatureResponse]
    total_count: int
    feature_statistics: Dict[str, int]