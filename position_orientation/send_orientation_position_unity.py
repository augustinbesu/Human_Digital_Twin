import asyncio
import websockets
import cv2
import numpy as np
import base64
import json
from datetime import datetime
import mediapipe as mp
from utils import DLT, get_projection_matrix
import os
from bleak import BleakScanner, BleakClient
import time
import re
import socket

# Configuración de MediaPipe y constantes (igual que en server.py)
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Nuevas configuraciones para BLE
DEVICE_NAME_PATTERN = r"Ard(\d+)"
CHARACTERISTIC_UUID = "2A5B"
MAX_ARDUINO_NUMBER = 11

IP_TO_ID = {
    "192.168.7.231": 0,
    "192.168.7.230": 1
}

pose_keypoints = [
    0,   # nariz
    11,  # hombro izquierdo
    13,  # codo izquierdo
    15,  # muñeca izquierda
    23,  # cadera izquierda
    12,  # hombro derecho
    14,  # codo derecho
    16,  # muñeca derecha
    24,  # cadera derecha
    25,  # rodilla izquierda
    26,  # rodilla derecha
    27,  # tobillo izquierdo
]

class PositionRecorder:
    def __init__(self):
        self.window_name = "Synchronized Videos"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        self.max_sync_diff = 100
        self.frames_buffer = {0: [], 1: []}
        
        # Inicializar detectores de pose
        self.pose_detector0 = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.pose_detector1 = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        # Obtener matrices de proyección
        self.P0 = get_projection_matrix(0)
        self.P1 = get_projection_matrix(1)
        
        # Nuevo: configuración para orientaciones
        self.ble_clients = {}  # {device_address: BleakClient}
        self.orientations = {}  # {arduino_number: {timestamp, quaternion}}
        self.arduino_numbers = {}  # {device_address: arduino_number}
        self.running = True
        self.last_print_time = 0
        self.print_interval = 0.1
        
        # Agregar puerto para Unity
        self.unity_ip = "127.0.0.1"
        self.unity_port = 5065  # Cambiar a 5065 para coincidir con Unity
        self.unity_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Iniciar servidor WebSocket para Unity
        self.unity_server = None
    
    def get_keypoint_name(self, keypoint_id):
        names = {
            0: "nariz",
            11: "hombro_izq",
            13: "codo_izq",
            15: "muneca_izq",
            23: "cadera_izq",
            12: "hombro_der",
            14: "codo_der",
            16: "muneca_der",
            24: "cadera_der",
            25: "rodilla_izq",
            26: "rodilla_der",
            27: "tobillo_izq"
        }
        return names.get(keypoint_id, f"punto_{keypoint_id}")

    def process_frame_with_pose(self, frame, detector):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False
        results = detector.process(frame_rgb)
        frame_rgb.flags.writeable = True
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        
        keypoints = []
        if results.pose_landmarks:
            for i, landmark in enumerate(results.pose_landmarks.landmark):
                if i not in pose_keypoints:
                    continue
                x = int(round(landmark.x * frame.shape[1]))
                y = int(round(landmark.y * frame.shape[0]))
                keypoints.append([x, y])
                cv2.circle(frame_bgr, (x, y), 3, (0,0,255), -1)
            
            # Dibujar conexiones
            mp_drawing.draw_landmarks(
                frame_bgr,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
            )
        else:
            keypoints = [[-1, -1]] * len(pose_keypoints)
            
        return frame_bgr, keypoints
        
    def add_frame(self, client_id, frame, timestamp):
        self.frames_buffer[client_id].append((timestamp, frame))
        if len(self.frames_buffer[client_id]) > 5:
            self.frames_buffer[client_id].pop(0)
            
    def find_matching_frames(self):
        if not self.frames_buffer[0] or not self.frames_buffer[1]:
            return None, None
        
        ts1, frame1 = self.frames_buffer[0][-1]
        ts2, frame2 = self.frames_buffer[1][-1]
        
        diff = abs((datetime.strptime(ts1, '%Y-%m-%d %H:%M:%S.%f') - 
                   datetime.strptime(ts2, '%Y-%m-%d %H:%M:%S.%f')).total_seconds() * 1000)
        
        if diff < self.max_sync_diff:
            self.frames_buffer[0] = [self.frames_buffer[0][-1]]
            self.frames_buffer[1] = [self.frames_buffer[1][-1]]
            return frame1, frame2
            
        return None, None

    async def find_ble_devices(self):
        """Busca continuamente dispositivos Arduino BLE"""
        while self.running:
            try:
                devices = await BleakScanner.discover()
                for device in devices:
                    if device.name and (match := re.match(DEVICE_NAME_PATTERN, device.name)):
                        arduino_number = int(match.group(1))
                        if arduino_number <= MAX_ARDUINO_NUMBER and device.address not in self.ble_clients:
                            print(f"Arduino {arduino_number} encontrado: {device.name} ({device.address})")
                            client = BleakClient(device.address)
                            self.ble_clients[device.address] = client
                            self.arduino_numbers[device.address] = arduino_number
                            asyncio.create_task(self.handle_ble_device(device.address))
            except Exception as e:
                print(f"Error en búsqueda de dispositivos BLE: {e}")
            await asyncio.sleep(5)

    async def handle_ble_device(self, address):
        """Maneja la conexión con un dispositivo BLE"""
        client = self.ble_clients[address]
        arduino_number = self.arduino_numbers[address]
        try:
            await client.connect()
            print(f"Conectado a Arduino {arduino_number} ({address})")

            def notification_handler(sender, data):
                try:
                    w, x, y, z = map(float, data.decode().split(','))
                    timestamp = datetime.now().timestamp()
                    self.orientations[arduino_number] = {
                        'timestamp': timestamp,
                        'quaternion': [w, x, y, z]
                    }
                except Exception as e:
                    print(f"Error procesando datos de Arduino {arduino_number}: {e}")

            await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
            
            while self.running and client.is_connected:
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error en Arduino {arduino_number}: {e}")
        finally:
            await client.disconnect()
            del self.ble_clients[address]
            if arduino_number in self.orientations:
                del self.orientations[arduino_number]
            del self.arduino_numbers[address]
            print(f"Desconectado Arduino {arduino_number}")

    async def start_unity_server(self):
        """Inicia el servidor WebSocket para Unity"""
        self.unity_server = await websockets.serve(
            self.handle_unity_client, 
            "0.0.0.0", 
            self.unity_port
        )
        print(f"Servidor Unity iniciado en puerto {self.unity_port}")

    async def handle_unity_client(self, websocket):
        """Maneja las conexiones de clientes Unity"""
        print("Cliente Unity conectado")
        self.unity_clients.add(websocket)
        try:
            async for _ in websocket:  # Mantener conexión abierta
                pass
        finally:
            self.unity_clients.remove(websocket)
            print("Cliente Unity desconectado")

    async def send_data_to_unity(self, positions_3d, timestamp):
        """Envía posiciones 3D y orientaciones por UDP"""
        try:
            # SOLO enviar orientaciones para los Arduinos conectados
            for arduino_number, data in self.orientations.items():
                w, x, y, z = data['quaternion']
                message = f"ORIENT:{arduino_number},{w:.3f},{x:.3f},{y:.3f},{z:.3f}"
                self.unity_socket.sendto(message.encode(), (self.unity_ip, self.unity_port))

            # Enviar posiciones con EXACTAMENTE el mismo formato que en guardar_posicion.py
            message = timestamp  # Usar el timestamp recibido, no crear uno nuevo
            
            # Asegurar que enviamos exactamente 12 puntos como en guardar_posicion.py
            while len(positions_3d) < 12:
                positions_3d.append([-1, -1, -1])
            
            # Solo enviar los primeros 12 puntos si hay más
            positions_3d = positions_3d[:12]
            
            # Formato idéntico al de guardar_posicion.py
            for point in positions_3d:
                if point[0] != -1:
                    # Formatear con 3 decimales exactamente como en guardar_posicion
                    message += f",{point[0]:.3f},{point[1]:.3f},{point[2]:.3f}"
                else:
                    # Usar "NA" para puntos no detectados, igual que en guardar_posicion
                    message += ",NA,NA,NA"
            
            print(f"Enviando mensaje a Unity: {message[:100]}...")  # Debug log
            self.unity_socket.sendto(message.encode(), (self.unity_ip, self.unity_port))

        except Exception as e:
            print(f"Error enviando datos a Unity: {e}")

    def display_synced_frames(self):
        frame1, frame2 = self.find_matching_frames()
        if frame1 is not None and frame2 is not None:
            # Procesar frames con MediaPipe
            frame1_processed, keypoints1 = self.process_frame_with_pose(frame1, self.pose_detector0)
            frame2_processed, keypoints2 = self.process_frame_with_pose(frame2, self.pose_detector1)
            
            # Calcular posiciones 3D
            frame_p3ds = []
            for uv1, uv2 in zip(keypoints1, keypoints2):
                if uv1[0] == -1 or uv2[0] == -1:
                    _p3d = [-1, -1, -1]
                else:
                    _p3d = DLT(self.P0, self.P1, uv1, uv2)
                frame_p3ds.append(_p3d)
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            
            # Enviar datos a Unity por UDP
            asyncio.create_task(self.send_data_to_unity(frame_p3ds, timestamp))
            
            # Imprimir posiciones y orientaciones combinadas
            self.print_combined_data(frame_p3ds, timestamp)
            
            # Mostrar frames procesados
            combined = np.hstack((frame1_processed, frame2_processed))
            cv2.imshow(self.window_name, combined)
            cv2.waitKey(1)

    def print_combined_data(self, positions_3d, timestamp):
        """Imprime posiciones 3D y orientaciones"""
        # Limpiar consola
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Imprimir posiciones
        output = [f"\n=== Datos Combinados ==="]
        output.append(f"Timestamp: {timestamp}")
        output.append("\n--- Posiciones ---")
        
        for i, point in enumerate(positions_3d):
            name = self.get_keypoint_name(pose_keypoints[i])
            if point[0] != -1:
                output.append(f"{name}: ({point[0]:.3f}, {point[1]:.3f}, {point[2]:.3f})")
            else:
                output.append(f"{name}: No detectado")
        
        # Imprimir orientaciones
        output.append("\n--- Orientaciones ---")
        for arduino_number, data in sorted(self.orientations.items()):
            w, x, y, z = data['quaternion']
            output.append(f"Arduino {arduino_number:2d}: "
                         f"w={w:6.3f}, x={x:6.3f}, y={y:6.3f}, z={z:6.3f}")
        
        print("\n".join(output))

    def __del__(self):
        """Cerrar socket UDP al finalizar"""
        if hasattr(self, 'unity_socket'):
            self.unity_socket.close()

async def process_frame(client_id, frame, timestamp):
    global position_recorder
    position_recorder.add_frame(client_id, frame, timestamp)
    position_recorder.display_synced_frames()

async def handle_client(websocket):
    client_ip = websocket.remote_address[0]
    client_id = IP_TO_ID.get(client_ip, -1)
    
    if client_id == -1:
        print(f"Conexión rechazada de IP desconocida: {client_ip}")
        return
    
    clients.add(websocket)
    print(f"Cliente {client_id} conectado.")

    try:
        async for message in websocket:
            message_json = json.loads(message)
            if message_json["type"] == "image":
                img_data = base64.b64decode(message_json["data"])
                timestamp_received = message_json.get("timestamp_received", "N/A")
                frame = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
                
                if frame is not None:
                    await process_frame(client_id, frame, timestamp_received)

    except websockets.exceptions.ConnectionClosed:
        print(f"Cliente {client_id} desconectado")
    finally:
        clients.remove(websocket)

async def trigger_capture():
    """Envía comando de captura cada 100ms."""
    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        message = json.dumps({"type": "capture", "timestamp_sent": timestamp})
        
        websockets_clients = list(clients)
        for client in websockets_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                continue

        await asyncio.sleep(0.1)

async def main():
    global position_recorder
    position_recorder = PositionRecorder()
    
    ws_server = await websockets.serve(handle_client, "0.0.0.0", 12345)
    await position_recorder.start_unity_server()  # Iniciar servidor Unity
    
    print("Servidor iniciado.")
    print(f"Servidor de cámaras en puerto 12345")
    print(f"Servidor Unity en puerto 12346")
    print("Buscando dispositivos Arduino BLE...")
    print("Presiona Ctrl+C para detener.")
    
    try:
        await asyncio.gather(
            ws_server.wait_closed(),
            trigger_capture(),
            position_recorder.find_ble_devices()
        )
    except KeyboardInterrupt:
        print("\nDetención solicitada por el usuario")
    finally:
        position_recorder.running = False
        cv2.destroyAllWindows()

if __name__ == "__main__":
    clients = set()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDetención solicitada por el usuario")
    finally:
        cv2.destroyAllWindows()