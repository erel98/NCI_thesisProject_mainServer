from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect
from websockets.exceptions import ConnectionClosedOK
import asyncio
from datetime import datetime
import json
import subprocess
from helper import Helper
import boto3
app = FastAPI()

# Let the script know which scenario we are simulating, checkpointing or replication
SIMULATION_SCENARIO = Helper.scenario

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    async def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_data(self, data: str, client_id: str):
        connection_info = self.active_connections.get(client_id)
        if connection_info:
            await connection_info.send_text(data)

manager = ConnectionManager()
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    current_region = getCurrentRegion()
    # Wait for client to connect
    await manager.connect(websocket, client_id)
    start_index = 0
    # Read checkpoint data
    checkpoint_data = readCheckpointDataFromJson()
    latest_value = checkpoint_data["latestValue"]
    before = checkpoint_data["before"]
    # If latest value is not null, start from the latest value
    if latest_value != -1:
        start_index = latest_value
        
    checkpoint_value = -1
    try:
        data = await websocket.receive_text()
        data = int(data)
        
        # Compute-heavy task
        for i in range(start_index, data):
            checkpoint_value = i
            print(i)
            # Simulate server failure at 5th iteration if scenario is replication
            if i == 5 and SIMULATION_SCENARIO != "checkpoint":
                raise WebSocketDisconnect
            # Update the latest values
            write_data = {"latestValue":i, "latestTime":before.strftime("%Y-%m-%d %H:%M:%S")}
            writeToCheckpointJson(write_data)
            # Wait for one second at each iteration
            await asyncio.sleep(1)
            
            await manager.send_data(f"Latest value: {i}", client_id)
            # Check if the client is still connected.
            try: 
                await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            except asyncio.TimeoutError:
                raise WebSocketDisconnect()
        # Empty the checkpoint JSON
        resetCheckpointJson()

        after = datetime.now()
        diff = (after - before).total_seconds()
        # Execution is successful. Send the total execution time
        await manager.send_data(f"{diff}", client_id)
    except WebSocketDisconnect:
        write_data = {"latestValue":checkpoint_value, "latestTime":before.strftime("%Y-%m-%d %H:%M:%S")}
        writeToCheckpointJson(write_data)
        # Raised on purpose. Send the so far spent time to client
        if SIMULATION_SCENARIO != "checkpoint":
            after = datetime.now()
            diff = (after - before).total_seconds()
            data = {"message":"replication", "diff":diff}
            # If this is the main server, sync checkpoint to the backup server
            if current_region == "eu-west-1" and SIMULATION_SCENARIO == "combined":
                subprocess.run(["bash", "./dataReplication.sh"])
            await manager.send_data(json.dumps(data), client_id)
            resetCheckpointJson()
        
        await manager.disconnect(client_id)
        print(f"Client {client_id} disconnected")

def getCurrentRegion():
    session = boto3.session.Session()
    current_region = session.region_name

    return current_region

def readCheckpointDataFromJson():
    with open("checkpoint.json", "r") as json_file:
        checkpoint_data = json.load(json_file)
        
    latest_value = checkpoint_data["latestValue"]
    before = checkpoint_data["latestTime"]
    
    if before:
       before = datetime.strptime(before, "%Y-%m-%d %H:%M:%S")
    else:
        before = datetime.now()
    return {"latestValue":latest_value, "before":before}

def writeToCheckpointJson(data_to_write: dict):
    with open("checkpoint.json", "w") as json_file:
        json.dump(data_to_write, json_file)
        
def resetCheckpointJson():
    with open("checkpoint.json", "w") as json_file:
        json.dump({"latestValue": -1, "latestTime": ""}, json_file)