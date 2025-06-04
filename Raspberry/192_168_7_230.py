import asyncio
import websockets
import base64
import json
from picamera2 import Picamera2
import time
import io
import numpy as np
from PIL import Image
from datetime import datetime

async def connect_with_retry(uri, max_retries=5, retry_delay=5):
    """Retry connection logic in case of failure."""
    for attempt in range(max_retries):
        try:
            return await websockets.connect(uri)
        except ConnectionRefusedError:
            if attempt < max_retries - 1:
                print(f"Conexion fallida. Reintentando en {retry_delay} segundos...")
                await asyncio.sleep(retry_delay)
            else:
                raise
        except Exception as e:
            print(f"Error al conectar: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise

async def receive_commands():
    """Waits for 'capture' command from the server and sends images accordingly."""
    uri = "ws://192.168.7.250:12345"
    
    while True:
        camera = None
        try:
            camera = Picamera2()
            camera.configure(camera.create_still_configuration(
                raw={"size": (1640, 1232)},
                main={"size": (640, 480)},
                controls={"FrameDurationLimits": (10000, 10000)}  # 10 FPS
            ))
            camera.start()
            
            await asyncio.sleep(2)  # Allow camera initialization
            
            websocket = await connect_with_retry(uri)
            print("Conectado al servidor.")
            
            async for message in websocket:
                try:
                    command = json.loads(message)
                    
                    if command["type"] == "capture":
                        timestamp_sent = command.get("timestamp_sent", "N/A")  # Timestamp from server
                        
                        # Capture frame
                        timestamp_received = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')  # Time of capture
                        frame = camera.capture_array()
                        
                        pil_image = Image.fromarray(frame)
                        with io.BytesIO() as stream:
                            pil_image.save(stream, format='JPEG', quality=65)
                            img_data = stream.getvalue()
                        
                        message = {
                            "type": "image",
                            "data": base64.b64encode(img_data).decode('utf-8'),
                            "timestamp_sent": timestamp_sent,  # Sent by server
                            "timestamp_received": timestamp_received  # Time of capture
                        }
                        
                        await websocket.send(json.dumps(message))
                        print(f"Imagen enviada con timestamps: sent={timestamp_sent}, received={timestamp_received}")

                except json.JSONDecodeError:
                    print("Error decodificando mensaje JSON.")
                except websockets.exceptions.ConnectionClosed:
                    print("Conexion cerrada. Intentando reconectar...")
                    break
                except Exception as e:
                    print(f"Error al recibir comando: {e}")
                    break
                    
        except Exception as e:
            print(f"Error general: {e}")
        finally:
            if camera:
                camera.stop()
            try:
                await websocket.close()
            except:
                pass
            
        print("Reintentando conexion en 5 segundos...")
        await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(receive_commands())
    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario")
