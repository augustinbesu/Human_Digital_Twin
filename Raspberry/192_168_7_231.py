import asyncio
import websockets
import base64
import json
from picamera import PiCamera
import time
import io
from datetime import datetime

latest_frame = None  # Global variable to store the latest frame

async def capture_frames(queue):
    """Continuously captures frames and stores the latest one."""
    global latest_frame
    camera = PiCamera()
    try:
        # Camera settings
        camera.resolution = (640, 480)
        camera.framerate = 30
        camera.exposure_mode = 'sports'
        camera.awb_mode = 'auto'
        camera.meter_mode = 'average'
        camera.video_denoise = False

        await asyncio.sleep(2)  # Allow camera to initialize

        stream = io.BytesIO()
        
        for _ in camera.capture_continuous(stream, format='jpeg', use_video_port=True, quality=65):
            stream.seek(0)
            latest_frame = stream.getvalue()  # Store the latest frame
            stream.seek(0)
            stream.truncate()
            
            await asyncio.sleep(0.05)  # Capture loop delay (~20 FPS)
    except Exception as e:
        print(f"Error en captura de frames: {e}")
    finally:
        camera.close()

async def connect_with_retry(uri, max_retries=5, retry_delay=5):
    """Retries connection to the WebSocket server in case of failure."""
    for attempt in range(max_retries):
        try:
            return await websockets.connect(uri)
        except ConnectionRefusedError:
            if attempt < max_retries - 1:
                print(f"Conexión fallida. Reintentando en {retry_delay} segundos...")
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
    """Listens for 'capture' commands from the WebSocket server and sends the latest stored frame."""
    uri = "ws://192.168.7.250:12345"

    while True:
        websocket = None
        try:
            websocket = await connect_with_retry(uri)
            print("Conectado al servidor. Esperando instrucciones...")

            async for message in websocket:
                try:
                    command = json.loads(message)

                    if command["type"] == "capture":
                        timestamp_sent = command.get("timestamp_sent", "N/A")  # Timestamp from server
                        timestamp_received = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')  # Local capture time
                        
                        # Send the latest stored frame
                        if latest_frame:
                            message = {
                                "type": "image",
                                "data": base64.b64encode(latest_frame).decode('utf-8'),
                                "timestamp_sent": timestamp_sent,
                                "timestamp_received": timestamp_received
                            }
                            await websocket.send(json.dumps(message))
                            print(f"Imagen enviada con timestamps: sent={timestamp_sent}, received={timestamp_received}")
                        else:
                            print("No hay frame disponible para enviar.")

                except json.JSONDecodeError:
                    print("Error al decodificar mensaje JSON.")
                except websockets.exceptions.ConnectionClosed:
                    print("Conexión cerrada. Intentando reconectar...")
                    break
                except Exception as e:
                    print(f"Error al recibir comando: {e}")
                    break

        except Exception as e:
            print(f"Error general: {e}")
        finally:
            if websocket:
                try:
                    await websocket.close()
                except:
                    pass
            
        print("Reintentando conexión en 5 segundos...")
        await asyncio.sleep(5)

async def main():
    """Runs the frame capture and command listener concurrently."""
    queue = asyncio.Queue()
    
    # Start both coroutines
    await asyncio.gather(
        capture_frames(queue),
        receive_commands()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario")
