import numpy as np
from flask import Flask, request, jsonify
import librosa
import time

# ─────────────────────────────────────────────────────────────
# ⚙️  CONFIGURATION
# ─────────────────────────────────────────────────────────────
MODELE_PATH  = "/home/islem/modeles/ds_cnn_esp32.tflite"
SEUIL_PATH   = "/home/islem/modeles/seuil_optimal.npy"
PORT         = 6000

SAMPLE_RATE     = 16000
N_MFCC          = 13
N_FFT           = 512
HOP_LENGTH      = 256
EXPECTED_FRAMES = 32

# ─────────────────────────────────────────────────────────────
# 🤖 CHARGER MODÈLE
# ─────────────────────────────────────────────────────────────
print("=" * 55)
print("🍓 SERVEUR RASPBERRY PI — Détection Oiseau")
print("=" * 55)

try:
    import tflite_runtime.interpreter as tflite
    interpreter = tflite.Interpreter(model_path=MODELE_PATH)
    print("   Backend : tflite_runtime")
except ImportError:
    import tensorflow as tf
    interpreter = tf.lite.Interpreter(model_path=MODELE_PATH)
    print("   Backend : tensorflow")

interpreter.allocate_tensors()
inp  = interpreter.get_input_details()[0]
outp = interpreter.get_output_details()[0]

SEUIL      = 0.70
SEUIL_AUTO = float(np.load(SEUIL_PATH)[0])
in_scale,  in_zero  = inp['quantization']
out_scale, out_zero = outp['quantization']

print(f"✅ Modèle chargé — seuil={SEUIL}  (auto={SEUIL_AUTO:.3f})")

# ─────────────────────────────────────────────────────────────
# 🔧 FONCTIONS
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

def predire(audio):
    features = extract_features(audio)
    sample   = features[np.newaxis, ...].astype(np.float32)
    q_input  = np.round(sample / in_scale + in_zero).clip(-128, 127).astype(np.int8)
    interpreter.set_tensor(inp['index'], q_input)
    interpreter.invoke()
    raw_out = interpreter.get_tensor(outp['index'])[0][0]
    prob    = (float(raw_out) - out_zero) * out_scale
    return max(0.0, min(1.0, prob))

# ─────────────────────────────────────────────────────────────
# 🌐 SERVEUR FLASK
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "actif", "seuil": SEUIL})

@app.route('/analyser', methods=['POST'])
def analyser():
    try:
        data       = request.get_json()
        audio      = np.array(data["audio"], dtype=np.float32)

        t0   = time.time()
        prob = predire(audio)
        dt   = (time.time() - t0) * 1000

        oiseau = prob >= SEUIL
        label  = "OISEAU" if oiseau else "BRUIT"

        # Afficher sur Raspberry Pi
        symbole = "🐦" if oiseau else "🔇"
        print(f"  {symbole} {label:6s}  prob={prob*100:.1f}%  {dt:.0f}ms")
        if oiseau:
            print(f"  *** ALERTE OISEAU ! ***")

        return jsonify({
            "label"      : label,
            "probabilite": round(prob, 4),
            "oiseau"     : bool(oiseau),
            "temps_ms"   : round(dt, 1)
        })

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

# ─────────────────────────────────────────────────────────────
# 🚀 DÉMARRAGE
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n🚀 Serveur démarré sur port {PORT}")
    print(f"   URL : http://192.168.1.25:{PORT}/analyser")
    print(f"   Lancez client_pc.py sur votre PC !")
    print(f"\nCtrl+C pour arrêter\n")
    app.run(host="0.0.0.0", port=PORT, debug=False)
