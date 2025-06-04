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

# Configuración de MediaPipe y constantes (igual que en server.py)
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

IP_TO_ID = {
    "192.168.7.16": 0,
    "192.168.7.17": 1
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
        
        # Crear directorio media si no existe
        os.makedirs('media', exist_ok=True)
        
        # Crear archivo de registro con timestamp
        self.timestamp_inicio = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename = f'media/posiciones_{self.timestamp_inicio}.txt'
        
        # Escribir encabezado en el archivo
        with open(self.filename, 'w') as f:
            # Escribir primera línea con nombres de columnas
            header = ["timestamp"]
            for i, kpt in enumerate(pose_keypoints):
                name = self.get_keypoint_name(kpt)
                header.extend([f"{name}_x", f"{name}_y", f"{name}_z"])
            f.write(",".join(header) + "\n")
    
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

    def save_positions(self, points_3d, timestamp):
        """Guarda las posiciones 3D con su timestamp en una sola línea"""
        with open(self.filename, 'a') as f:
            # Empezar con el timestamp
            line = [timestamp]
            
            # Añadir todas las coordenadas
            for point in points_3d:
                if point[0] != -1:
                    line.extend([f"{point[0]:.3f}", f"{point[1]:.3f}", f"{point[2]:.3f}"])
                else:
                    line.extend(["NA", "NA", "NA"])  # Para puntos no detectados
            
            # Escribir la línea completa
            f.write(",".join(line) + "\n")

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
            
            # Guardar posiciones con timestamp actual
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            self.save_positions(frame_p3ds, timestamp)
            
            # Mostrar frames procesados
            combined = np.hstack((frame1_processed, frame2_processed))
            cv2.imshow(self.window_name, combined)
            cv2.waitKey(1)

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
    print(f"Servidor iniciado. Guardando posiciones en: {position_recorder.filename}")
    print("Presiona Ctrl+C para detener.")
    
    try:
        await asyncio.gather(
            ws_server.wait_closed(),
            trigger_capture()
        )
    except KeyboardInterrupt:
        print("\nDetención solicitada por el usuario")
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    clients = set()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDetención solicitada por el usuario")
    finally:
        cv2.destroyAllWindows() 