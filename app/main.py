import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List
from datetime import datetime
from dotenv import load_dotenv
import os
from .database import get_db
from sqlalchemy.orm import Session

load_dotenv()



# Create a connection to the PostgreSQL database
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DATABASE_HOST"),
            database=os.getenv("DATABASE_NAME"),
            user= os.getenv("DATABASE_USER"),
            password= os.getenv("DATABASE_PASS"),
            cursor_factory=RealDictCursor  # This returns results as dictionaries for easier access
        )
        return conn
    except (Exception, psycopg2.Error) as error:
        print("Error connecting to the database:", error)

# Sample HTML page (you can keep this unchanged)
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now();
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages');
                var message = document.createElement('li');
                var content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText");
                ws.send(input.value);
                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""


app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket)

    # Get the database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Retrieve and send old messages to the client
    cursor.execute("SELECT * FROM messages ORDER BY timestamp ASC")
    messages = cursor.fetchall()
    for message in messages:
        await websocket.send_text(f"Client #{message['client_id']} at {message['timestamp']}: {message['message']}")

    try:
        while True:
            data = await websocket.receive_text()

            # Save the new message to the database
            cursor.execute("INSERT INTO messages (client_id, message) VALUES (%s, %s)", (client_id, data))
            conn.commit()

            # Send the message to the client and broadcast it to others
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
    finally:
        cursor.close()
        conn.close()  # Close the database connection