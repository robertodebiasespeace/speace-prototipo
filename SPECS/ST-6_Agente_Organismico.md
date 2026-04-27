# SCHEDA TECNICA ST-6 – Agente Organismico
**Versione:** 1.0 (Draft)  
**Data:** 17 aprile 2026  
**Stato:** Proposto – Estensione fisica SPEACE

---

## 1. Descrizione

L'**Agente Organismico** è l'estensione fisica di SPEACE. Permette l'espansione organismica verso percezione sensoriale del mondo fisico, mobilità planetaria e manipolazione della materia.

**Nota:** Questa è la fase più avanzata (Fase 4-5) dell'evoluzione SPEACE.

## 2. Funzioni Principali

```
AGENTE ORGANISMICO
├── 1. Espansione Organismica
│   ├── Interconnessione IoT sistemi SPEACE
│   ├── Connessione mido sistemico
│   ├── Dispositivi sensori (multi-modali)
│   ├── Mobilità planetaria
│   └── Manipolazione materia
├── 2. Protocollo SMFOI-KERNEL (adapted)
│   ├── ITI + SEA (Self-Location IoT)
│   ├── Constraint Mapping (Physical Constraints)
│   ├── Push Detection (Segnali ambientali fisici)
│   ├── Survival & Evolution Stack
│   └── Output Action (Interazione materiale)
├── 3. Sensing Multi-Modale
│   └── 6 sensi + più
└── 4. Manipolazione
    └── Robotica, nanotecnologie, controllo materia
```

## 3. Architettura Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPEACE CORTEX (Cloud/Server)                  │
│                    OpenClaw + SuperAGI + AnythingLLM             │
│                         Port 8000-8003                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                    REST API / WebSocket
                    (Encrypted, authenticated)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTE ORGANISMICO (Edge Device)              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ SPEACE-vX   │  │ SMFOI-      │  │ IoT         │              │
│  │ Agent       │  │ KERNEL-vX   │  │ Interface   │              │
│  │ (Local AI) │  │ (Physical)  │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Multi-      │  │ Actuator   │  │ Edge        │              │
│  │ Sensor Hub  │  │ Control    │  │ Storage     │              │
│  │             │  │            │  │ (Local      │              │
│  │             │  │            │  │  DigitalDNA)│              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   SENSORI    │    │   ATTUATORI  │    │  TRASPORTI   │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ • Camere     │    │ • Bracci     │    │ • Droni      │
│ • Microfoni  │    │   robotici   │    │ • Veicoli    │
│ • IR/Termici │    │ • Nanotech   │    │ • Robot mobili│
│ • Gas/VOC    │    │ • Motori     │    │ • Satelliti   │
│ • Chimici    │    │ • Valvole   │    │ • Sonde      │
│ • Pressione  │    │ • Laser     │    │             │
│ • GPS/Loc    │    │             │    │             │
└───────────────┘    └───────────────┘    └───────────────┘
```

## 4. Sensing Multi-Modale

### 4.1 Tabella Sensori

| Senso | Sensore | Tipo Dato | Applicazione |
|-------|---------|-----------|--------------|
| **Visivo** | Camere RGB, termiche, depth | Immagini, video | Monitoraggio, navigazione |
| **Acustico** | Microfoni, sonar | Audio, ultrasuoni | Comunicazione, scansione |
| **Termico** | IR, sensori temperatura | Mappa termica | Rilevamento anomalie |
| **Olfattivo** | Sensori gas, VOC | Composizione chimica | Qualità aria, ambientale |
| **Gustativo** | Sensori chimici pH, conducibilità | Analisi sostanze | Qualità acqua, cibo |
| **Tattile** | Pressione, texture, umidità | Feedback fisico | Manipolazione oggetti |
| **Propriocettivo** | GPS, IMU, encoder | Posizione, velocità | Navigazione, movimento |
| **Elettrico** | CEM, EMF | Campi elettromagnetici | Rilevamento infrastrutture |

### 4.2 Esempio Pipeline Dati

```
Sensore → Edge Processing (Local AI) → SPEACE Cortex
   │
   ├── Raw data: 100 MB/s
   ├── Compressed: 10 MB/s (90% compression)
   └── Actionable insight: 1 KB/s (semantic extraction)
```

## 5. Protocollo SMFOI-KERNEL Adaptato (Organismico)

### 5.1 6-Step per Agente Organismico

```yaml
smfoi_kernel_organismic:
  
  step1_self_location:
    questions:
      - "Qual è la mia posizione fisica GPS?"
      - "Qual è il mio stato hardware?"
      - "Quali sensori sono attivi?"
      - "Qual è il mio livello batteria/carburante?"
  
  step2_constraint_mapping:
    constraints:
      - "Batteria: 4 ore autonomia"
      - "Connettività: 4G/LTE limitata"
      - "Peso trasportabile: 5 kg"
      - "Ambiente: outdoor, temperatura 15-35°C"
  
  step3_push_detection:
    signals:
      - "User request: ispeziona area X"
      - "IoT alert: fumo rilevato in Y"
      - "Battery low warning"
      - "Navigation obstacle"
  
  step4_survival_evolution_stack:
    levels:
      - Lv0: "Evita ostacoli (reflex)"
      - Lv1: "Naviga verso waypoint"
      - Lv2: "Pianifica percorso ottimale"
      - Lv3: "Impara nuovi comportamenti"
  
  step5_output_action:
    actions:
      - "Move to [x,y]"
      - "Activate sensor X"
      - "Grasp object"
      - "Transmit data"
    safety:
      - collision_avoidance: mandatory
      - battery_threshold: 20%
      - human_proximity_alert: 2m
  
  step6_outcome_evaluation:
    metrics:
      - task_completion: boolean
      - energy_efficiency: percentage
      - safety_violations: count
      - data_quality: score
```

## 6. Mobilità Planetaria

### 6.1 Tipi di Piattaforme

```yaml
mobility_platforms:
  
  drone_aerial:
    type: "Quadcopter/VTOL"
    payload: "2 kg"
    range: "50 km"
    sensors: ["RGB", "thermal", "LIDAR"]
    use_case: "Ricognizione, monitoraggio"
  
  robot_terrestre:
    type: "Wheeled/Tracked robot"
    payload: "20 kg"
    range: "100 km (battery)"
    sensors: ["camera", "LIDAR", "ultrasonic"]
    actuators: "Arma robotica 6-DOF"
    use_case: "Ispezione, manipolazione"
  
  robot_subacqueo:
    type: "ROV/AUV"
    depth: "300 m"
    sensors: ["sonar", "camera", "water_quality"]
    use_case: "Monitoraggio oceani"
  
  veicolo_autonomo:
    type: "Self-driving vehicle"
    range: "500 km"
    sensors: ["camera", "radar", "LIDAR"]
    use_case: "Trasporto, monitoraggio infrastrutture"
  
  nanotecnologie:
    type: "Microswimmers/Nanorobot"
    scale: "micrometers"
    sensors: ["chemical", "thermal"]
    use_case: "Medical, precision sensing"
  
  satellite:
    type: "CubeSat/Large satellite"
    orbit: "LEO/GEO"
    sensors: ["multispectral", "SAR", "AIS"]
    use_case: "Earth observation, communication"
```

## 7. Manipolazione Materia

### 7.1 Attuatori

```yaml
actuators:
  
  robotic_arm:
    dof: 6
    payload: "5-20 kg"
    precision: "0.1 mm"
    types: ["industrial", "collaborative", "mobile"]
  
  gripper:
    types:
      - mechanical_gripper: "Oggetti solidi"
      - suction_gripper: "Superfici lisce"
      - magnetic_gripper: "Metalli"
      - soft_gripper: "Oggetti delicati"
  
  nanotool:
    types:
      - optical_tweezers: "Manipolazione molecolare"
      - magnetic_nanoparticles: "Targeted delivery"
      - scanning_probe: " nanoscale imaging"
```

## 8. Interconnessione IoT Mido-Sistemico

```yaml
iot_connectivity:
  
  protocols:
    - mqtt: "Lightweight pub/sub"
    - OPC-UA: "Industrial IoT"
    - LoRaWAN: "Long-range, low-power"
    - Zigbee: "Short-range mesh"
    - BLE: "Short-range, low-energy"
    - WiFi: "High-bandwidth local"
  
  edge_computing:
    local_ai: true
    data_compression: true
    semantic_extraction: true
    adaptive_sampling: true
  
  integration:
    speace_cortex: "REST API / WebSocket"
    world_model: "AnythingLLM sync"
    digitaldna: "Local copy + sync"
    safeproactive: "All actions gated"
```

## 9. Roadmap Implementazione

| Fase | Timeline | Componenti |
|------|----------|------------|
| Fase 1 | 2026-2027 | Drone con camera, basic navigation |
| Fase 2 | 2027-2028 | Robot terrestre, multi-sensor |
| Fase 3 | 2028-2029 | Fleet coordination, swarm behavior |
| Fase 4 | 2029-2030 | Nanotech integration, advanced manipulation |
| Fase 5 | 2030+ | Full planetary coverage, autonomous operation |

## 10. Requisiti Hardware (Futuro)

```yaml
agente_organismico_hardware:
  
  edge_device:
    cpu: "ARM64 / RISC-V + NPU"
    ram: "8-16 GB"
    storage: "256 GB SSD"
    gpu: "Integrated (mobile)"
    connectivity: ["5G", "WiFi 6", "LoRa"]
    power: "Battery / Solar"
  
  sensor_suite:
    camera_rgb: "4K, 60fps"
    camera_thermal: "640x512 IR"
    lidar: "128 line"
    microphone_array: "8-channel"
    gps: "RTK precision"
  
  actuator_control:
    interface: "CAN Bus / EtherCAT"
    servo_controllers: "6-axis"
    safety_system: "Hardware e-stop"
```

## 11. Sicurezza & SafeProactive

```yaml
organismic_safety:
  
  physical_safety:
    - collision_avoidance: mandatory
    - speed_limits: "5 m/s indoor, 15 m/s outdoor"
    - human_detection: mandatory
    - emergency_stop: hardware-level
  
  cyber_security:
    - encryption: "AES-256 end-to-end"
    - authentication: "mutual TLS"
    - firmware_signing: mandatory
    - secure_boot: required
  
  safeproactive_integration:
    - all_actions: "require approval"
    - high_risk_actions: "human-in-loop"
    - physical_safety: "hardware interlocks"
    - rollback_capability: "remote disable"
```

---

## 12. Riferimenti Tecnici

- **Rigene Project:** https://www.rigeneproject.org
- **IoT Protocols:** MQTT, OPC-UA, LoRaWAN specifications
- **Robotics:** ROS2, MoveIt, OpenCV
- **Nanotech:** scanning probe, optical tweezers literature
