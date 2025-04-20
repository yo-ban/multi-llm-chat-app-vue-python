from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from mcp_manager import MCPClientManager
import os

# MCPClientManagerのインスタンスを作成 (グローバル or アプリケーション状態)
mcp_manager = MCPClientManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # アプリケーション起動時にMCP接続を初期化
    # 設定ファイルのパスを環境変数などから取得
    config_path = os.getenv("MCP_CONFIG_PATH", "./mcp_servers.json")
    await mcp_manager.initialize_from_config(config_path=config_path)
    yield
    # アプリケーション終了時にクリーンアップ
    await mcp_manager.close_all_connections()

app = FastAPI(lifespan=lifespan)

# 依存性注入
async def get_mcp_manager():
    # ここで初期化状態を確認し、未初期化ならエラーを出すか、
    # initialize_from_config を再度呼び出す（冪等性があれば）
    if not mcp_manager._is_initialized:
         raise RuntimeError("MCP Manager is not initialized yet.")
    return mcp_manager

@app.get("/mcp/tools")
async def list_mcp_tools(manager: MCPClientManager = Depends(get_mcp_manager)):
    tools = await manager.get_available_tools()
    return tools

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)

# /api/messages エンドポイントで manager を注入して利用する