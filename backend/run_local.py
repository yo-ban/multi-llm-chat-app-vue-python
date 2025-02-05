import sys
import asyncio

# エントリーポイントで最も早い段階で、Windows環境の場合はProactorイベントループポリシーに切り替え
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.main import app  # app のインポート（ここ以降に Playwright 等がインポートされるようにする）
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5200) 