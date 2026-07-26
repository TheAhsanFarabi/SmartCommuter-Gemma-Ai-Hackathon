import asyncio
import json
import threading
import queue
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from agent.loop import run_agent
from agent.config import Config, SESSION_DIR
from agent.skills import skills_manager
from agent.tasks import TaskList
from agent.memory import MemoryLayer
import ollama

app = FastAPI(title="Smart Transit & Commuter Agent Web UI")

app.mount("/static", StaticFiles(directory="web"), name="static")

@app.get("/")
async def get_index():
    return FileResponse("web/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    cfg = Config.load()
    skills_manager.load()
    system_prompt = skills_manager.build_system_prompt()
    history = []
    
    def get_state():
        tasks = TaskList.load()
        # Find sessions
        sessions = []
        if SESSION_DIR.exists():
            for f in SESSION_DIR.glob("*_history.json"):
                sessions.append(f.name.replace("_history.json", ""))
                
        # Fetch available models dynamically
        try:
            ollama_response = ollama.list()
            # Depending on ollama-python version, models could be an attribute or dict key
            models_list = getattr(ollama_response, 'models', ollama_response.get('models', [])) if hasattr(ollama_response, 'get') else ollama_response.models
            available_models = [getattr(m, 'model', getattr(m, 'name', str(m))) for m in models_list]
        except Exception as e:
            print("Error fetching models:", e)
            available_models = [cfg.model]
            
        # Context Token Calculation
        if history:
            mem = MemoryLayer.from_list(history)
            tokens = mem.total_tokens
            turns = mem.message_count
        else:
            tokens = 0
            turns = 0
        
        return {
            "type": "state",
            "model": cfg.model,
            "available_models": available_models,
            "tasks": [
                {"id": t.id, "text": t.text, "status": t.status} 
                for t in tasks.items
            ],
            "sessions": sessions,
            "active_session": cfg.active_session or "default",
            "context_tokens": tokens,
            "context_limit": cfg.context_limit,
            "turn_count": turns
        }
    
    try:
        # Send initial state
        await websocket.send_json(get_state())
        
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload.get("type") == "command":
                cmd = payload.get("cmd")
                val = payload.get("value")
                
                if cmd == "get_state":
                    await websocket.send_json(get_state())
                elif cmd == "clear":
                    history.clear()
                    await websocket.send_json({"type": "stream", "token": "মেমরি মুছে ফেলা হয়েছে। এজেন্ট আগের কথোপকথন ভুলে গেছে।"})
                    await websocket.send_json({"type": "done"})
                    await websocket.send_json(get_state())
                elif cmd == "set_model":
                    cfg.model = val
                    cfg.save()
                    await websocket.send_json(get_state())
                elif cmd == "add_task":
                    tasks = TaskList.load()
                    tasks.add(val)
                    tasks.save()
                    await websocket.send_json(get_state())
                elif cmd == "clear_tasks":
                    tasks = TaskList.load()
                    tasks.clear_done()
                    tasks.save()
                    await websocket.send_json(get_state())
                elif cmd == "clear_all_tasks":
                    tasks = TaskList.load()
                    tasks.clear_all()
                    tasks.save()
                    await websocket.send_json(get_state())
                continue

            user_input = payload.get("message", "").strip()
            if not user_input:
                continue
                
            q = queue.Queue()
            
            def on_tool_call(name, args, result):
                q.put({
                    "type": "tool_call",
                    "name": name,
                    "args": args,
                    "result": str(result)
                })
                # Refresh state after any tool call
                q.put(get_state())
                
            def on_stream(token):
                q.put({
                    "type": "stream",
                    "token": token
                })
                
            def run_agent_thread():
                nonlocal history
                try:
                    answer, history = run_agent(
                        user_input=user_input,
                        model=cfg.model,
                        system_prompt=system_prompt,
                        history=history,
                        verbose=False,
                        on_tool_call=on_tool_call,
                        on_stream=on_stream
                    )
                    q.put({"type": "done", "answer": answer})
                    q.put(get_state())
                except Exception as e:
                    q.put({"type": "error", "message": str(e)})

            thread = threading.Thread(target=run_agent_thread)
            thread.start()
            
            while True:
                try:
                    msg = await asyncio.to_thread(q.get)
                    if msg["type"] == "done":
                        await websocket.send_json({"type": "done"})
                        break
                    elif msg["type"] == "error":
                        await websocket.send_json({"type": "error", "message": msg["message"]})
                        break
                    else:
                        await websocket.send_json(msg)
                except Exception as e:
                    print("Error sending to websocket:", e)
                    break
                    
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
