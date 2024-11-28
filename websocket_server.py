import asyncio
import websockets
import json
import time
import numpy as np
import json
import base64
import audioop
import time


async def handle_connection(websocket):
    print(f"Conexão estabelecida com {websocket.remote_address}")
    

    try:
        async for message in websocket:

            data = json.loads(message)

  
            # Recupera o timestamp enviado pelo cliente
            timestamp = data.get("timestamp", None)

            # Prepara e envia a resposta
            response = {
                "id": data.get("id", "unknown"),
                "timestamp": timestamp,  # Retorna o mesmo timestamp
                "status": "received"
            }
            await websocket.send(json.dumps(response))
            print(f"Mensagem processada e resposta enviada: {response}")

    except websockets.ConnectionClosed:
        print("Conexão fechada.")

async def main():
    # Define o servidor WebSocket
    server = await websockets.serve(handle_connection, "0.0.0.0", 8767)
    print("Servidor WebSocket iniciado em ws://0.0.0.0:8767")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
