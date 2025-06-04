## NOT USED

import cv2
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import mediapipe as mp
from utils import DLT, get_projection_matrix
import time
import asyncio
import websockets
import json
import base64
from datetime import datetime

# Configuración de MediaPipe
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Mismos puntos que en send_orientation_position_unity_FINAL.py
pose_keypoints = [
    0,   # nariz
    11,  # hombro izquierdo
    12,  # hombro derecho
    13,  # codo izquierdo
    14,  # codo derecho
    15,  # muñeca izquierda
    16,  # muñeca derecha
    23,  # cadera izquierda
    24,  # cadera derecha
    25,  # rodilla izquierda
    26,  # rodilla derecha
]

'''
    private const int NARIZ_INDEX = 0;
    private const int HOMBRO_IZQ_INDEX = 1;
    private const int HOMBRO_DER_INDEX = 2;
    private const int CODO_IZQ_INDEX = 3;
    private const int CODO_DER_INDEX = 4;
    private const int MUNECA_IZQ_INDEX = 5;
    private const int MUNECA_DER_INDEX = 6;
    private const int CADERA_IZQ_INDEX = 7;
    private const int CADERA_DER_INDEX = 8;
    private const int RODILLA_IZQ_INDEX = 9;
    private const int RODILLA_DER_INDEX = 10;
'''

# Definir conexiones para dibujar el esqueleto
skeleton_connections = [
    (0, 11),  # nariz - hombro izquierdo
    (0, 12),  # nariz - hombro derecho
    (11, 13),  # hombro izquierdo - codo izquierdo
    (13, 15),  # codo izquierdo - muñeca izquierda
    (12, 14),  # hombro derecho - codo derecho
    (14, 16),  # codo derecho - muñeca derecha
    (11, 23),  # hombro izquierdo - cadera izquierda
    (12, 24),  # hombro derecho - cadera derecha
    (23, 24),  # cadera izquierda - cadera derecha
    (23, 25),  # cadera izquierda - rodilla izquierda
    (24, 26),  # cadera derecha - rodilla derecha
    (11, 12),  # hombro izquierdo - hombro derecho
]

IP_TO_ID = {
    "192.168.7.231": 0,
    "192.168.7.230": 1
}

class Pose3DVisualizer:
    def __init__(self):
        self.window_name = "Camera Views"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        self.max_sync_diff = 100
        self.frames_buffer = {0: [], 1: []}
        
        # Inicializar detectores de pose
        self.pose_detector0 = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.pose_detector1 = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        # Obtener matrices de proyección
        self.P0 = get_projection_matrix(0)
        self.P1 = get_projection_matrix(1)
        
        # Configurar visualización 3D
        plt.ion()  # Modo interactivo
        self.fig = plt.figure(figsize=(10, 8))
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.lines = {}  # Para almacenar las líneas del esqueleto
        self.points = None  # Para almacenar los puntos
        
        # Configuración inicial del gráfico 3D
        self.setup_3d_plot()
        
    def setup_3d_plot(self):
        """Configuración inicial del gráfico 3D"""
        self.ax.set_title('Reconstrucción 3D de pose')
        self.ax.set_xlabel('Z')  # Z en el eje X del gráfico
        self.ax.set_ylabel('X')  # X en el eje Y del gráfico
        self.ax.set_zlabel('Y')  # Y sigue en el eje Z
        
        # Establecer límites iniciales
        self.ax.set_xlim(-1, 1)
        self.ax.set_ylim(-1, 1)
        self.ax.set_zlim(-0.5, 2)  # Ajustar para que la persona esté de pie
    
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
        """Detecta puntos de pose en un frame"""
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
                mp_pose.POSE_CONNECTIONS
            )
        else:
            keypoints = [[-1, -1]] * len(pose_keypoints)
            
        return frame_bgr, keypoints
        
    def add_frame(self, client_id, frame, timestamp):
        """Añade un frame al buffer"""
        self.frames_buffer[client_id].append((timestamp, frame))
        if len(self.frames_buffer[client_id]) > 5:
            self.frames_buffer[client_id].pop(0)
            
    def find_matching_frames(self):
        """Busca frames sincronizados entre ambas cámaras"""
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
        
    def update_3d_visualization(self, positions_3d):
        """Actualiza la visualización 3D con las nuevas posiciones"""
        # Limpiar el gráfico para la nueva postura
        self.ax.clear()
        self.setup_3d_plot()
        
        # Convertir a formato numpy para manipulación
        positions = np.array(positions_3d)
        valid_points = positions[:, 0] != -1
        
        # Revisar si hay puntos válidos antes de intentar dibujar
        if not np.any(valid_points):
            return
            
        # Aplicar rotación 180° sobre eje Z + 90° hacia arriba (eje X)
        rotated_positions = []
        for point in positions_3d:
            if point[0] != -1:
                # Aplicamos ambas rotaciones: 180° en Z y 90° en X
                rotated_positions.append([-point[2], -point[1], -point[0]])
        
        # Si no hay puntos después de la rotación, salir
        if not rotated_positions:
            return
            
        # Convertir a numpy para calcular límites
        rotated_positions = np.array(rotated_positions)
        
        # Calcular límites con margen para mejor visualización
        margin = 0.5  # Aumentado el margen para mejor visibilidad
        min_coords = np.min(rotated_positions, axis=0) - margin
        max_coords = np.max(rotated_positions, axis=0) + margin
        
        # Establecer límites asegurando que el muñeco está centrado
        if not np.any(np.isnan(min_coords)) and not np.any(np.isnan(max_coords)):
            self.ax.set_xlim(min_coords[0], max_coords[0])
            self.ax.set_ylim(min_coords[1], max_coords[1])
            self.ax.set_zlim(min_coords[2], max_coords[2])
        
        # Dibujar puntos (círculos) con la nueva rotación
        for i, point in enumerate(positions_3d):
            if point[0] != -1:
                name = self.get_keypoint_name(pose_keypoints[i])
                # Aplicar rotación combinada
                self.ax.scatter(-point[2], -point[1], -point[0], c='r', marker='o', s=50)
                self.ax.text(-point[2], -point[1], -point[0], name, size=8)
        
        # Dibujar las conexiones del esqueleto (excluyendo conexiones a la nariz)
        for start_idx, end_idx in skeleton_connections:
            # Omitir las conexiones que van a la nariz (índice 0)
            if start_idx == 0 or end_idx == 0:
                continue
                
            if start_idx in pose_keypoints and end_idx in pose_keypoints:
                start_pose_idx = pose_keypoints.index(start_idx)
                end_pose_idx = pose_keypoints.index(end_idx)
                
                if (positions_3d[start_pose_idx][0] != -1 and 
                    positions_3d[end_pose_idx][0] != -1):
                    start_point = positions_3d[start_pose_idx]
                    end_point = positions_3d[end_pose_idx]
                    self.ax.plot(
                        [-start_point[2], -end_point[2]], 
                        [-start_point[1], -end_point[1]], 
                        [-start_point[0], -end_point[0]], 
                        'b-', linewidth=2
                    )
        
        # Ajustar vista para la nueva orientación
        self.ax.view_init(elev=30, azim=-75)
        
        # Actualizar el gráfico
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
    
    def process_synchronized_frames(self):
        """Procesa frames sincronizados y actualiza visualización"""
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
            
            # Actualizar visualización 3D
            self.update_3d_visualization(frame_p3ds)
            
            # Mostrar frames procesados 2D
            combined = np.hstack((frame1_processed, frame2_processed))
            cv2.imshow(self.window_name, combined)
            cv2.waitKey(1)
            
            return True
        return False

async def process_frame(client_id, frame, timestamp):
    """Procesa un frame recibido de una cámara"""
    visualizer.add_frame(client_id, frame, timestamp)
    visualizer.process_synchronized_frames()

async def handle_client(websocket):
    """Maneja la conexión con un cliente (cámara)"""
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
    global visualizer
    visualizer = Pose3DVisualizer()
    
    ws_server = await websockets.serve(handle_client, "0.0.0.0", 12345)
    
    print("Servidor iniciado en puerto 12345")
    print("Esperando conexión de cámaras...")
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
        plt.close('all')

if __name__ == "__main__":
    clients = set()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDetención solicitada por el usuario")
    finally:
        cv2.destroyAllWindows()
        plt.close('all')