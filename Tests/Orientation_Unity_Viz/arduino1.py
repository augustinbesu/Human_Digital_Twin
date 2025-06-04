import asyncio
import socket
from bleak import BleakScanner, BleakClient
import re
import time

# Configuración
DEVICE_NAME_PATTERN = r"Arduino(\d+)"
CHARACTERISTIC_UUID = "2A5B"  # UUID del característico BLE donde el Arduino envía los datos
UNITY_IP = "127.0.0.1"
UNITY_PORT = 5065  # Puerto UDP para Unity

class ArduinoOrientationSender:
    def __init__(self):
        # Configuración UDP
        self.unity_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.unity_ip = UNITY_IP
        self.unity_port = UNITY_PORT
        
        # Estado
        self.arduino1_client = None
        self.arduino1_address = None
        self.running = True
        
        print(f"ArduinoOrientationSender iniciado - enviando a {UNITY_IP}:{UNITY_PORT}")
    
    async def find_arduino1(self):
        """Busca específicamente el Arduino 1"""
        print("Buscando Arduino 1...")
        
        while self.running and self.arduino1_client is None:
            try:
                devices = await BleakScanner.discover()
                for device in devices:
                    if device.name and (match := re.match(DEVICE_NAME_PATTERN, device.name)):
                        arduino_number = int(match.group(1))
                        if arduino_number == 1:  # Solo nos interesa Arduino 1
                            print(f"Arduino 1 encontrado: {device.name} ({device.address})")
                            self.arduino1_address = device.address
                            return
            except Exception as e:
                print(f"Error buscando dispositivos: {e}")
            
            print("Arduino 1 no encontrado. Reintentando en 3 segundos...")
            await asyncio.sleep(3)
    
    async def connect_to_arduino1(self):
        """Conectarse al Arduino 1 y manejar los datos"""
        if not self.arduino1_address:
            print("No se encontró la dirección del Arduino 1")
            return
        
        while self.running:
            try:
                print(f"Conectando a Arduino 1 ({self.arduino1_address})...")
                client = BleakClient(self.arduino1_address)
                await client.connect()
                print("Conectado a Arduino 1!")
                
                # Configurar manejador de notificaciones
                def notification_handler(sender, data):
                    try:
                        # Parsear los datos (formato esperado: w,x,y,z)
                        w, x, y, z = map(float, data.decode().split(','))
                        
                        # Enviar a Unity
                        message = f"ORIENT:1,{w:.3f},{x:.3f},{y:.3f},{z:.3f}"
                        self.unity_socket.sendto(message.encode(), (self.unity_ip, self.unity_port))
                        print(f"Enviado: {message}")
                    except Exception as e:
                        print(f"Error procesando datos: {e}")
                
                # Suscribirse a las notificaciones
                await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                
                # Mantener la conexión activa
                while self.running and client.is_connected:
                    await asyncio.sleep(1)
                
                # Si llegamos aquí, se perdió la conexión
                await client.disconnect()
                print("Desconectado de Arduino 1. Reintentando en 3 segundos...")
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"Error de conexión con Arduino 1: {e}")
                await asyncio.sleep(3)
    
    async def run(self):
        """Ejecuta el flujo completo"""
        try:
            await self.find_arduino1()
            if self.arduino1_address:
                await self.connect_to_arduino1()
        except KeyboardInterrupt:
            print("\nDetención solicitada por el usuario")
        finally:
            self.running = False
            if hasattr(self, 'unity_socket'):
                self.unity_socket.close()
            print("ArduinoOrientationSender finalizado")

# Punto de entrada
async def main():
    sender = ArduinoOrientationSender()
    await sender.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDetención solicitada por el usuario")