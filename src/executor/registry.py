"""
ツール登録管理
"""
from ..tools.base import BaseTool, ToolType


class ToolRegistry:
    """ツールの登録・取得管理"""

    def __init__(self):
        self._tools: dict[ToolType, BaseTool] = {}

    def register(self, tool: BaseTool):
        """ツール登録"""
        self._tools[tool.tool_type] = tool

    def get(self, tool_type: ToolType) -> BaseTool:
        """ツール取得"""
        if tool_type not in self._tools:
            raise KeyError(f"Tool not registered: {tool_type.value}")
        return self._tools[tool_type]

    def list_tools(self) -> list[dict]:
        """登録済みツール一覧"""
        return [
            {
                "type": t.tool_type.value,
                "name": t.name,
                "description": t.description,
            }
            for t in self._tools.values()
        ]

    async def health_check_all(self) -> dict[str, bool]:
        """全ツールのヘルスチェック"""
        results = {}
        for tool_type, tool in self._tools.items():
            results[tool_type.value] = await tool.health_check()
        return results
