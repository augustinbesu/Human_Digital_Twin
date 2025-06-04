// FIRST VERSION - ABSOLUTE POSITION AND ORIENTATION

using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Collections.Concurrent;
using System.Collections.Generic;

public class BodyUDPReceiver : MonoBehaviour
{
    [Header("Network Settings")]
    [SerializeField] private string udpAddress = "127.0.0.1";
    [SerializeField] private int udpPort = 5065;

    [Header("Body Parts")]
    [SerializeField] private GameObject nariz;
    [SerializeField] private GameObject hombroIzq;
    [SerializeField] private GameObject hombroDer;
    [SerializeField] private GameObject codoIzq;
    [SerializeField] private GameObject codoDer;
    [SerializeField] private GameObject munecaIzq;
    [SerializeField] private GameObject munecaDer;
    [SerializeField] private GameObject caderaIzq;
    [SerializeField] private GameObject caderaDer;
    [SerializeField] private GameObject rodillaIzq;
    [SerializeField] private GameObject rodillaDer;
    [SerializeField] private GameObject spine1_M; // Articulación para la columna baja
    [SerializeField] private GameObject root_M; // Articulación para la raíz
    [SerializeField] private GameObject chest_M; // Nueva articulación para el pecho
    [SerializeField] private GameObject spine2_M; // Nueva articulación para la columna media

    [Header("Calculated Joints Settings")]
    [SerializeField] private float spineVerticalOffset = 0.1f; // Ajuste vertical para la columna
    [SerializeField] private float rootVerticalOffset = 0.05f; // Valor moderado para subir ligeramente el root_M
    [SerializeField] private bool calculateSpine = true; // Calcular spine1_M
    [SerializeField] private bool calculateRoot = true; // Calcular root_M
    [SerializeField] private bool calculateChest = true; // Calcular chest_M
    [SerializeField] private bool calculateSpine2 = true; // Calcular spine2_M

    [Header("Smoothing Settings")]
    [SerializeField] private bool enableSmoothing = true; // Activar/desactivar suavizado
    [SerializeField][Range(0f, 0.95f)] private float smoothingFactor = 0.5f; // Factor de suavizado (mayor = más suave pero más retardo)
    [SerializeField][Range(0f, 0.1f)] private float jitterThreshold = 0.005f; // Umbral para ignorar pequeños cambios (metros)
    [SerializeField] private bool adaptiveSmoothing = true; // Si es true, aplica más suavizado a movimientos pequeños

    [Header("Debug")]
    [SerializeField] private bool debugMode = true;

    [Header("Position Settings")]
    private const float POSITION_SCALE = 0.00014f; // Valor fijo de escala
    [SerializeField] private bool invertXAxis = false;
    [SerializeField] private bool invertYAxis = true; // Invertir Y para corregir cara hacia abajo
    [SerializeField] private bool invertZAxis = true;

    private UdpClient udpClient;
    private Thread udpThread;
    private bool isReceiving = true;
    private ConcurrentQueue<Vector3[]> positionsQueue = new ConcurrentQueue<Vector3[]>();
    private GameObject[] bodyParts;
    private Vector3[] previousPositions; // Array para almacenar posiciones previas
    private bool isFirstFrame = true;

    // Constantes para acceder a las posiciones (Orden según MediaPipe)
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

    // Índices para las articulaciones calculadas
    private const int SPINE_INDEX = 12;
    private const int ROOT_INDEX = 13;
    private const int CHEST_INDEX = 14;
    private const int SPINE2_INDEX = 15;

    // Cola para orientaciones recibidas
    private ConcurrentQueue<KeyValuePair<int, Quaternion>> orientationsQueue = new ConcurrentQueue<KeyValuePair<int, Quaternion>>();

    // Mapeo de números de Arduino a índices de partes del cuerpo
    private Dictionary<int, int> arduinoToBodyPartMap = new Dictionary<int, int>()
    {
        { 1, NARIZ_INDEX },       // Arduino 1 controla la nariz
        { 2, HOMBRO_IZQ_INDEX },  // Arduino 2 controla el hombro izquierdo
        { 3, HOMBRO_DER_INDEX },  // Arduino 3 controla el hombro derecho
        { 4, CODO_IZQ_INDEX },    // Arduino 4 controla el codo izquierdo
        { 5, CODO_DER_INDEX },    // Arduino 5 controla el codo derecho
        { 6, MUNECA_IZQ_INDEX },  // Arduino 6 controla la muñeca izquierda
        { 7, MUNECA_DER_INDEX },  // Arduino 7 controla la muñeca derecha
        { 8, CADERA_IZQ_INDEX },  // Arduino 8 controla la cadera izquierda
        { 9, CADERA_DER_INDEX },  // Arduino 9 controla la cadera derecha
        { 10, RODILLA_IZQ_INDEX },// Arduino 10 controla la rodilla izquierda
        { 11, RODILLA_DER_INDEX } // Arduino 11 controla la rodilla derecha
    };

    // Definir las correcciones de ejes para cada Arduino
    private Dictionary<int, Vector3> arduinoAxisCorrections = new Dictionary<int, Vector3>()
    {
        // Formato: {Arduino ID, Vector3(x, y, z) para Euler}
        { 1, new Vector3(0, -90, 0) },
        { 2, new Vector3(0, -90, 0) },
        { 3, new Vector3(-180, -270, -180) },
        { 4, new Vector3(0, -90, 0) },
        { 5, new Vector3(-180, -270, -180) },
        { 6, new Vector3(180, 90, 180) },
        { 7, new Vector3(-180, -270, -180) },
        { 8, new Vector3(0, -90, 0) },
        { 9, new Vector3(-180, -270, -180) },
        { 10, new Vector3(0, -90, 0) },
        { 11, new Vector3(-180, -270, -180) }
    };

    void Start()
    {
        // Asegurarse de que bodyParts tiene suficiente capacidad (al menos 16 elementos)
        bodyParts = new GameObject[16]; // Garantiza que hay espacio para los 16 índices definidos

        // Asignar las partes del cuerpo directamente
        bodyParts[NARIZ_INDEX] = nariz;
        bodyParts[HOMBRO_IZQ_INDEX] = hombroIzq;
        bodyParts[HOMBRO_DER_INDEX] = hombroDer;
        bodyParts[CODO_IZQ_INDEX] = codoIzq;
        bodyParts[CODO_DER_INDEX] = codoDer;
        bodyParts[MUNECA_IZQ_INDEX] = munecaIzq;
        bodyParts[MUNECA_DER_INDEX] = munecaDer;
        bodyParts[CADERA_IZQ_INDEX] = caderaIzq;
        bodyParts[CADERA_DER_INDEX] = caderaDer;
        bodyParts[RODILLA_IZQ_INDEX] = rodillaIzq;
        bodyParts[RODILLA_DER_INDEX] = rodillaDer;

        // Las articulaciones calculadas se agregan después
        bodyParts[SPINE_INDEX] = spine1_M;
        bodyParts[ROOT_INDEX] = root_M;
        bodyParts[CHEST_INDEX] = chest_M;
        bodyParts[SPINE2_INDEX] = spine2_M;

        // Inicializar array de posiciones previas
        previousPositions = new Vector3[16]; // Mismo tamaño que bodyParts
        for (int i = 0; i < previousPositions.Length; i++)
        {
            previousPositions[i] = Vector3.zero;
        }

        // Crear automáticamente las articulaciones calculadas si no existen
        if (calculateSpine && spine1_M == null)
        {
            spine1_M = new GameObject("spine1_M");
            bodyParts[SPINE_INDEX] = spine1_M;
            Debug.Log("Objeto spine1_M creado automáticamente");
        }

        if (calculateRoot && root_M == null)
        {
            root_M = new GameObject("root_M");
            bodyParts[ROOT_INDEX] = root_M;
            Debug.Log("Objeto root_M creado automáticamente");
        }

        if (calculateChest && chest_M == null)
        {
            chest_M = new GameObject("chest_M");
            bodyParts[CHEST_INDEX] = chest_M;
            Debug.Log("Objeto chest_M creado automáticamente");
        }

        if (calculateSpine2 && spine2_M == null)
        {
            spine2_M = new GameObject("spine2_M");
            bodyParts[SPINE2_INDEX] = spine2_M;
            Debug.Log("Objeto spine2_M creado automáticamente");
        }

        try
        {
            udpClient = new UdpClient();
            udpClient.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
            udpClient.Client.Bind(new IPEndPoint(IPAddress.Parse(udpAddress), udpPort));

            udpThread = new Thread(new ThreadStart(ReceiveData));
            udpThread.IsBackground = true;
            udpThread.Start();

            Debug.Log($"UDP Receiver iniciado en puerto {udpPort}");
        }
        catch (Exception e)
        {
            Debug.LogError($"Error iniciando UDP: {e.Message}");
        }
    }

    void Update()
    {
        if (positionsQueue.TryDequeue(out Vector3[] positions))
        {
            // Verificar que las posiciones no excedan el tamaño del array
            if (positions.Length > bodyParts.Length)
            {
                Debug.LogWarning($"Recibidas más posiciones ({positions.Length}) que partes del cuerpo ({bodyParts.Length})");
            }

            // Actualizar posición de cada parte del cuerpo asignada
            for (int i = 0; i < positions.Length && i < bodyParts.Length && i < 12; i++)
            {
                // Saltamos las partes del cuerpo no asignadas
                if (bodyParts[i] == null) continue;

                // Reordenar los ejes:
                // x del archivo -> x en Unity (izquierda/derecha)
                // y del archivo -> z en Unity (adelante/atrás)
                // z del archivo -> y en Unity (arriba/abajo)
                Vector3 newPosition = new Vector3(
                    positions[i].x * POSITION_SCALE * (invertXAxis ? -1 : 1),
                    positions[i].y * POSITION_SCALE * (invertYAxis ? -1 : 1),  // Invierte Y para corregir cara hacia abajo
                    positions[i].z * POSITION_SCALE * (invertZAxis ? -1 : 1)
                );

                // Aplicar suavizado si está activado y no es el primer frame
                if (enableSmoothing && !isFirstFrame)
                {
                    newPosition = SmoothPosition(newPosition, previousPositions[i], i);
                }

                // Guardar la posición actual como posición anterior para el siguiente frame
                previousPositions[i] = newPosition;

                // Actualizar la posición del GameObject
                bodyParts[i].transform.position = newPosition;

                if (debugMode && i % 3 == 0) // Reducir logs mostrando sólo algunas partes
                {
                    Debug.Log($"Parte {i} - Posición calculada: {newPosition}");
                }
            }

            isFirstFrame = false;

            // Calcular las articulaciones adicionales
            CalculateJoints();

            // Calcular orientaciones para las articulaciones generadas
            //CalculateJointOrientations();
        }

        // Procesar orientaciones recibidas
        while (orientationsQueue.TryDequeue(out KeyValuePair<int, Quaternion> orientationData))
        {
            int partIndex = orientationData.Key;
            Quaternion rotation = orientationData.Value;

            // Verificar que el índice es válido y el objeto existe
            if (partIndex >= 0 && partIndex < bodyParts.Length && bodyParts[partIndex] != null)
            {
                // Aplicar la rotación al objeto
                bodyParts[partIndex].transform.rotation = rotation;

                if (debugMode)
                {
                    Debug.Log($"Aplicada rotación a parte {partIndex}: {rotation.eulerAngles}");
                }
            }
            else if (debugMode)
            {
                Debug.LogWarning($"Índice de parte inválido o objeto nulo: {partIndex}");
            }
        }
    }

    private Vector3 SmoothPosition(Vector3 newPosition, Vector3 previousPosition, int jointIndex)
    {
        // Si es el primer dato de una articulación, no suavizar
        if (previousPosition == Vector3.zero)
        {
            return newPosition;
        }

        // Calculamos la distancia entre la posición anterior y la nueva
        float distance = Vector3.Distance(newPosition, previousPosition);

        // Factor de suavizado adaptativo: más suavizado para cambios pequeños, menos para cambios grandes
        float factor = smoothingFactor;
        if (adaptiveSmoothing)
        {
            // Ajustar el factor según la distancia (movimientos más rápidos tienen menos suavizado)
            factor = smoothingFactor * Mathf.Clamp01(1.0f - distance / 0.1f);
        }

        // Ignorar cambios muy pequeños (probablemente ruido)
        if (distance < jitterThreshold)
        {
            return previousPosition;
        }

        // Interpolar entre la posición anterior y la nueva usando el factor de suavizado
        return Vector3.Lerp(newPosition, previousPosition, factor);
    }

    private void CalculateJoints()
    {
        // Verificar que los índices especiales no excedan los límites del array
        if (SPINE_INDEX >= bodyParts.Length || ROOT_INDEX >= bodyParts.Length ||
           CHEST_INDEX >= bodyParts.Length || SPINE2_INDEX >= bodyParts.Length)
        {
            Debug.LogError("Índices de articulaciones calculadas fuera de rango. Verifica la longitud del array bodyParts.");
            return;
        }

        // Calcular articulaciones basadas en las caderas
        bool canCalculateHipJoints = bodyParts[CADERA_IZQ_INDEX] != null && bodyParts[CADERA_DER_INDEX] != null;
        if (canCalculateHipJoints)
        {
            Vector3 caderaIzqPos = bodyParts[CADERA_IZQ_INDEX].transform.position;
            Vector3 caderaDerPos = bodyParts[CADERA_DER_INDEX].transform.position;

            // Punto medio entre las caderas
            Vector3 midHipPos = (caderaIzqPos + caderaDerPos) / 2.0f;

            // Calcular la posición de spine1_M
            if (calculateSpine && spine1_M != null)
            {
                Vector3 spinePos = midHipPos;
                spinePos.y += spineVerticalOffset;

                // Aplicar suavizado a las articulaciones calculadas también
                if (enableSmoothing && !isFirstFrame)
                {
                    spinePos = SmoothPosition(spinePos, previousPositions[SPINE_INDEX], SPINE_INDEX);
                }
                previousPositions[SPINE_INDEX] = spinePos;

                spine1_M.transform.position = spinePos;

                if (debugMode)
                {
                    Debug.Log($"Spine1_M - Posición calculada: {spinePos}");
                }
            }

            // Calcular la posición de root_M
            if (calculateRoot && root_M != null)
            {
                Vector3 rootPos = midHipPos;
                rootPos.y += rootVerticalOffset;

                // Aplicar suavizado a root_M
                if (enableSmoothing && !isFirstFrame)
                {
                    rootPos = SmoothPosition(rootPos, previousPositions[ROOT_INDEX], ROOT_INDEX);
                }
                previousPositions[ROOT_INDEX] = rootPos;

                root_M.transform.position = rootPos;

                if (debugMode)
                {
                    Debug.Log($"Root_M - Posición calculada: {rootPos}");
                }
            }
        }

        // Calcular articulaciones basadas en los hombros
        bool canCalculateShoulderJoints = bodyParts[HOMBRO_IZQ_INDEX] != null && bodyParts[HOMBRO_DER_INDEX] != null;
        if (canCalculateShoulderJoints)
        {
            Vector3 hombroIzqPos = bodyParts[HOMBRO_IZQ_INDEX].transform.position;
            Vector3 hombroDerPos = bodyParts[HOMBRO_DER_INDEX].transform.position;

            // Punto medio entre los hombros (chest_M)
            Vector3 chestPos = (hombroIzqPos + hombroDerPos) / 2.0f;

            if (calculateChest && chest_M != null)
            {
                // Aplicar suavizado a chest_M
                if (enableSmoothing && !isFirstFrame)
                {
                    chestPos = SmoothPosition(chestPos, previousPositions[CHEST_INDEX], CHEST_INDEX);
                }
                previousPositions[CHEST_INDEX] = chestPos;

                chest_M.transform.position = chestPos;

                if (debugMode)
                {
                    Debug.Log($"Chest_M - Posición calculada: {chestPos}");
                }
            }

            // Calcular spine2_M solo si tenemos chest y spine1 disponibles
            if (calculateSpine2 && spine2_M != null && spine1_M != null && chest_M != null)
            {
                // Punto medio entre spine1_M y chest_M
                Vector3 spine2Pos = (spine1_M.transform.position + chest_M.transform.position) / 2.0f;

                // Aplicar suavizado a spine2_M
                if (enableSmoothing && !isFirstFrame)
                {
                    spine2Pos = SmoothPosition(spine2Pos, previousPositions[SPINE2_INDEX], SPINE2_INDEX);
                }
                previousPositions[SPINE2_INDEX] = spine2Pos;

                spine2_M.transform.position = spine2Pos;

                if (debugMode)
                {
                    Debug.Log($"Spine2_M - Posición calculada: {spine2Pos}");
                }
            }
        }
    }

    private void CalculateJointOrientations()
    {
        // Solo necesitamos los hombros para determinar la orientación frontal
        if (bodyParts[HOMBRO_IZQ_INDEX] == null || bodyParts[HOMBRO_DER_INDEX] == null)
        {
            if (debugMode) Debug.Log("No se puede calcular orientación: hombros no disponibles");
            return;
        }

        // 1. Vector para hombros (de izquierdo a derecho)
        Vector3 shoulderDir = (bodyParts[HOMBRO_DER_INDEX].transform.position -
                               bodyParts[HOMBRO_IZQ_INDEX].transform.position).normalized;

        // 2. Aplanar el vector (eliminar componente Y para rotación horizontal)
        Vector3 flatShoulderDir = new Vector3(shoulderDir.x, 0, shoulderDir.z).normalized;

        // 3. Calcular dirección "adelante" perpendicular a la línea de hombros
        Vector3 shoulderForward = Vector3.Cross(Vector3.up, flatShoulderDir);

        // 4. Crear rotación basada en esta dirección
        Quaternion shoulderRotation = Quaternion.LookRotation(shoulderForward, Vector3.up);

        // 5. Aplicar la misma rotación a todas las articulaciones calculadas
        if (spine1_M != null && calculateSpine)
            spine1_M.transform.rotation = shoulderRotation;

        if (spine2_M != null && calculateSpine2)
            spine2_M.transform.rotation = shoulderRotation;

        if (chest_M != null && calculateChest)
            chest_M.transform.rotation = shoulderRotation;

        if (debugMode)
            Debug.Log($"Orientación basada en hombros aplicada: {shoulderRotation.eulerAngles.y}°");
    }

    // Método auxiliar para aplicar solo la rotación Y preservando X y Z
    private void ApplyYawRotationOnly(GameObject obj, float yawDegrees, bool shouldApply)
    {
        if (obj == null || !shouldApply)
            return;

        // Obtener rotación actual en ángulos de Euler
        Vector3 currentRotation = obj.transform.rotation.eulerAngles;

        // Crear nueva rotación manteniendo X y Z originales
        Quaternion newRotation = Quaternion.Euler(currentRotation.x, yawDegrees, currentRotation.z);

        // Aplicar solo si la diferencia es significativa (opcional, para estabilidad)
        if (Quaternion.Angle(obj.transform.rotation, newRotation) > 0.5f)
            obj.transform.rotation = newRotation;
    }

    // Modificar la función ProcessMessage para distinguir mensajes de orientación
    private void ProcessMessage(string message)
    {
        // Verificar si es un mensaje de orientación
        if (message.StartsWith("ORIENT:"))
        {
            string[] parts = message.Substring(7).Split(',');

            if (parts.Length >= 5)
            {
                try
                {
                    int arduinoNumber = int.Parse(parts[0]);

                    // Crear el cuaternión recibido
                    Quaternion receivedRotation = new Quaternion(
                        float.Parse(parts[2]), // x
                        float.Parse(parts[3]), // y
                        float.Parse(parts[4]), // z
                        float.Parse(parts[1])  // w (primero en el mensaje)
                    );

                    // Verificar si este Arduino está mapeado a una parte del cuerpo
                    if (arduinoToBodyPartMap.TryGetValue(arduinoNumber, out int partId))
                    {
                        // Declarar la variable para la rotación final
                        Quaternion finalRotation;

                        // Reorientar el cuaternión (igual para todos los Arduinos)
                        Quaternion reorientedRotation = new Quaternion(
                            -receivedRotation.y,
                            receivedRotation.z,
                            receivedRotation.x,
                            -receivedRotation.w
                        );

                        // Aplicar la corrección específica para este Arduino
                        if (arduinoAxisCorrections.TryGetValue(arduinoNumber, out Vector3 correction))
                        {
                            Quaternion axisCorrection = Quaternion.Euler(correction);
                            finalRotation = axisCorrection * reorientedRotation;

                            if (debugMode)
                            {
                                Debug.Log($"Arduino {arduinoNumber}: Corrección aplicada con ejes optimizados");
                            }
                        }
                        else
                        {
                            // Fallback en caso de que el Arduino no tenga corrección definida
                            finalRotation = Quaternion.Euler(0, 180, 0) * receivedRotation;
                            if (debugMode) Debug.Log($"Arduino {arduinoNumber}: Sin corrección específica");
                        }

                        // Enviar la rotación a la cola para ser aplicada en Update()
                        orientationsQueue.Enqueue(new KeyValuePair<int, Quaternion>(partId, finalRotation));

                        if (debugMode) Debug.Log($"Arduino {arduinoNumber} → Parte {partId}: rotación procesada");
                    }
                    else if (debugMode)
                    {
                        Debug.LogWarning($"Arduino {arduinoNumber} no está mapeado a ninguna parte del cuerpo");
                    }
                }
                catch (Exception e)
                {
                    Debug.LogError($"Error procesando orientación: {e.Message}");
                }
                return;
            }
        }

        // Si no es un mensaje de orientación, procesarlo como mensaje de posición (código existente)
        try
        {
            string[] parts = message.Split(',');

            // El primer valor es el timestamp, lo ignoramos
            // Después vienen grupos de 3 valores (x,y,z) para cada parte del cuerpo
            int numBodyParts = (parts.Length - 1) / 3;
            Vector3[] positions = new Vector3[numBodyParts];

            for (int i = 0; i < numBodyParts; i++)
            {
                int baseIndex = 1 + (i * 3); // +1 para saltar el timestamp

                // Asegurarnos de que hay suficientes elementos en el array
                if (baseIndex + 2 < parts.Length)
                {
                    try
                    {
                        positions[i] = new Vector3(
                            float.Parse(parts[baseIndex]),
                            float.Parse(parts[baseIndex + 1]),
                            float.Parse(parts[baseIndex + 2])
                        );
                    }
                    catch (FormatException)
                    {
                        // Usar valor por defecto si hay error de formato
                        positions[i] = Vector3.zero;
                        if (debugMode) Debug.LogWarning($"Error de formato en posición {i}");
                    }
                }
                else
                {
                    positions[i] = Vector3.zero;
                }
            }

            positionsQueue.Enqueue(positions);

            if (debugMode)
            {
                Debug.Log($"Recibidas {numBodyParts} posiciones");
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"Error procesando mensaje: {e.Message}\nMensaje: {message}");
        }
    }

    private void ReceiveData()
    {
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, udpPort);

        while (isReceiving)
        {
            try
            {
                byte[] data = udpClient.Receive(ref remoteEndPoint);
                string message = System.Text.Encoding.UTF8.GetString(data);
                ProcessMessage(message);
            }
            catch (SocketException)
            {
                continue;
            }
            catch (Exception e)
            {
                Debug.LogError($"Error recibiendo datos: {e.Message}");
            }
        }
    }

    void OnDisable()
    {
        CleanupNetworking();
    }

    void OnApplicationQuit()
    {
        CleanupNetworking();
    }

    private void CleanupNetworking()
    {
        isReceiving = false;
        if (udpClient != null)
        {
            udpClient.Close();
            udpClient = null;
        }
        if (udpThread != null && udpThread.IsAlive)
        {
            udpThread.Join(1000);
            udpThread = null;
        }
    }
}