from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import random
import uuid
from typing import Dict

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Game state
games: Dict[str, dict] = {}

SUITS = ["hearts", "diamonds", "clubs", "spades"]

class GameManager:
    def __init__(self):
        self.connections = {}
        
    async def connect(self, websocket: WebSocket, game_id: str, player_id: str):
        await websocket.accept()
        self.connections[player_id] = websocket
        
        if game_id not in games:
            games[game_id] = {
                "players": {},
                "deck": [],
                "logs": [],
                "current_turn": 0,
                "turn_order": [],
                "status": "lobby"
            }
        
        return games[game_id]

manager = GameManager()

def initialize_deck(game_id: str, player_count: int):
    game = games[game_id]
    deck = [{"number": n, "suit": s} for n in range(1, 14) for s in SUITS]
    random.shuffle(deck)
    
    cards_per_player = max(4, 7 - (player_count - 2) // 2)
    
    for p in game["players"]:
        game["players"][p]["hand"] = [deck.pop() for _ in range(cards_per_player)]
    
    game["deck"] = deck
    game["status"] = "playing"
    game["turn_order"] = list(game["players"].keys())
    game["current_turn"] = 0

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    game = await manager.connect(websocket, game_id, player_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["action"] == "join":
                game["players"][player_id] = {
                    "hand": [],
                    "sets": [],
                    "status": "joined"
                }
                await manager.broadcast(game_id, {"type": "player_joined", "player": player_id})
                
            elif data["action"] == "start":
                initialize_deck(game_id, len(game["players"]))
                await manager.broadcast(game_id, {"type": "game_start", "state": game})
                
            elif data["action"] == "ask":
                current_player = game["turn_order"][game["current_turn"]]
                
                if player_id != current_player:
                    await websocket.send_json({"error": "Not your turn!"})
                    continue
                
                # Proses logika permainan di sini
                # (Implementasi mirip dengan contoh Flask sebelumnya)
                
                await manager.broadcast(game_id, {"type": "game_update", "state": game})
                
    except WebSocketDisconnect:
        del manager.connections[player_id]
        await manager.broadcast(game_id, {"type": "player_left", "player": player_id})