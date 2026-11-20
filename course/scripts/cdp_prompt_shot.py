# -*- coding: utf-8 -*-
"""CDP：发送一条指令并截图（用于报告生成场景）。"""
import asyncio
import base64
import json
import sys

import requests
import websockets

PROMPT = "帮我生成一份本周研发周报，包含知识库使用情况"
OUT = sys.argv[1] if len(sys.argv) > 1 else r"D:\课设\截图\shot_report.png"
WAIT = int(sys.argv[2]) if len(sys.argv) > 2 else 45


async def main():
    page = None
    for _ in range(25):
        try:
            for p in requests.get("http://127.0.0.1:9222/json", timeout=5).json():
                if p.get("type") == "page" and "127.0.0.1:9000" in p.get("url", ""):
                    page = p
                    break
        except Exception:
            pass
        if page:
            break
        await asyncio.sleep(1)
    if not page:
        print("no page")
        return
    async with websockets.connect(page["webSocketDebuggerUrl"], max_size=80 * 1024 * 1024) as ws:
        mid = 0

        async def call(method, **params):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({"id": mid, "method": method, "params": params}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == mid:
                    return msg.get("result", {})

        await call("Page.enable")
        await call("Runtime.enable")
        await asyncio.sleep(6)
        fill = """
        (() => {
          const ta = document.querySelector('textarea');
          if (!ta) return 'no-textarea';
          const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(ta, %s);
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          return 'filled';
        })()
        """ % json.dumps(PROMPT, ensure_ascii=False)
        r1 = await call("Runtime.evaluate", expression=fill, returnByValue=True)
        print("fill:", r1.get("result", {}).get("value"))
        await asyncio.sleep(1.2)
        r2 = await call("Runtime.evaluate", expression="document.querySelector('button.btn-send')?.click(); 'clicked'", returnByValue=True)
        print("click:", r2.get("result", {}).get("value"))
        await asyncio.sleep(WAIT)
        shot = await call("Page.captureScreenshot", format="png")
        open(OUT, "wb").write(base64.b64decode(shot["data"]))
        print("saved", OUT)


asyncio.run(main())
