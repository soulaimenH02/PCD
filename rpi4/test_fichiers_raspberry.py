import os
import numpy as np
import librosa
import time

# ─────────────────────────────────────────────────────────────
# ⚙️  CONFIGURATION
# ─────────────────────────────────────────────────────────────
MODELE_PATH  = "/home/islem/modeles/ds_cnn_esp32.tflite"
SEUIL_PATH   = "/home/islem/modeles/seuil_optimal.npy"

# ✅ Dossiers de test — fichiers audio du dataset
DOSSIER_TEST = {
    "oiseau": "/home/islem/dataset/oiseau",
    "bruit" : "/home/islem/dataset/bruit"
}
NB_FICHIERS_PAR_CLASSE = 20   # tester 20 fichiers par classe

SAMPLE_RATE     = 16000
DURATION        = 1
N_MFCC          = 13
N_FFT           = 512
HOP_LENGTH      = 256
EXPECTED_FRAMES = 32

# ─────────────────────────────────────────────────────────────
# 🤖 CHARGER MODÈLE
# ─────────────────────────────────────────────────────────────
print("=" * 55)
print("🔬 TEST MODÈLE — Fichiers Audio")
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

print(f"✅ Modèle chargé — seuil={SEUIL}  (auto={SEUIL_AUTO:.3f})\n")

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
# 🔄 TEST PAR CLASSE
# ─────────────────────────────────────────────────────────────
total_correct = 0
total_tests   = 0

for classe, dossier in DOSSIER_TEST.items():
    if not os.path.exists(dossier):
        print(f"⚠️  Dossier non trouvé : {dossier}")
        continue

    label_attendu = 1 if classe == "oiseau" else 0

    # Récupérer fichiers
    fichiers = []
    for f in os.listdir(dossier):
        if f.lower().endswith((".wav", ".mp3", ".m4a")) and "_esp32" not in f and "_converted" not in f:
            fichiers.append(os.path.join(dossier, f))

    # Sélectionner N aléatoirement
    np.random.seed(42)
    if len(fichiers) > NB_FICHIERS_PAR_CLASSE:
        fichiers = list(np.random.choice(fichiers, NB_FICHIERS_PAR_CLASSE, replace=False))

    print(f"{'─'*55}")
    print(f"📂 Classe : {classe.upper()}  ({len(fichiers)} fichiers testés)")
    print(f"{'─'*55}")

    correct = 0
    for fp in fichiers:
        try:
            audio, _ = librosa.load(fp, sr=SAMPLE_RATE, mono=True, duration=DURATION)
            if len(audio) < SAMPLE_RATE:
                audio = np.pad(audio, (0, SAMPLE_RATE - len(audio)), 'constant')

            t0   = time.time()
            prob = predire(audio)
            dt   = (time.time() - t0) * 1000

            pred   = 1 if prob >= SEUIL else 0
            ok     = pred == label_attendu
            correct += int(ok)

            barre_len = 15
            rempli    = int(prob * barre_len)
            barre     = "█" * rempli + "░" * (barre_len - rempli)

            symbole = "✅" if ok else "❌"
            label   = "OISEAU" if pred == 1 else "BRUIT"
            print(f"  {symbole} {os.path.basename(fp)[:25]:25s} "
                  f"prob={prob*100:5.1f}%  [{barre}]  → {label}  {dt:.0f}ms")

        except Exception as e:
            print(f"  ❌ Erreur {os.path.basename(fp)} : {e}")

    acc = correct / len(fichiers) * 100 if fichiers else 0
    print(f"\n  ✅ Accuracy {classe} : {correct}/{len(fichiers)} = {acc:.1f}%\n")
    total_correct += correct
    total_tests   += len(fichiers)

# ─────────────────────────────────────────────────────────────
# 📊 RÉSUMÉ FINAL
# ─────────────────────────────────────────────────────────────
print("=" * 55)
print("📊 RÉSUMÉ FINAL")
print("=" * 55)
print(f"   Total testé  : {total_tests} fichiers")
print(f"   Correct      : {total_correct}")
if total_tests > 0:
    print(f"   Accuracy     : {total_correct/total_tests*100:.1f}%")
print("=" * 55)
