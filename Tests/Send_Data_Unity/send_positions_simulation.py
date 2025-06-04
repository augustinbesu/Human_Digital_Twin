import pandas as pd
import socket
import time
from datetime import datetime
import numpy as np

# Configuración
UDP_IP = "127.0.0.1"
UDP_PORT = 5065
POSITIONS_FILE = 'posiciones.txt'
SIMULATION_FPS = 10  # Frecuencia de envío

class PositionSimulator:
    def __init__(self):
        # Cargar datos de posición
        self.positions_data = pd.read_csv(POSITIONS_FILE)
        self.current_frame = 0
        self.start_time = None
        
        # Configuración UDP
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Lista de todas las partes del cuerpo
        self.body_parts = [
            "nariz", "hombro_izq", "codo_izq", "muneca_izq", "cadera_izq",
            "hombro_der", "codo_der", "muneca_der", "cadera_der", "rodilla_izq", "rodilla_der", "tobillo_izq"
        ]
        
    def get_current_position_frame(self):
        """Obtiene el frame actual basado en el tiempo transcurrido"""
        if self.start_time is None:
            return None

        current_time = datetime.now()
        first_timestamp = pd.to_datetime(self.positions_data['timestamp'].iloc[0])
        elapsed_time = (current_time - self.start_time).total_seconds()
        
        # Calcular qué frame debería mostrarse
        timestamps = pd.to_datetime(self.positions_data['timestamp'])
        time_diffs = (timestamps - first_timestamp).dt.total_seconds()
        
        # Encontrar el frame más cercano al tiempo actual
        frame_index = np.argmin(np.abs(time_diffs - elapsed_time))
        return self.positions_data.iloc[frame_index]

    def send_positions(self, frame):
        """Envía todas las posiciones del cuerpo por UDP"""
        try:
            # Crear mensaje con todas las posiciones
            positions = []
            for part in self.body_parts:
                pos_x = float(frame[f"{part}_x"])
                pos_y = float(frame[f"{part}_y"])
                pos_z = float(frame[f"{part}_z"])
                positions.extend([pos_x, pos_y, pos_z])
            
            # Formatear mensaje con todas las posiciones
            # Formato: timestamp,pos1_x,pos1_y,pos1_z,pos2_x,pos2_y,pos2_z,...
            timestamp = frame['timestamp']
            positions_str = ",".join([f"{pos:.3f}" for pos in positions])
            message = f"{timestamp},{positions_str}"
            
            # Enviar por UDP
            self.udp_socket.sendto(message.encode(), (UDP_IP, UDP_PORT))
            
            # Mostrar mensaje más compacto para debug
            print(f"Frame enviado - Timestamp: {timestamp}")
            
        except Exception as e:
            print(f"Error enviando datos: {e}")

    def run(self):
        """Ejecuta la simulación"""
        print("Iniciando simulación de posiciones...")
        print(f"Enviando datos de {len(self.body_parts)} partes del cuerpo")
        print(f"Partes del cuerpo: {', '.join(self.body_parts)}")
        self.start_time = datetime.now()
        
        try:
            while True:
                frame = self.get_current_position_frame()
                if frame is not None:
                    self.send_positions(frame)
                time.sleep(1.0/SIMULATION_FPS)  # Mantener FPS constante
                
        except KeyboardInterrupt:
            print("\nSimulación detenida por el usuario")
        finally:
            self.udp_socket.close()

if __name__ == "__main__":
    simulator = PositionSimulator()
    simulator.run() 