// Augustin Alexandru Besu - Escáner I2C 

#include <Wire.h>  // Librería para comunicación I2C

void setup()
{
  Serial.begin(115200);
  // Inicializamos el bus I2C en los pines 21 (SDA) y 22 (SCL) del ESP32
  Wire.begin(21, 22);  
}

void Scanner ()
{
  Serial.println();
  Serial.println("Escáner I2C en progreso...");
  byte count = 0;

  // Recorremos todas las direcciones I2C posibles (de 8 a 120)
  for (byte i = 8; i < 120; i++)
  {
    Wire.beginTransmission(i);  // Iniciar transmisión I2C a la dirección (i)
    
    // Si el dispositivo responde (ACK), la función endTransmission devuelve 0
    if (Wire.endTransmission() == 0)
    {
      Serial.print("Dirección encontrada: ");
      Serial.print(i, DEC);  // Imprime la dirección en decimal
      Serial.print(" (0x");
      Serial.print(i, HEX);  // Imprime la dirección en hexadecimal
      Serial.println(")");
      count++;
    }
  }

  // Informe final con el número de dispositivos encontrados
  Serial.print("Total de dispositivos encontrados: ");      
  Serial.print(count, DEC);  
  Serial.println(" dispositivo(s).");
}

void loop()
{
  Scanner(); 
  delay(1000);  // Pausa de 1 segundo antes del próximo escaneo
}
