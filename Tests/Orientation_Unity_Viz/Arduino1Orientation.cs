using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Text;

public class Arduino1Orientation : MonoBehaviour
{
    [Header("Network Settings")]
    [SerializeField] private string udpAddress = "127.0.0.1";
    [SerializeField] private int udpPort = 5065;
    
    [Header("Target Settings")]
    [SerializeField] private GameObject targetObject;
    [SerializeField] private bool applyRotationDirectly = true;
    [SerializeField] private float smoothingFactor = 10f;
    
    [Header("Axis Adjustments")]
    [SerializeField] private bool invertX = false;
    [SerializeField] private bool invertY = false;
    [SerializeField] private bool invertZ = false;
    
    [Header("Debug")]
    [SerializeField] private bool debugMode = true;
    
    private UdpClient udpClient;
    private Thread receiverThread;
    private bool isRunning = true;
    private Quaternion targetRotation;
    private bool newRotationReceived = false;
    
    // Inicialización
    void Start()
    {
        if (targetObject == null)
        {
            targetObject = this.gameObject;
            Debug.Log("No se asignó objeto destino. Usando este objeto.");
        }
        
        try
        {
            udpClient = new UdpClient();
            udpClient.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
            udpClient.Client.Bind(new IPEndPoint(IPAddress.Parse(udpAddress), udpPort));
            
            receiverThread = new Thread(new ThreadStart(ReceiveData));
            receiverThread.IsBackground = true;
            receiverThread.Start();
            
            Debug.Log($"Receptor UDP iniciado en {udpAddress}:{udpPort}");
        }
        catch (Exception e)
        {
            Debug.LogError($"Error iniciando UDP: {e.Message}");
        }
    }
    
    // Bucle principal Update
    void Update()
    {
        if (newRotationReceived)
        {
            if (applyRotationDirectly)
            {
                targetObject.transform.rotation = targetRotation;
            }
            else
            {
                // Suavizado opcional
                targetObject.transform.rotation = Quaternion.Slerp(
                    targetObject.transform.rotation,
                    targetRotation,
                    Time.deltaTime * smoothingFactor
                );
            }
            
            newRotationReceived = false;
        }
    }
    
    // Función que corre en el thread secundario
    private void ReceiveData()
    {
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, udpPort);
        
        while (isRunning)
        {
            try
            {
                byte[] data = udpClient.Receive(ref remoteEndPoint);
                string message = Encoding.UTF8.GetString(data);
                
                if (debugMode)
                {
                    Debug.Log($"Recibido: {message}");
                }
                
                ProcessMessage(message);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"Error recibiendo datos: {e.Message}");
            }
        }
    }
    
    // Procesar mensaje UDP
    private void ProcessMessage(string message)
    {
        if (message.StartsWith("ORIENT:"))
        {
            string[] parts = message.Substring(7).Split(',');
            
            if (parts.Length >= 5)
            {
                int arduinoNumber = int.Parse(parts[0]);
                
                // Asegurarse de que es el Arduino 1
                if (arduinoNumber == 1)
                {
                    // Primero creamos el cuaternión recibido
                    Quaternion receivedRotation = new Quaternion(
                        float.Parse(parts[2]), // x
                        float.Parse(parts[3]), // y
                        float.Parse(parts[4]), // z
                        float.Parse(parts[1])  // w
                    );
                    
                    ApplyRotation(receivedRotation);
                }
            }
        }
    }
    
    // Aplicar la rotación recibida
    private void ApplyRotation(Quaternion receivedRotation)
    {
        // En lugar de usar ángulos de Euler, vamos a modificar directamente el cuaternión
        // Esto ayuda a evitar el problema de "gimbal lock"
        
        // Primero reordenamos los componentes para alinearlos correctamente
        Quaternion reorientedRotation = new Quaternion(
            receivedRotation.x,  // Mantenemos x
            -receivedRotation.z, // Negamos z y lo asignamos a y
            receivedRotation.y,  // y va a z
            receivedRotation.w   // w se mantiene igual
        );
        
        // Aplicamos una rotación adicional para corregir la orientación inicial (si es necesario)
        Quaternion correctionRotation = Quaternion.Euler(0, 180, 0); // Ajusta estos valores según sea necesario
        targetRotation = correctionRotation * reorientedRotation;
        
        // Aplicar inversiones adicionales si están configuradas
        if (invertX || invertY || invertZ)
        {
            Vector3 eulerAngles = targetRotation.eulerAngles;
            
            if (invertX) eulerAngles.x = 360 - eulerAngles.x;
            if (invertY) eulerAngles.y = 360 - eulerAngles.y;
            if (invertZ) eulerAngles.z = 360 - eulerAngles.z;
            
            targetRotation = Quaternion.Euler(eulerAngles);
        }
        
        if (debugMode)
        {
            Debug.Log($"Quaternion recibido: w={receivedRotation.w}, x={receivedRotation.x}, y={receivedRotation.y}, z={receivedRotation.z}");
            Debug.Log($"Quaternion reorientado: w={reorientedRotation.w}, x={reorientedRotation.x}, y={reorientedRotation.y}, z={reorientedRotation.z}");
            Debug.Log($"Ángulos finales: {targetRotation.eulerAngles}");
        }
        
        newRotationReceived = true;
    }
    
    // Limpieza al desactivar o cerrar
    private void OnDisable()
    {
        CleanUp();
    }
    
    private void OnApplicationQuit()
    {
        CleanUp();
    }
    
    private void CleanUp()
    {
        isRunning = false;
        
        if (udpClient != null)
        {
            udpClient.Close();
            udpClient = null;
        }
        
        if (receiverThread != null && receiverThread.IsAlive)
        {
            receiverThread.Join(1000);
            receiverThread = null;
        }
    }
}