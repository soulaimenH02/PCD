# 🌾 FarmWatch

> **Système intelligent de surveillance et de protection agricole contre les oiseaux nuisibles**

FarmWatch est un système embarqué de bout en bout combinant intelligence artificielle, IoT et interface web. Il détecte automatiquement les oiseaux dans les vergers grâce à une analyse hybride **son + image**, et déclenche un dispositif sonore de dissuasion via un buzzer commandé à distance.

---

## 📋 Table des matières

- [Aperçu de l'architecture](#-aperçu-de-larchitecture)
- [Fonctionnalités](#-fonctionnalités)
- [Stack technique](#-stack-technique)
- [Structure du projet](#-structure-du-projet)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Configuration](#%EF%B8%8F-configuration)
- [Lancement du système](#-lancement-du-système)
- [Utilisation](#-utilisation)
- [Auteurs](#-auteurs)

---

## 🏗️ Aperçu de l'architecture

Le système repose sur une **architecture distribuée à trois niveaux** communiquant sur un réseau Wi-Fi local.

```
┌──────────────────────────────────────────────────────────────────┐
│                    NIVEAU PRÉSENTATION                           │
│   ┌────────────────────────────────────────────────────────┐    │
│   │   Tableau de bord Angular 17  (navigateur)             │    │
│   │   - Authentification JWT                               │    │
│   │   - Flux vidéo en direct                               │    │
│   │   - Statistiques & notifications temps réel (STOMP)    │    │
│   │   - Contrôle manuel de la sirène                       │    │
│   └────────────────────────────────────────────────────────┘    │
└────────────────────────────┬─────────────────────────────────────┘
                  REST  │  WebSocket
┌─────────────────────────┴────────────────────────────────────────┐
│                    NIVEAU APPLICATIF                             │
│   ┌────────────────────────────────────────────────────────┐    │
│   │   Backend Spring Boot 3  (port 8082)                   │    │
│   │   - REST API · WebSocket STOMP · Sécurité JWT          │    │
│   │   - Proxy MJPEG  ·  Persistance PostgreSQL             │    │
│   └────────────────────────────────────────────────────────┘    │
└──────┬──────────────────────────────┬────────────────────────────┘
       │ HTTP                          │ JDBC
┌──────┴──────────────────────────┐  ┌─┴───────────────────────────┐
│      NIVEAU MATÉRIEL (TERRAIN)   │  │  PostgreSQL                │
│  ┌────────────┐   ┌───────────┐  │  └────────────────────────────┘
│  │ ESP32-CAM  │   │ Raspberry │  │
│  │  Caméra +  │◄──┤  Pi 4     │  │
│  │  Buzzer    │   │  Flask AI │  │
│  └────────────┘   │  + Mic    │  │
│                   │  INMP441  │  │
│                   └───────────┘  │
└──────────────────────────────────┘
```

---

## ✨ Fonctionnalités

- 🎤 **Détection sonore** des chants d'oiseaux via un microphone INMP441 et un modèle TFLite optimisé (DS-CNN avec mécanisme d'attention).
- 📷 **Détection visuelle** par l'ESP32-CAM et un classificateur MobileNetV2 par transfert d'apprentissage.
- 🔊 **Sirène de dissuasion** déclenchable automatiquement (mode AUTO) ou manuellement depuis le tableau de bord.
- 📊 **Tableau de bord temps réel** : flux vidéo, cartes statistiques, graphiques horaires, heatmap hebdomadaire, historique paginé.
- 🔐 **Sécurité** par authentification JWT et CORS configuré.
- 🔌 **Notifications instantanées** via WebSocket STOMP, sans rechargement de page.

---

## 🛠️ Stack technique

| Couche       | Technologies                                                        |
|--------------|---------------------------------------------------------------------|
| **Frontend** | Angular 17 · TypeScript · STOMP.js · SockJS                         |
| **Backend**  | Spring Boot 3 · Spring Security · Spring Data JPA · Spring WebSocket |
| **Base**     | PostgreSQL 14+                                                      |
| **IA**       | TensorFlow Lite · Keras · MobileNetV2 · DS-CNN · librosa            |
| **Embarqué** | Raspberry Pi 4 · Python 3.10 · Flask · OpenCV · sounddevice         |
| **IoT**      | ESP32-CAM (Arduino) · OV2640 · INMP441 (I²S) · Buzzer 5 V           |

---

## 📁 Structure du projet

```
PCD/
├── farmwatch/
│   ├── backend/                    # Spring Boot 3 (REST + WebSocket)
│   │   ├── src/main/java/com/farmwatch/
│   │   │   ├── controller/         # AuthController, DetectionController, ...
│   │   │   ├── service/            # DetectionService, SirenService, JwtService
│   │   │   ├── entity/             # Sector, Camera, Detection, SirenEvent
│   │   │   ├── repository/         # Spring Data JPA repositories
│   │   │   ├── dto/                # Data Transfer Objects
│   │   │   ├── config/             # SecurityConfig, WebSocketConfig
│   │   │   └── websocket/          # DetectionEventPublisher (STOMP)
│   │   ├── src/main/resources/
│   │   │   └── application.yml     # Configuration (DB, JWT, IPs)
│   │   └── pom.xml
│   │
│   ├── frontend/                   # Angular 17 SPA
│   │   ├── src/app/
│   │   │   ├── components/         # dashboard, login, camera, siren, ...
│   │   │   ├── services/           # auth, websocket, api
│   │   │   └── models/             # detection, siren, sector
│   │   ├── angular.json
│   │   └── package.json
│   │
│   ├── database/
│   │   └── schema.sql              # Schéma PostgreSQL
│   │
│   └── farmwatch_esp32cam.ino      # Firmware ESP32-CAM
│
└── rpi4/                           # Scripts Raspberry Pi
    ├── bridge.py                   # Orchestrateur principal
    ├── serveur_complet.py          # Serveur Flask AI (audio + image)
    ├── serveur.py                  # Variantes pour tests
    ├── opencv_oiseau_bruit.py
    └── test_*.py                   # Scripts de test (mic, fichiers)
```

---

## 📦 Prérequis

### Côté PC

- **Java 17+** (pour Spring Boot 3)
- **Maven 3.8+**
- **Node.js 18+** & npm 9+
- **PostgreSQL 14+** (peut tourner sur le PC ou sur le Pi)

### Côté Raspberry Pi 4

- **Raspberry Pi OS 64-bit** (Bookworm recommandé)
- **Python 3.10+**
- **I²S activé** (overlay `googlevoicehat-soundcard`)

### Côté ESP32-CAM

- **Arduino IDE** avec le board manager ESP32 installé
- Modules requis : `WiFi`, `esp_camera`, `esp_http_server`

### Matériel

| Composant                 | Rôle                                               |
|---------------------------|----------------------------------------------------|
| ESP32-CAM (avec OV2640)   | Capture d'images et streaming vidéo                |
| Raspberry Pi 4 (4 Go)     | Inférence IA et orchestration                      |
| Microphone INMP441 (I²S)  | Acquisition audio pour la détection sonore         |
| Buzzer actif 5 V          | Dispositif sonore de dissuasion                    |
| Transistor NPN (BC547 / 2N2222) + résistances 1 kΩ et 10 kΩ | Pilotage du buzzer       |

---

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone <url-du-depot>
cd PCD
```

### 2. Base de données PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE farmwatch;
CREATE USER farmwatch WITH PASSWORD 'farmwatch1978';
GRANT ALL PRIVILEGES ON DATABASE farmwatch TO farmwatch;
\q
```

Puis charger le schéma :

```bash
psql -U farmwatch -d farmwatch -f farmwatch/database/schema.sql
```

### 3. Backend Spring Boot

```bash
cd farmwatch/backend
mvn clean install
mvn spring-boot:run
```

Le backend démarre sur `http://localhost:8082`.

### 4. Frontend Angular

```bash
cd farmwatch/frontend
npm install
npm start
```

L'interface est accessible sur `http://localhost:4200`.

### 5. Raspberry Pi — Flask AI + Bridge

```bash
# Activer I²S pour l'INMP441
sudo nano /boot/firmware/config.txt
# Commenter: dtparam=audio=on
# Ajouter:   dtoverlay=googlevoicehat-soundcard
sudo reboot

# Vérifier le micro
arecord -l

# Installer les dépendances Python
pip3 install flask numpy librosa pillow tensorflow tflite-runtime \
             sounddevice opencv-python requests RPi.GPIO

cd rpi4/
python3 serveur_complet.py     # Terminal 1 — serveur IA
python3 bridge.py              # Terminal 2 — orchestrateur
```

### 6. ESP32-CAM

1. Ouvrir `farmwatch/farmwatch_esp32cam.ino` dans l'Arduino IDE.
2. Modifier les credentials WiFi en haut du fichier :

   ```cpp
   const char* WIFI_SSID     = "VotreSSID";
   const char* WIFI_PASSWORD = "VotreMotDePasse";
   ```

3. Sélectionner la carte **AI Thinker ESP32-CAM** et le bon port COM.
4. Maintenir IO0 sur GND, presser RESET, puis téléverser.
5. Ouvrir le moniteur série (115200 bauds) pour récupérer l'IP.

---

## ⚙️ Configuration

### Backend — `application.yml`

Mettre à jour les IPs de votre réseau local :

```yaml
farmwatch:
  camera:
    espcam-url:       "http://192.168.X.X:81/stream"   # IP de l'ESP32-CAM
    pi-stream-url:    "http://localhost:4000/stream"
    mjpeg-proxy-url:  "http://192.168.X.X:81/stream"
  auth:
    jwt-secret:       "VotreCleSecreteAuMoins32Caracteres"
    admin-password:   "votre_mot_de_passe"             # ⚠️ à changer
```

### Bridge.py — IPs réseau

Modifier les variables au début de `rpi4/bridge.py` :

```python
FLASK_URL      = "http://localhost:4000"
SPRINGBOOT_URL = "http://192.168.X.X:8082"     # IP du PC
ESPCAM_IP      = "192.168.X.X"                  # IP de l'ESP32-CAM
```

> 💡 **Astuce :** réservez les IPs dans votre routeur (DHCP reservation) pour éviter qu'elles ne changent.

---

## ▶️ Lancement du système

Démarrer **dans cet ordre** :

| Étape | Composant         | Commande / action                              |
|-------|-------------------|------------------------------------------------|
| 1     | PostgreSQL        | (lancé en service)                             |
| 2     | ESP32-CAM         | Mise sous tension                              |
| 3     | Backend           | `mvn spring-boot:run` (ou bouton IntelliJ)     |
| 4     | Flask IA (Pi)     | `python3 serveur_complet.py`                   |
| 5     | Bridge (Pi)       | `python3 bridge.py`                            |
| 6     | Frontend          | `npm start`                                    |
| 7     | Navigateur        | `http://localhost:4200`                        |

---

## 🎮 Utilisation

1. **Connexion** : utiliser le compte administrateur configuré dans `application.yml` (par défaut `admin` / `admin123`).
2. **Tableau de bord** : visualiser le flux vidéo, les statistiques de détection et l'état de la sirène.
3. **Mode automatique** : la sirène se déclenche dès qu'une détection dépasse le seuil de confiance (80 % par défaut).
4. **Mode manuel** : activer ou désactiver la sirène depuis l'interface.
5. **Historique** : consulter le journal détaillé des détections, filtré par date, secteur ou méthode.

---

## 🐛 Dépannage

| Problème                                    | Cause probable                                  | Solution                                                   |
|---------------------------------------------|-------------------------------------------------|------------------------------------------------------------|
| `❌ /predict error: HTTP -1` sur l'ESP32     | Pi injoignable                                  | Vérifier l'IP du Pi et `ping 192.168.X.X`                  |
| Caméra noire dans le dashboard              | `bridge.py` monopolise le flux MJPEG            | Désactiver `camera_loop` dans `bridge.py`                  |
| Sirène inactive depuis l'interface          | Endpoint `/api/siren/*` non whitelisté          | Vérifier `SecurityConfig` et le filtre JWT                 |
| Mic non détecté (`arecord -l` vide)         | Overlay I²S non chargé                          | Vérifier `/boot/firmware/config.txt` et redémarrer         |
| Erreur `httpd_server_init ... socket (112)` | Conflit de port de contrôle interne             | Définir des `ctrl_port` distincts pour les serveurs HTTP   |

---

## 👥 Auteurs

Projet réalisé dans le cadre du **Projet de Conception et Développement (PCD)**, année universitaire 2025–2026.

---

## 📜 Licence

Projet académique — tous droits réservés aux auteurs.
