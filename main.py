from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from typing import Dict
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from io import BytesIO
from PIL import Image

app = FastAPI()

# 연결된 클라이언트를 저장할 딕셔너리
active_connections = {}
        
# 각 방에 있는 클라이언트를 저장할 딕셔너리
rooms: Dict[str, Dict[str, WebSocket]] = {}

# 채팅 메시지를 해당 방의 클라이언트들에게 브로드캐스트하는 함수
async def broadcast_message(room_id: str, client_id: str, message: str):
    if room_id in rooms:
        for cid, websocket in rooms[room_id].items():
            if cid != client_id:  # 메시지 보낸 본인을 제외하고 메시지 전송
                await websocket.send_text(f"Client {client_id}: {message}")
            else:  # 본인에게는 다른 포맷으로 메시지 전송
                await websocket.send_text(f"You: {message}")

@app.websocket("/chat/{room_id}/{client_id}")
async def connect_websocket(room_id: str, client_id: str, websocket: WebSocket):
    await websocket.accept()
    if room_id not in rooms:
        rooms[room_id] = {}
    rooms[room_id][client_id] = websocket  # 클라이언트를 해당 방에 추가
    try:
        while True:
            data = await websocket.receive_text()
            await broadcast_message(room_id, client_id, data)
    except WebSocketDisconnect:
        rooms[room_id].pop(client_id)
        if not rooms[room_id]:  # 방이 비었으면 해당 방을 삭제
            del rooms[room_id]

@app.get("/chat/", response_class=HTMLResponse)
async def chat_page():
    return HTMLResponse("""
    <html>
    <head>
        <title>Multi-Room Chat</title>
    </head>
    <body>
        <form id="join-form">
            <label for="room-id">Room ID:</label>
            <input type="text" id="room-id" name="room_id">
            <label for="client-id">Client ID:</label>
            <input type="text" id="client-id" name="client_id">
            <button type="submit">Join Room</button>
        </form>

        <div id="chat-box" style="display: none;"></div>
        <input type="text" id="message-input" placeholder="Type your message..." style="display: none;">
        <button id="send-button" style="display: none;">Send</button>

        <script>
            const joinForm = document.getElementById('join-form');
            const chatBox = document.getElementById('chat-box');
            const messageInput = document.getElementById('message-input');
            const sendButton = document.getElementById('send-button');
            let ws;

            joinForm.addEventListener('submit', function(event) {
                event.preventDefault();
                const room_id = document.getElementById('room-id').value;
                const client_id = document.getElementById('client-id').value;
                ws = new WebSocket(`ws://localhost:8000/chat/${room_id}/${client_id}`);

                ws.onopen = function() {
                    chatBox.style.display = 'block';
                    messageInput.style.display = 'block';
                    sendButton.style.display = 'block';
                };
                ws.onmessage = function(event) {
                    chatBox.innerHTML += `<p>${event.data}</p>`;
                };
                ws.onclose = function() {
                    console.log('WebSocket disconnected');
                };

                sendButton.onclick = function() {
                    const message = messageInput.value;
                    if (message.trim() !== '') {
                        ws.send(message);
                        messageInput.value = '';
                    }
                };
            });
        </script>
    </body>
    </html>
    """)

@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    return Response(content=b"", media_type="image/png")
