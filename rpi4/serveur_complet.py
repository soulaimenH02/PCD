import numpy as np
from flask import Flask, request, jsonify
import librosa
import time
from PIL import Image
from io import BytesIO

# ─────────────────────────────────────────────────────────────
# ⚙️  CONFIGURATION
# ─────────────────────────────────────────────────────────────
MODELE_SON_PATH   = "/home/islem/modeles/ds_cnn_esp32.tflite"
MODELE_IMAGE_PATH = "/home/islem/modeles/model_oiseau_bruit.h5"
SEUIL_PATH        = "/home/islem/modeles/seuil_optimal.npy"
PORT              = 4000

SAMPLE_RATE     = 16000
N_MFCC          = 13
N_FFT           = 512
HOP_LENGTH      = 256
EXPECTED_FRAMES = 32
IMG_SIZE        = (224, 224)

# ─────────────────────────────────────────────────────────────
# 🤖 CHARGER MODÈLE SON (TFLite)
# ─────────────────────────────────────────────────────────────
print("=" * 55)
print("🍓 SERVEUR RASPBERRY PI — Son + Image")
print("=" * 55)

try:
    import tflite_runtime.interpreter as tflite
    interpreter_son = tflite.Interpreter(model_path=MODELE_SON_PATH)
    print("   Modèle son  : tflite_runtime")
except ImportError:
    import tensorflow as tf
    interpreter_son = tf.lite.Interpreter(model_path=MODELE_SON_PATH)
    print("   Modèle son  : tensorflow")

interpreter_son.allocate_tensors()
inp_son  = interpreter_son.get_input_details()[0]
outp_son = interpreter_son.get_output_details()[0]

SEUIL_SON  = 0.70
SEUIL_AUTO = float(np.load(SEUIL_PATH)[0])
in_scale,  in_zero  = inp_son['quantization']
out_scale, out_zero = outp_son['quantization']
print(f"✅ Modèle son chargé  — seuil={SEUIL_SON}  (auto={SEUIL_AUTO:.3f})")

# ─────────────────────────────────────────────────────────────
# 🖼️  CHARGER MODÈLE IMAGE (MobileNetV2 .h5)
# ─────────────────────────────────────────────────────────────
import tensorflow as tf

def get_f1(y_true, y_pred):
    from tensorflow.keras import backend as K
    true_pos = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible = K.sum(K.round(K.clip(y_true, 0, 1)))
    predicted = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_pos / (predicted + K.epsilon())
    recall    = true_pos / (possible  + K.epsilon())
    return 2 * (precision * recall) / (precision + recall + K.epsilon())

def get_precision(y_true, y_pred):
    from tensorflow.keras import backend as K
    true_pos  = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted = K.sum(K.round(K.clip(y_pred, 0, 1)))
    return true_pos / (predicted + K.epsilon())

def get_recall(y_true, y_pred):
    from tensorflow.keras import backend as K
    true_pos = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible = K.sum(K.round(K.clip(y_true, 0, 1)))
    return true_pos / (possible + K.epsilon())

try:
    model_image = tf.keras.models.load_model(
        MODELE_IMAGE_PATH,
        custom_objects={"get_f1": get_f1, "get_precision": get_precision, "get_recall": get_recall}
    )
    print("✅ Modèle image chargé")
    IMAGE_OK = True
except Exception as e:
    print(f"⚠️  Modèle image non chargé : {e}")
    IMAGE_OK = False

# ─────────────────────────────────────────────────────────────
# 🔧 FONCTIONS SON
# ─────────────────────────────────────────────────────────────
def extract_features(audio):
    mfcc = librosa.feature.mfcc(
        y=audio.astype(np.float32), sr=SAMPLE_RATE,
        n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LENGTH
    )
    mfcc = (mfcc - np.mean(mfcc)) / (np.std(mfcc) + 1e-9)
    if mfcc.shape[1] < EXPECTED_FRAMES:
        mfcc = np.pad(mfcc, ((0,0),(0, EXPECTED_FRAMES - mfcc.shape[1])), 'constant')
    else:
        mfcc = mfcc[:, :EXPECTED_FRAMES]
    return mfcc[..., np.newaxis]

def predire_son(audio):
    features = extract_features(audio)
    sample   = features[np.newaxis, ...].astype(np.float32)
    q_input  = np.round(sample / in_scale + in_zero).clip(-128, 127).astype(np.int8)
    interpreter_son.set_tensor(inp_son['index'], q_input)
    interpreter_son.invoke()
    raw_out = interpreter_son.get_tensor(outp_son['index'])[0][0]
    prob    = (float(raw_out) - out_zero) * out_scale
    return max(0.0, min(1.0, prob))

# ─────────────────────────────────────────────────────────────
# 🔧 FONCTIONS IMAGE
# ─────────────────────────────────────────────────────────────
def predire_image(image_bytes):
    img       = Image.open(BytesIO(image_bytes)).convert("RGB")
    img       = img.resize(IMG_SIZE)
    img_array = np.array(img, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    predictions = model_image.predict(img_array, verbose=0)[0]
    idx         = int(np.argmax(predictions))
    confiance   = float(predictions[idx]) * 100
    label       = "OISEAU" if idx == 0 else "BRUIT"

    return {
        "label"     : label,
        "confiance" : round(confiance, 1),
        "oiseau_pct": round(float(predictions[0]) * 100, 1),
        "bruit_pct" : round(float(predictions[1]) * 100, 1),
    }

# ─────────────────────────────────────────────────────────────
# 🌐 ROUTES FLASK
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status"    : "actif",
        "seuil_son" : SEUIL_SON,
        "image_ok"  : IMAGE_OK
    })

# ── Route SON ──────────────────────────────────────────────
@app.route('/analyser', methods=['POST'])
def analyser():
    try:
        data  = request.get_json()
        audio = np.array(data["audio"], dtype=np.float32)

        t0   = time.time()
        prob = predire_son(audio)
        dt   = (time.time() - t0) * 1000

        oiseau = prob >= SEUIL_SON
        label  = "OISEAU" if oiseau else "BRUIT"

        symbole = "🐦" if oiseau else "🔇"
        print(f"  {symbole} SON   {label:6s}  prob={prob*100:.1f}%  {dt:.0f}ms")

        return jsonify({
            "label"      : label,
            "probabilite": round(prob, 4),
            "oiseau"     : bool(oiseau),
            "temps_ms"   : round(dt, 1)
        })
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ── Route IMAGE ────────────────────────────────────────────
@app.route('/predict', methods=['POST'])
def predict():
    if not IMAGE_OK:
        return jsonify({"erreur": "Modèle image non disponible"}), 503
    try:
        if 'image' in request.files:
            image_bytes = request.files['image'].read()
        else:
            image_bytes = request.data

        t0      = time.time()
        resultat = predire_image(image_bytes)
        dt      = (time.time() - t0) * 1000

        resultat['temps_ms'] = round(dt, 1)

        symbole = "🐦" if resultat['label'] == "OISEAU" else "🖼️"
        print(f"  {symbole} IMG   {resultat['label']:6s}  "
              f"conf={resultat['confiance']}%  {dt:.0f}ms")

        return jsonify(resultat)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# 🚀 DÉMARRAGE
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n🚀 Serveur démarré sur port {PORT}")
    print(f"   /analyser  → modèle son")
    print(f"   /predict   → modèle image")
    print(f"   /status    → état")
    print(f"\nCtrl+C pour arrêter\n")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
