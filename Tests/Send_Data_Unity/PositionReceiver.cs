/* USING BALL OBJECTS TO SHOW POSITION (WITHOUT HUMANOID MODEL) */

using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

public class PositionReceiver : MonoBehaviour
{
    [Header("UDP Configuration")]
    public int port = 5065;
    
    [Header("Body Part Spheres")]
    public Transform nariz;
    public Transform hombro_izq;
    public Transform codo_izq;
    public Transform muneca_izq;
    public Transform cadera_izq;
    public Transform hombro_der;
    public Transform codo_der;
    public Transform muneca_der;
    public Transform cadera_der;
    public Transform rodilla_izq;
    public Transform rodilla_der;
    
    private UdpClient udpClient;
    private Thread udpThread;
    private bool isReceiving = false;
    private Transform[] bodyParts;
    private UnityMainThreadDispatcher dispatcher;
    
    void Start()
    {
        // Inicializar array de partes del cuerpo - ahora 11 elementos
        bodyParts = new Transform[] {
            nariz, hombro_izq, codo_izq, muneca_izq, cadera_izq,
            hombro_der, codo_der, muneca_der, cadera_der, rodilla_izq, rodilla_der
        };
        
        // Inicializar el dispatcher en el hilo principal
        dispatcher = UnityMainThreadDispatcher.Instance();
        
        StartReceiving();
    }
    
    void StartReceiving()
    {
        try
        {
            udpClient = new UdpClient(port);
            isReceiving = true;
            udpThread = new Thread(new ThreadStart(ReceiveData));
            udpThread.Start();
            Debug.Log($"Started UDP receiver on port {port}");
        }
        catch (Exception e)
        {
            Debug.LogError($"Error starting UDP receiver: {e.Message}");
        }
    }
    
    void ReceiveData()
    {
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, port);
        
        while (isReceiving)
        {
            try
            {
                byte[] data = udpClient.Receive(ref remoteEndPoint);
                string message = Encoding.UTF8.GetString(data);
                ProcessPositionData(message);
            }
            catch (Exception e)
            {
                if (isReceiving)
                {
                    Debug.LogError($"Error receiving UDP data: {e.Message}");
                }
            }
        }
    }
    
    void ProcessPositionData(string message)
    {
        try
        {
            string[] parts = message.Split(',');
            
            // El primer elemento es el timestamp, los siguientes son las posiciones
            if (parts.Length >= 34) // 1 timestamp + 11 partes * 3 coordenadas
            {
                // Procesar posiciones (saltar el timestamp)
                for (int i = 0; i < bodyParts.Length && i < 11; i++)
                {
                    if (bodyParts[i] != null)
                    {
                        int startIndex = 1 + (i * 3); // +1 para saltar timestamp
                        
                        if (startIndex + 2 < parts.Length)
                        {
                            // Leer coordenadas del archivo
                            float fileX = float.Parse(parts[startIndex]) * 0.00014f;
                            float fileY = float.Parse(parts[startIndex + 1]) * 0.00014f;
                            float fileZ = float.Parse(parts[startIndex + 2]) * 0.00014f;
                            
                            // Aplicar rotación de 90° en Y para orientar correctamente
                            // Rotación de 90°: X' = Z, Y' = Y, Z' = -X
                            float unityX = fileZ;                    // Z del archivo -> X Unity
                            float unityY = -fileZ;                   // Z del archivo -> Y Unity (invertido)
                            float unityZ = -fileY;                   // Y del archivo -> Z Unity (invertido)
                            
                            // Crear Vector3 con las coordenadas rotadas
                            Vector3 newPosition = new Vector3(unityX, unityY, unityZ);
                            UpdatePositionOnMainThread(bodyParts[i], newPosition);
                        }
                    }
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"Error processing position data: {e.Message}");
        }
    }
    
    void UpdatePositionOnMainThread(Transform bodyPart, Vector3 position)
    {
        // Usar el dispatcher ya inicializado
        if (dispatcher != null)
        {
            dispatcher.Enqueue(() => {
                if (bodyPart != null)
                {
                    bodyPart.position = position;
                }
            });
        }
    }
    
    void OnDestroy()
    {
        StopReceiving();
    }
    
    void OnApplicationQuit()
    {
        StopReceiving();
    }
    
    void StopReceiving()
    {
        isReceiving = false;
        
        if (udpThread != null && udpThread.IsAlive)
        {
            udpThread.Join(1000);
        }
        
        if (udpClient != null)
        {
            udpClient.Close();
        }
    }
}

// Clase auxiliar para ejecutar código en el hilo principal
public class UnityMainThreadDispatcher : MonoBehaviour
{
    private static UnityMainThreadDispatcher _instance;
    private readonly Queue<System.Action> _executionQueue = new Queue<System.Action>();
    
    public static UnityMainThreadDispatcher Instance()
    {
        if (_instance == null)
        {
            _instance = FindFirstObjectByType<UnityMainThreadDispatcher>();
            if (_instance == null)
            {
                GameObject go = new GameObject("MainThreadDispatcher");
                _instance = go.AddComponent<UnityMainThreadDispatcher>();
                DontDestroyOnLoad(go);
            }
        }
        return _instance;
    }
    
    public void Enqueue(System.Action action)
    {
        lock (_executionQueue)
        {
            _executionQueue.Enqueue(action);
        }
    }
    
    void Update()
    {
        lock (_executionQueue)
        {
            while (_executionQueue.Count > 0)
            {
                _executionQueue.Dequeue().Invoke();
            }
        }
    }
}
