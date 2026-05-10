import numpy as np
import tensorflow as tf
import librosa
import sounddevice as sd
import time

# ─────────────────────────────────────────────────────────────
# ⚙️  CONFIGURATION — même que prepare_dataset_esp32.py
# ─────────────────────────────────────────────────────────────
MODELE_PATH     = "/home/islem/modeles/ds_cnn_esp32.tflite"
SEUIL_PATH      = "/home/islem/modeles/seuil_optimal.npy"

SAMPLE_RATE     = 16000
DURATION        = 1
N_MFCC          = 13
N_FFT           = 512
HOP_LENGTH      = 256
EXPECTED_FRAMES = 32

SEUIL_ENERGIE   = 0.001    # ignorer silence

# ─────────────────────────────────────────────────────────────
# 🤖 CHARGER MODÈLE TFLITE
# ─────────────────────────────────────────────────────────────
print("=" * 55)
print("🎙️  TEST MICROPHONE — Détection Oiseau Raspberry Pi")
print("=" * 55)

print("\n⏳ Chargement du modèle...")

try:
    import tflite_runtime.interpreter as tflite
    interpreter = tflite.Interpreter(model_path=MODELE_PATH)
    print("   Backend : tflite_runtime")
except ImportError:
    interpreter = tf.lite.Interpreter(model_path=MODELE_PATH)
    print("   Backend : tensorflow")

interpreter.allocate_tensors()
inp  = interpreter.get_input_details()[0]
outp = interpreter.get_output_details()[0]

# Seuil
SEUIL_AUTO = float(np.load(SEUIL_PATH)[0])
SEUIL      = 0.70
in_scale,  in_zero  = inp['quantization']
out_scale, out_zero = outp['quantization']

print(f"✅ Modèle chargé")
print(f"   Seuil auto     : {SEUIL_AUTO:.3f}")
print(f"   Seuil utilisé  : {SEUIL}")
print(f"   INT8 input     : scale={in_scale:.6f}  zero={in_zero}")
print(f"   INT8 output    : scale={out_scale:.6f}  zero={out_zero}")

# ─────────────────────────────────────────────────────────────
# 🔧 EXTRACTION MFCC
# ─────────────────────────────────────────────────────────────
def extract_features(audio):
    mfcc = librosa.feature.mfcc(
        y=audio.astype(np.float32),
        sr=SAMPLE_RATE,
        n_mfcc=N_MFCC,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH
    )
    mfcc = (mfcc - np.mean(mfcc)) / (np.std(mfcc) + 1e-9)
    if mfcc.shape[1] < EXPECTED_FRAMES:
        mfcc = np.pad(mfcc, ((0,0),(0, EXPECTED_FRAMES - mfcc.shape[1])), 'constant')
    else:
        mfcc = mfcc[:, :EXPECTED_FRAMES]
    return mfcc[..., np.newaxis]

# ─────────────────────────────────────────────────────────────
# 🔮 INFÉRENCE
# ─────────────────────────────────────────────────────────────
def predire(audio):
    features = extract_features(audio)
    sample   = features[np.newaxis, ...].astype(np.float32)

    # Quantisation INT8
    q_input = np.round(sample / in_scale + in_zero).clip(-128, 127).astype(np.int8)
    interpreter.set_tensor(inp['index'], q_input)
    interpreter.invoke()

    raw_out = interpreter.get_tensor(outp['index'])[0][0]
    prob    = (float(raw_out) - out_zero) * out_scale
    return max(0.0, min(1.0, prob))

# ─────────────────────────────────────────────────────────────
# 🎙️  AFFICHER MICROS DISPONIBLES
# ─────────────────────────────────────────────────────────────
print("\n📋 Microphones disponibles :")
devices = sd.query_devices()
for i, d in enumerate(devices):
    if d['max_input_channels'] > 0:
        marker = " ← défaut" if i == sd.default.device[0] else ""
        print(f"   [{i}] {d['name']}{marker}")

# ─────────────────────────────────────────────────────────────
# 🔄 BOUCLE TEMPS RÉEL
# ─────────────────────────────────────────────────────────────
print(f"\n{'─'*55}")
print("🔴 ÉCOUTE EN COURS — Ctrl+C pour arrêter")
print(f"{'─'*55}")
print(f"{'Heure':^10} {'Résultat':^12} {'Probabilité':^14} {'Barre':^20}")
print(f"{'─'*55}")

nb_oiseau  = 0
nb_analyse = 0

try:
    while True:
        # Enregistrer 1 seconde
        audio = sd.rec(
            int(SAMPLE_RATE * DURATION),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32'
        )
        sd.wait()
        audio = audio.flatten()

        heure = time.strftime("%H:%M:%S")

        # ── Vérifier énergie — ignorer silence ──
        energie = float(np.sqrt(np.mean(audio**2)))
        if energie < SEUIL_ENERGIE:
            print(f"{heure:^10} \033[90m{'🔇 silence':^12}\033[0m "
                  f"{'---':>6}         [{'░'*20}]  RMS={energie:.4f}")
            continue

        # ── Inférence ──
        t0   = time.time()
        prob = predire(audio)
        dt   = (time.time() - t0) * 1000
        nb_analyse += 1

        oiseau    = prob >= SEUIL
        barre_len = 20
        rempli    = int(prob * barre_len)

        if oiseau:
            barre   = "█" * rempli + "░" * (barre_len - rempli)
            label   = "🐦 OISEAU"
            couleur = "\033[92m"
            nb_oiseau += 1
        else:
            barre   = "▒" * rempli + "░" * (barre_len - rempli)
            label   = "🔇 bruit "
            couleur = "\033[90m"

        reset = "\033[0m"
        print(f"{heure:^10} {couleur}{label:^12}{reset} "
              f"{prob*100:>6.1f}%        [{barre}]  {dt:.0f}ms")

        if oiseau:
            print(f"\033[93m           *** ALERTE OISEAU ! ({nb_oiseau} détections) ***\033[0m")

except KeyboardInterrupt:
    print(f"\n{'─'*55}")
    print("⏹️  Arrêt")
    print(f"   Analyses      : {nb_analyse}")
    print(f"   Oiseaux       : {nb_oiseau}")
    if nb_analyse > 0:
        print(f"   Taux détection: {nb_oiseau/nb_analyse*100:.1f}%")
    print(f"{'─'*55}")
