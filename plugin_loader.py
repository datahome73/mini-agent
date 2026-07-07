"""
插件加载器 — 自动发现并加载 plugins/ 目录下的插件。

每个插件是一个 packages 目录（含 __init__.py），导出 Plugin 类：

    class Plugin:
        name = "my_plugin"          # 唯一标识
        description = "..."          # 一句话说明

        def on_load(self, context: dict):
            '''可选初始化钩子。在 get_tools 前调用。
               context 包含重要共享对象：
               - workspace_dir: str
               - agent_config: dict
               - long_term_memory: LongTermMemory | None
            '''
            pass

        def get_tools(self) -> list[Tool]:
            '''返回本插件提供的工具列表。'''
            return []
"""

import importlib
import logging
import os
from pathlib import Path
from typing import Any

from tools.base import Tool
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# 插件必须导出的类名
_PLUGIN_CLASS_NAME = "Plugin"


class PluginMeta:
    """已加载的插件元信息"""

    def __init__(self, name: str, description: str, path: str, tools: list[Tool]):
        self.name = name
        self.description = description
        self.path = path
        self.tools = tools
        self.enabled = True

    def __repr__(self):
        return (f"PluginMeta(name={self.name!r}, enabled={self.enabled}, "
                f"tools={len(self.tools)})")


class PluginLoader:
    """插件加载器 — 扫描目录、加载、注册工具"""

    def __init__(self, plugins_dir: str = "plugins"):
        self._plugins_dir = Path(plugins_dir)
        self._loaded_plugins: dict[str, PluginMeta] = {}

    # ---- 公开接口 ----

    @property
    def loaded_plugins(self) -> dict[str, PluginMeta]:
        """所有已加载的插件（name → PluginMeta）"""
        return dict(self._loaded_plugins)

    def discover(self) -> list[str]:
        """扫描 plugins/ 目录，返回发现的插件名列表"""
        if not self._plugins_dir.is_dir():
            logger.warning("插件目录不存在: %s", self._plugins_dir)
            return []

        found = []
        for entry in sorted(self._plugins_dir.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("_"):
                continue  # 跳过 __pycache__ 等
            init_file = entry / "__init__.py"
            if init_file.is_file():
                found.append(entry.name)
        return found

    def load_all(self, registry: ToolRegistry, context: dict[str, Any] | None = None) -> list[PluginMeta]:
        """扫描并加载所有插件，将工具注册到 registry。"""
        names = self.discover()
        loaded = []
        for name in names:
            try:
                meta = self._load_one(name, context or {})
                if meta:
                    for tool in meta.tools:
                        registry.register(tool)
                    self._loaded_plugins[name] = meta
                    loaded.append(meta)
                    logger.info("插件已加载: %s (%d 个工具)", name, len(meta.tools))
            except Exception as e:
                logger.exception("插件加载失败: %s — %s", name, e)
        return loaded

    def load_single(self, name: str, registry: ToolRegistry,
                    context: dict[str, Any] | None = None) -> PluginMeta | None:
        """加载单个指定插件。失败返回 None。"""
        try:
            meta = self._load_one(name, context or {})
            if meta:
                for tool in meta.tools:
                    registry.register(tool)
                self._loaded_plugins[name] = meta
                logger.info("插件已加载: %s (%d 个工具)", name, len(meta.tools))
                return meta
        except Exception as e:
            logger.exception("插件加载失败: %s — %s", name, e)
        return None

    # ---- 内部 ----

    def _load_one(self, name: str, context: dict[str, Any]) -> PluginMeta | None:
        """加载单个插件，返回 PluginMeta"""
        module_path = f"plugins.{name}"
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as e:
            logger.error("无法导入插件模块 %s: %s", module_path, e)
            return None

        plugin_cls = getattr(module, _PLUGIN_CLASS_NAME, None)
        if plugin_cls is None:
            logger.warning("插件 %s 没有导出 Plugin 类", name)
            return None

        # 实例化
        try:
            instance = plugin_cls()
        except Exception as e:
            logger.error("实例化插件 %s 失败: %s", name, e)
            return None

        plugin_name = getattr(instance, "name", name)
        plugin_desc = getattr(instance, "description", "")

        # on_load 钩子
        if hasattr(instance, "on_load"):
            try:
                instance.on_load(context)
            except Exception as e:
                logger.warning("插件 %s 的 on_load 异常: %s", name, e)

        # 获取工具
        tools = []
        if hasattr(instance, "get_tools"):
            try:
                tools = instance.get_tools()
            except Exception as e:
                logger.error("插件 %s 的 get_tools 异常: %s", name, e)
                return None

        return PluginMeta(
            name=plugin_name,
            description=plugin_desc,
            path=str(self._plugins_dir / name),
            tools=tools or [],
        )
