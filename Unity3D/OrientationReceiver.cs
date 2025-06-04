// SECOND VERSION - SEMI-ABSOLUTE POSITION AND ABSOLUTE ORIENTATION

using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Collections.Concurrent;
using System.Collections.Generic;

public class OrientationReceiver : MonoBehaviour
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
    [SerializeField] private GameObject spine1_M;
    [SerializeField] private GameObject root_M;
    [SerializeField] private GameObject chest_M;
    [SerializeField] private GameObject spine2_M;
    [SerializeField] private GameObject scapulaLeft;  // Escápula izquierda (nueva)
    [SerializeField] private GameObject scapulaRight; // Escápula derecha (nueva)

    [Header("Position Settings")]
    // Valores estáticos definidos como constantes
    private const float positionScale = 0.00014f;
    [SerializeField] private Vector3 positionOffset = Vector3.zero;
    [SerializeField] private bool invertX = false;
    private const bool invertY = true;
    private const bool invertZ = true;

    [Header("Skeleton Structure Settings")]
    [SerializeField] private bool captureInitialPose = true;

    [Header("Smoothing Settings")]
    [SerializeField] private bool enableSmoothing = true;
    [SerializeField][Range(0f, 0.95f)] private float smoothingFactor = 0.5f;
    [SerializeField][Range(0f, 0.1f)] private float jitterThreshold = 0.005f;
    [SerializeField] private float movementSpeed = 10f;

    [Header("Debug")]
    [SerializeField] private bool debugMode = false;

    [Header("Rotation Settings")]
    [SerializeField] private bool enableOrientationControl = true;

    [Header("Orientation Correction")]
    [SerializeField] private bool lockRootRotation = true; // Evita el efecto peonza
    [SerializeField] private bool useFixedUpDirection = true; // Mantener dirección vertical fija
    [SerializeField] private float rootRotationSmoothing = 0.8f; // Suavizado para rotación del root

    [Header("Spine Orientation Settings")]
    [SerializeField] private Vector3 spineOrientationOffset = new Vector3(0, -150, -90); // Offset en grados Euler para ajustar la orientación de la columna
    [SerializeField] private bool enableSpineOrientationCorrection = true; // Para activar/desactivar la corrección

    private UdpClient udpClient;
    private Thread udpThread;
    private bool isReceiving = true;
    private ConcurrentQueue<Vector3[]> hipsPositionsQueue = new ConcurrentQueue<Vector3[]>();
    private ConcurrentQueue<KeyValuePair<int, Quaternion>> orientationsQueue = new ConcurrentQueue<KeyValuePair<int, Quaternion>>();
    private GameObject[] bodyParts;
    private Vector3[] previousPositions;
    private Vector3[] targetPositions;
    private bool isFirstFrame = true;
    private Dictionary<int, JointRelationship> jointRelationships = new Dictionary<int, JointRelationship>();

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

    // Constantes para acceder a las posiciones
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
    private const int SPINE_INDEX = 12;
    private const int ROOT_INDEX = 13;
    private const int CHEST_INDEX = 14;
    private const int SPINE2_INDEX = 15;
    private const int SCAPULA_LEFT_INDEX = 16;
    private const int SCAPULA_RIGHT_INDEX = 17;

    // Clase para almacenar relaciones entre articulaciones
    private class JointRelationship
    {
        public int parentIndex = -1;
        public Vector3 initialPosition;
        public Vector3 relativePosition; // Posición relativa al padre
        public float distance; // Distancia al padre
    }

    void Start()
    {
        // Forzar valores por defecto si están en cero
        if (spineOrientationOffset == Vector3.zero)
        {
            spineOrientationOffset = new Vector3(0, -150, -90);
        }

        // Inicializar arrays
        bodyParts = new GameObject[18];
        previousPositions = new Vector3[18];
        targetPositions = new Vector3[18];

        // Asignar las partes del cuerpo
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
        bodyParts[SPINE_INDEX] = spine1_M;
        bodyParts[ROOT_INDEX] = root_M;
        bodyParts[CHEST_INDEX] = chest_M;
        bodyParts[SPINE2_INDEX] = spine2_M;
        bodyParts[SCAPULA_LEFT_INDEX] = scapulaLeft;  // Nueva escápula izquierda
        bodyParts[SCAPULA_RIGHT_INDEX] = scapulaRight; // Nueva escápula derecha

        // Inicializar posiciones previas
        for (int i = 0; i < previousPositions.Length; i++)
        {
            previousPositions[i] = Vector3.zero;
            targetPositions[i] = Vector3.zero;
        }

        // Crear articulaciones calculadas si no existen
        CreateCalculatedJointsIfNeeded();

        // Definir relaciones entre articulaciones
        DefineJointRelationships();

        // Si está habilitado, capturar la pose inicial
        if (captureInitialPose)
        {
            CaptureInitialPose();
        }

        // Iniciar recepción UDP
        StartUDPReceiver();

        // Establecer orientación inicial
        SetInitialModelOrientation();
    }

    private void DefineJointRelationships()
    {
        // Definir relaciones entre articulaciones para la reconstrucción del esqueleto
        jointRelationships.Clear();

        // Caderas son independientes (no tienen padre)
        jointRelationships[CADERA_IZQ_INDEX] = new JointRelationship { parentIndex = -1 };
        jointRelationships[CADERA_DER_INDEX] = new JointRelationship { parentIndex = -1 };

        // Root deriva de las caderas
        jointRelationships[ROOT_INDEX] = new JointRelationship { parentIndex = -1 }; // Especial: se calcula del promedio

        // Columna vertebral
        jointRelationships[SPINE_INDEX] = new JointRelationship { parentIndex = ROOT_INDEX };
        jointRelationships[SPINE2_INDEX] = new JointRelationship { parentIndex = SPINE_INDEX };
        jointRelationships[CHEST_INDEX] = new JointRelationship { parentIndex = SPINE2_INDEX };

        // Hombros
        jointRelationships[HOMBRO_IZQ_INDEX] = new JointRelationship { parentIndex = CHEST_INDEX };
        jointRelationships[HOMBRO_DER_INDEX] = new JointRelationship { parentIndex = CHEST_INDEX };

        // Brazos
        jointRelationships[CODO_IZQ_INDEX] = new JointRelationship { parentIndex = HOMBRO_IZQ_INDEX };
        jointRelationships[CODO_DER_INDEX] = new JointRelationship { parentIndex = HOMBRO_DER_INDEX };
        jointRelationships[MUNECA_IZQ_INDEX] = new JointRelationship { parentIndex = CODO_IZQ_INDEX };
        jointRelationships[MUNECA_DER_INDEX] = new JointRelationship { parentIndex = CODO_DER_INDEX };

        // Piernas
        jointRelationships[RODILLA_IZQ_INDEX] = new JointRelationship { parentIndex = CADERA_IZQ_INDEX };
        jointRelationships[RODILLA_DER_INDEX] = new JointRelationship { parentIndex = CADERA_DER_INDEX };

        // Cabeza
        jointRelationships[NARIZ_INDEX] = new JointRelationship { parentIndex = CHEST_INDEX };
    }

    private void CaptureInitialPose()
    {
        // Capturar posiciones iniciales y calcular relaciones
        for (int i = 0; i < bodyParts.Length; i++)
        {
            if (bodyParts[i] != null && jointRelationships.ContainsKey(i))
            {
                JointRelationship relationship = jointRelationships[i];
                relationship.initialPosition = bodyParts[i].transform.position;

                // Si tiene padre, calcular posición relativa y distancia
                if (relationship.parentIndex >= 0 && relationship.parentIndex < bodyParts.Length &&
                    bodyParts[relationship.parentIndex] != null)
                {
                    Vector3 parentPos = bodyParts[relationship.parentIndex].transform.position;
                    relationship.relativePosition = bodyParts[i].transform.position - parentPos;
                    relationship.distance = relationship.relativePosition.magnitude;
                }
            }
        }

        if (debugMode)
        {
            Debug.Log("Pose inicial capturada para reconstrucción del esqueleto");
        }
    }

    private void CreateCalculatedJointsIfNeeded()
    {
        if (spine1_M == null)
        {
            spine1_M = new GameObject("spine1_M");
            bodyParts[SPINE_INDEX] = spine1_M;
        }

        if (root_M == null)
        {
            root_M = new GameObject("root_M");
            bodyParts[ROOT_INDEX] = root_M;
        }

        if (chest_M == null)
        {
            chest_M = new GameObject("chest_M");
            bodyParts[CHEST_INDEX] = chest_M;
        }

        if (spine2_M == null)
        {
            spine2_M = new GameObject("spine2_M");
            bodyParts[SPINE2_INDEX] = spine2_M;
        }
    }

    private void StartUDPReceiver()
    {
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
        // Verificar que el root mantiene su orientación vertical
        if (lockRootRotation && root_M != null)
        {
            // Usar la rotación guardada, no la variable que podría cambiar
            root_M.transform.rotation = rootLastRotation;
        }

        // Procesar posiciones de caderas recibidas
        ProcessHipPositions();

        // Procesar orientaciones recibidas
        if (enableOrientationControl)
        {
            ProcessOrientations();
        }

        // Mover articulaciones hacia sus posiciones objetivo
        MoveJointsToTargets();
    }

    private void ProcessHipPositions()
    {
        if (hipsPositionsQueue.TryDequeue(out Vector3[] hipPositions))
        {
            if (hipPositions.Length >= 2)
            {
                // Aplicar transformaciones a las posiciones de caderas
                Vector3 leftHipPos = ProcessPosition(hipPositions[0]);
                Vector3 rightHipPos = ProcessPosition(hipPositions[1]);

                // Actualizar posiciones objetivo de las caderas
                targetPositions[CADERA_IZQ_INDEX] = leftHipPos;
                targetPositions[CADERA_DER_INDEX] = rightHipPos;

                // Reconstruir el resto del esqueleto basado en las posiciones de caderas
                ReconstructSkeletonFromHips(leftHipPos, rightHipPos);
            }
        }
    }

    private Vector3 ProcessPosition(Vector3 position)
    {
        // Aplicar inversiones de ejes
        Vector3 processedPos = new Vector3(
            position.x * (invertX ? -1 : 1),
            position.y * (invertY ? -1 : 1),
            position.z * (invertZ ? -1 : 1)
        );

        // Aplicar escala y offset
        return processedPos * positionScale + positionOffset;
    }

    private Quaternion rootLastRotation = Quaternion.identity;

    private void ReconstructSkeletonFromHips(Vector3 leftHipPos, Vector3 rightHipPos)
    {
        // Calcular posición del root (centro de las caderas)
        Vector3 rootPos = (leftHipPos + rightHipPos) / 2.0f;

        // Posicionar el root
        bodyParts[ROOT_INDEX].transform.position = rootPos;

        // CALCULAR ORIENTACIÓN BASADA EN LA LÍNEA DE CADERAS
        Vector3 hipDirection = (rightHipPos - leftHipPos).normalized;
        Vector3 forward = Vector3.Cross(hipDirection, Vector3.up).normalized;
        Quaternion spineOrientation = Quaternion.LookRotation(forward, Vector3.up);

        // ESTABILIZAR LA ROTACIÓN DEL ROOT PARA EVITAR EFECTO PEONZA
        if (isFirstFrame)
        {
            // En el primer frame, aplicar la rotación inicial 
            Quaternion initialRotation = Quaternion.Euler(new Vector3(-180, -180, 90));
            bodyParts[ROOT_INDEX].transform.rotation = initialRotation;
            rootLastRotation = initialRotation;
        }
        else if (!lockRootRotation)
        {
            // Solo calculamos la rotación basada en caderas si no está bloqueada
            Vector3 forward_root = Vector3.forward;

            if (!useFixedUpDirection)
            {
                forward_root = Vector3.Cross(hipDirection, Vector3.up);
            }

            Quaternion targetRotation = Quaternion.LookRotation(forward_root, Vector3.up);
            Quaternion smoothedRotation = Quaternion.Slerp(
                rootLastRotation,
                targetRotation,
                1.0f - rootRotationSmoothing
            );

            bodyParts[ROOT_INDEX].transform.rotation = smoothedRotation;
            rootLastRotation = smoothedRotation;
        }

        // APLICAR LA ORIENTACIÓN DE CADERAS A LAS ARTICULACIONES DE LA COLUMNA
        ApplySpineOrientation(spineOrientation);

        // Las posiciones de caderas se mantienen para alinear correctamente con los sensores
        bodyParts[CADERA_IZQ_INDEX].transform.position = leftHipPos;
        bodyParts[CADERA_DER_INDEX].transform.position = rightHipPos;
    }

    private void ApplySpineOrientation(Quaternion spineOrientation)
    {
        // Calcular orientación base desde las caderas
        Vector3 hipDirection = (bodyParts[CADERA_DER_INDEX].transform.position - bodyParts[CADERA_IZQ_INDEX].transform.position).normalized;
        Vector3 forward = Vector3.Cross(hipDirection, Vector3.up).normalized;
        Quaternion baseSpineOrientation = Quaternion.LookRotation(forward, Vector3.up);

        // Aplicar offset personalizable
        Quaternion offsetRotation = Quaternion.Euler(spineOrientationOffset);
        Quaternion finalSpineOrientation = baseSpineOrientation * offsetRotation;

        // Solo aplicar si la corrección está habilitada
        if (enableSpineOrientationCorrection)
        {
            if (bodyParts[SPINE_INDEX] != null)
            {
                bodyParts[SPINE_INDEX].transform.rotation = finalSpineOrientation;
            }

            if (bodyParts[SPINE2_INDEX] != null)
            {
                bodyParts[SPINE2_INDEX].transform.rotation = finalSpineOrientation;
            }

            if (bodyParts[CHEST_INDEX] != null)
            {
                bodyParts[CHEST_INDEX].transform.rotation = finalSpineOrientation;
            }
        }

        if (debugMode)
        {
            Debug.Log($"Orientación de columna - Base: {baseSpineOrientation.eulerAngles}, Offset: {spineOrientationOffset}, Final: {finalSpineOrientation.eulerAngles}");
        }
    }

    private void ReconstructFromCapturedPose(Vector3 rootPos)
    {
        // Reconstruir jerárquicamente desde el root, manteniendo las relaciones capturadas

        // Primero reconstruir la columna vertebral desde el root
        if (jointRelationships.TryGetValue(SPINE_INDEX, out JointRelationship spineRel))
        {
            Vector3 spinePos = rootPos + spineRel.relativePosition.normalized * spineRel.distance;
            targetPositions[SPINE_INDEX] = spinePos;

            // Spine2 (a partir de spine)
            if (jointRelationships.TryGetValue(SPINE2_INDEX, out JointRelationship spine2Rel))
            {
                Vector3 spine2Pos = spinePos + spine2Rel.relativePosition.normalized * spine2Rel.distance;
                targetPositions[SPINE2_INDEX] = spine2Pos;

                // Chest (a partir de spine2)
                if (jointRelationships.TryGetValue(CHEST_INDEX, out JointRelationship chestRel))
                {
                    Vector3 chestPos = spine2Pos + chestRel.relativePosition.normalized * chestRel.distance;
                    targetPositions[CHEST_INDEX] = chestPos;

                    // Reconstruir hombros, brazos y cabeza a partir del chest
                    ReconstructUpperBody(chestPos);
                }
            }
        }

        // Reconstruir piernas a partir de las caderas
        ReconstructLegsFromHips();
    }

    private void ReconstructUpperBody(Vector3 chestPos)
    {
        // Reconstruir hombros a partir del chest
        if (jointRelationships.TryGetValue(HOMBRO_IZQ_INDEX, out JointRelationship hombroIzqRel))
        {
            Vector3 hombroIzqPos = chestPos + hombroIzqRel.relativePosition.normalized * hombroIzqRel.distance;
            targetPositions[HOMBRO_IZQ_INDEX] = hombroIzqPos;

            // Codo izquierdo
            if (jointRelationships.TryGetValue(CODO_IZQ_INDEX, out JointRelationship codoIzqRel))
            {
                Vector3 codoIzqPos = hombroIzqPos + codoIzqRel.relativePosition.normalized * codoIzqRel.distance;
                targetPositions[CODO_IZQ_INDEX] = codoIzqPos;

                // Muñeca izquierda
                if (jointRelationships.TryGetValue(MUNECA_IZQ_INDEX, out JointRelationship munecaIzqRel))
                {
                    Vector3 munecaIzqPos = codoIzqPos + munecaIzqRel.relativePosition.normalized * munecaIzqRel.distance;
                    targetPositions[MUNECA_IZQ_INDEX] = munecaIzqPos;
                }
            }
        }

        // Lado derecho
        if (jointRelationships.TryGetValue(HOMBRO_DER_INDEX, out JointRelationship hombroDerRel))
        {
            Vector3 hombroDerPos = chestPos + hombroDerRel.relativePosition.normalized * hombroDerRel.distance;
            targetPositions[HOMBRO_DER_INDEX] = hombroDerPos;

            // Codo derecho
            if (jointRelationships.TryGetValue(CODO_DER_INDEX, out JointRelationship codoDerRel))
            {
                Vector3 codoDerPos = hombroDerPos + codoDerRel.relativePosition.normalized * codoDerRel.distance;
                targetPositions[CODO_DER_INDEX] = codoDerPos;

                // Muñeca derecha
                if (jointRelationships.TryGetValue(MUNECA_DER_INDEX, out JointRelationship munecaDerRel))
                {
                    Vector3 munecaDerPos = codoDerPos + munecaDerRel.relativePosition.normalized * munecaDerRel.distance;
                    targetPositions[MUNECA_DER_INDEX] = munecaDerPos;
                }
            }
        }

        // Nariz/cabeza
        if (jointRelationships.TryGetValue(NARIZ_INDEX, out JointRelationship narizRel))
        {
            Vector3 narizPos = chestPos + narizRel.relativePosition.normalized * narizRel.distance;
            targetPositions[NARIZ_INDEX] = narizPos;
        }
    }

    private void ReconstructLegsFromHips()
    {
        // Reconstruir rodillas a partir de caderas
        if (bodyParts[CADERA_IZQ_INDEX] != null && jointRelationships.TryGetValue(RODILLA_IZQ_INDEX, out JointRelationship rodillaIzqRel))
        {
            Vector3 caderaIzqPos = targetPositions[CADERA_IZQ_INDEX];
            Vector3 rodillaIzqPos = caderaIzqPos + rodillaIzqRel.relativePosition.normalized * rodillaIzqRel.distance;
            targetPositions[RODILLA_IZQ_INDEX] = rodillaIzqPos;
        }

        if (bodyParts[CADERA_DER_INDEX] != null && jointRelationships.TryGetValue(RODILLA_DER_INDEX, out JointRelationship rodillaDerRel))
        {
            Vector3 caderaDerPos = targetPositions[CADERA_DER_INDEX];
            Vector3 rodillaDerPos = caderaDerPos + rodillaDerRel.relativePosition.normalized * rodillaDerRel.distance;
            targetPositions[RODILLA_DER_INDEX] = rodillaDerPos;
        }
    }

    private void MoveJointsToTargets()
    {
        for (int i = 0; i < bodyParts.Length; i++)
        {
            if (bodyParts[i] != null && targetPositions[i] != Vector3.zero)
            {
                Vector3 newPosition = targetPositions[i];

                // Aplicar suavizado si está habilitado
                if (enableSmoothing && !isFirstFrame && previousPositions[i] != Vector3.zero)
                {
                    newPosition = SmoothPosition(newPosition, previousPositions[i]);
                }

                // Mover gradualmente hacia la posición objetivo
                bodyParts[i].transform.position = Vector3.MoveTowards(
                    bodyParts[i].transform.position,
                    newPosition,
                    Time.deltaTime * movementSpeed
                );

                // Guardar posición para el siguiente frame
                previousPositions[i] = bodyParts[i].transform.position;
            }
        }

        isFirstFrame = false;
    }

    private Vector3 SmoothPosition(Vector3 newPosition, Vector3 previousPosition)
    {
        float distance = Vector3.Distance(newPosition, previousPosition);

        // Ignorar cambios pequeños (eliminar jitter)
        if (distance < jitterThreshold)
            return previousPosition;

        // Interpolar entre posición anterior y nueva
        return Vector3.Lerp(newPosition, previousPosition, smoothingFactor);
    }

    private void ProcessMessage(string message)
    {
        try
        {
            // Procesamiento de orientaciones
            if (message.StartsWith("ORIENT:"))
            {
                ProcessOrientationMessage(message.Substring(7));
                return;
            }

            // Procesamiento especial para mensajes de caderas
            if (message.StartsWith("HIPS:"))
            {
                ProcessHipsMessage(message.Substring(5));
                return;
            }

            // Procesamiento estándar (formato antiguo)
            string[] parts = message.Split(',');

            // Solo necesitamos las posiciones de las caderas
            if (parts.Length > 22) // Asegurarnos de que hay suficientes datos
            {
                Vector3[] hipPositions = new Vector3[2];

                // Extraer cadera izquierda (índice 7)
                int leftHipBaseIndex = 1 + (CADERA_IZQ_INDEX * 3);
                if (leftHipBaseIndex + 2 < parts.Length)
                {
                    hipPositions[0] = new Vector3(
                        float.Parse(parts[leftHipBaseIndex]),
                        float.Parse(parts[leftHipBaseIndex + 1]),
                        float.Parse(parts[leftHipBaseIndex + 2])
                    );
                }

                // Extraer cadera derecha (índice 8)
                int rightHipBaseIndex = 1 + (CADERA_DER_INDEX * 3);
                if (rightHipBaseIndex + 2 < parts.Length)
                {
                    hipPositions[1] = new Vector3(
                        float.Parse(parts[rightHipBaseIndex]),
                        float.Parse(parts[rightHipBaseIndex + 1]),
                        float.Parse(parts[rightHipBaseIndex + 2])
                    );
                }

                hipsPositionsQueue.Enqueue(hipPositions);
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"Error procesando mensaje: {e.Message}\nMensaje: {message}");
        }
    }

    private void ProcessOrientationMessage(string message)
    {
        string[] parts = message.Split(',');

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
                if (arduinoToBodyPartMap.TryGetValue(arduinoNumber, out int partId) &&
                    arduinoAxisCorrections.TryGetValue(arduinoNumber, out Vector3 correction))
                {
                    // Reorientar el cuaternión (común para todos los Arduinos)
                    Quaternion reorientedRotation = new Quaternion(
                        -receivedRotation.y,
                        receivedRotation.z,
                        receivedRotation.x,
                        -receivedRotation.w
                    );

                    // Aplicar la corrección específica para este Arduino
                    Quaternion axisCorrection = Quaternion.Euler(correction);
                    Quaternion finalRotation = axisCorrection * reorientedRotation;

                    // Enviar la rotación a la cola para ser aplicada en Update()
                    orientationsQueue.Enqueue(new KeyValuePair<int, Quaternion>(partId, finalRotation));
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Error procesando orientación: {e.Message}");
            }
        }
    }

    private void ProcessHipsMessage(string message)
    {
        try
        {
            string[] parts = message.Split(',');

            if (parts.Length >= 6) // Formato esperado: leftX,leftY,leftZ,rightX,rightY,rightZ
            {
                Vector3[] hipPositions = new Vector3[2];

                // Cadera izquierda
                hipPositions[0] = new Vector3(
                    float.Parse(parts[0]),
                    float.Parse(parts[1]),
                    float.Parse(parts[2])
                );

                // Cadera derecha
                hipPositions[1] = new Vector3(
                    float.Parse(parts[3]),
                    float.Parse(parts[4]),
                    float.Parse(parts[5])
                );

                hipsPositionsQueue.Enqueue(hipPositions);

                if (debugMode)
                {
                    Debug.Log($"Recibidas posiciones de caderas: Left={hipPositions[0]}, Right={hipPositions[1]}");
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"Error procesando mensaje de caderas: {e.Message}");
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

    private void ProcessOrientations()
    {
        while (orientationsQueue.TryDequeue(out KeyValuePair<int, Quaternion> orientationData))
        {
            int partIndex = orientationData.Key;
            Quaternion rotation = orientationData.Value;

            // Verificar que el índice es válido y el objeto existe
            if (partIndex >= 0 && partIndex < bodyParts.Length && bodyParts[partIndex] != null)
            {
                // Evitar cambiar la rotación del root si está bloqueada
                if (lockRootRotation && partIndex == ROOT_INDEX)
                    continue;

                // Aplicar la rotación al objeto
                bodyParts[partIndex].transform.rotation = rotation;
            }
        }
    }

    private void SetInitialModelOrientation()
    {
        if (root_M != null)
        {
            // Versión minimalista con solo lo esencial
            Vector3 correctRotation = new Vector3(-180, -180, 90);
            root_M.transform.rotation = Quaternion.Euler(correctRotation);
            rootLastRotation = root_M.transform.rotation;
        }
    }
}