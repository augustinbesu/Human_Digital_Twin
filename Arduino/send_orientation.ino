#include <ArduinoBLE.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <utility/imumaths.h>

// Configuración del sensor BNO055
Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x29);

// Configuración BLE 
BLEService sensorService("0001"); // BLE Sensor Service
BLECharacteristic orientationCharacteristic("2A5B", BLERead | BLENotify | BLEBroadcast, 50);

// Cambia este número para cada Arduino (1, 2, 3...)
#define ARDUINO_NUMBER 1

void setup() {
  Serial.begin(115200);
  
  // Configurar BNO055
  if (!bno.begin()) {
    Serial.println("No se pudo inicializar el BNO055!");
    while (1);
  }
  bno.setExtCrystalUse(true);
  Serial.println("BNO055 inicializado correctamente");
  
  // Inicializar BLE
  if (!BLE.begin()) {
    Serial.println("Fallo al iniciar BLE!");
    while (1);
  }
  
  // Configurar nombre del dispositivo (debe coincidir con el patrón en Python)
  String deviceName = "Ard" + String(ARDUINO_NUMBER);
  BLE.setLocalName(deviceName.c_str());
  BLE.setDeviceName(deviceName.c_str());
  
  // Configurar servicio y característica BLE
  BLE.setAdvertisedService(sensorService);
  sensorService.addCharacteristic(orientationCharacteristic);
  BLE.addService(sensorService);
  
  // Configuración de broadcast
  BLE.setAdvertisingInterval(100); // Intervalo en ms (más bajo = más frecuente)
  // Para broadcast sin conexión, usar
  orientationCharacteristic.broadcast();
  
  // Iniciar anuncio BLE
  BLE.advertise();
  Serial.println("BLE configurado y anunciando como " + deviceName);
}

void loop() {
  // Actualizar conexión BLE
  BLE.poll();
  
  // Obtener cuaternión del BNO055
  imu::Quaternion quat = bno.getQuat();
  
  // Aumentar el tamaño del buffer y precisión
  char quatData[30]; // Buffer más grande
  snprintf(quatData, sizeof(quatData), "%.4f,%.4f,%.4f,%.4f", 
           quat.w(), quat.x(), quat.y(), quat.z());
  
  // Verificar que tenemos 4 valores antes de enviar
  int commaCount = 0;
  for (int i = 0; i < strlen(quatData); i++) {
    if (quatData[i] == ',') commaCount++;
  }
  
  if (commaCount == 3) { // Aseguramos tener 3 comas = 4 valores
    // Enviar los datos por BLE
    orientationCharacteristic.writeValue(quatData);
    
    // También mostrar por Serial para depuración
    Serial.println(quatData);
  } else {
    Serial.print("Error de formato: ");
    Serial.println(quatData);
  }
  
  // Estado de calibración para depuración
  uint8_t system_status, self_test, system_error;
  bno.getSystemStatus(&system_status, &self_test, &system_error);
  
  uint8_t sys, gyro, accel, mag;
  bno.getCalibration(&sys, &gyro, &accel, &mag);
  
  // Esperar un poco antes de la próxima lectura
  delay(50);
}