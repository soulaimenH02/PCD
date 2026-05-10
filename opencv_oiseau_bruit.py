

import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras import backend as K
import os
import time

# ─────────────────────────────────────────────────────────────
# ⚙️  CONFIGURATION
# ─────────────────────────────────────────────────────────────
MODELE_PATH  = r"C:\Users\MSI\Desktop\PCD\modeles\model_oiseau_bruit.h5"
IMG_SIZE     = (224, 224)
CLASSES      = ["✅ OISEAU", "❌ BRUIT"]
COULEURS     = [(0, 255, 0), (0, 0, 255)]  # Vert=Oiseau, Rouge=Bruit
SEUIL        = 0.70   # Confiance minimum 70%



def get_recall(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    return true_positives / (possible_positives + K.epsilon())

def get_precision(y_true, y_pred):
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    return true_positives / (predicted_positives + K.epsilon())

def get_f1(y_true, y_pred):
    precision = get_precision(y_true, y_pred)
    recall    = get_recall(y_true, y_pred)
    return 2 * ((precision * recall) / (precision + recall + K.epsilon()))


def charger_modele():
    print("⏳ Chargement du modèle...")
    model = tf.keras.models.load_model(
        MODELE_PATH,
        custom_objects={
            'get_f1': get_f1,
            'get_precision': get_precision,
            'get_recall': get_recall
        }
    )
    print("✅ Modèle chargé !\n")
    return model



def pretraiter_image_cv(image_bgr):
    """
    Prétraitement d'une image OpenCV (BGR) pour le modèle
    OpenCV lit en BGR → on convertit en RGB pour TensorFlow
    """
    # BGR → RGB
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    # Redimensionner
    image_resized = cv2.resize(image_rgb, IMG_SIZE)

    # Normaliser [0, 255] → [0, 1]
    image_norm = image_resized / 255.0

    # Ajouter dimension batch
    image_batch = np.expand_dims(image_norm, axis=0)

    return image_batch



def predire(model, image_bgr):
    """Prédit si l'image contient un oiseau ou du bruit"""
    img = pretraiter_image_cv(image_bgr)
    predictions = model.predict(img, verbose=0)
    idx         = np.argmax(predictions[0])
    confiance   = predictions[0][idx]
    return idx, confiance, predictions[0]



def afficher_resultat(frame, idx, confiance, predictions):
    """Dessine les résultats sur le frame OpenCV"""
    h, w = frame.shape[:2]
    couleur = COULEURS[idx]
    label   = CLASSES[idx]

    # Rectangle en haut
    cv2.rectangle(frame, (0, 0), (w, 80), (0, 0, 0), -1)

    # Texte principal
    cv2.putText(frame, label,
                (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2, couleur, 3)

    # Confiance
    cv2.putText(frame, f"Confiance: {confiance*100:.1f}%",
                (20, 75),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (255, 255, 255), 2)

    # Barre de progression oiseau
    barre_w = int((w - 40) * predictions[0])
    cv2.rectangle(frame, (20, h-60), (w-20, h-40), (50, 50, 50), -1)
    cv2.rectangle(frame, (20, h-60), (20 + barre_w, h-40), (0, 255, 0), -1)
    cv2.putText(frame, f"Oiseau: {predictions[0]*100:.1f}%",
                (20, h-65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (0, 255, 0), 2)

    # Barre de progression bruit
    barre_w2 = int((w - 40) * predictions[1])
    cv2.rectangle(frame, (20, h-30), (w-20, h-10), (50, 50, 50), -1)
    cv2.rectangle(frame, (20, h-30), (20 + barre_w2, h-10), (0, 0, 255), -1)
    cv2.putText(frame, f"Bruit: {predictions[1]*100:.1f}%",
                (20, h-35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (0, 0, 255), 2)

    # Bordure colorée
    cv2.rectangle(frame, (0, 0), (w-1, h-1), couleur, 4)

    return frame



def tester_image(chemin_image, model):
    print(f"\n📷 Test image : {chemin_image}")

    # Lire avec OpenCV
    frame = cv2.imread(chemin_image)
    if frame is None:
        print("❌ Image introuvable !")
        return

    # Prédiction
    idx, confiance, predictions = predire(model, frame)

    # Affichage console
    print(f"   Résultat  : {CLASSES[idx]}")
    print(f"   Confiance : {confiance*100:.1f}%")
    print(f"   ✅ Oiseau : {predictions[0]*100:.1f}%")
    print(f"   ❌ Bruit  : {predictions[1]*100:.1f}%")

    # Afficher le résultat sur l'image
    frame_resultat = afficher_resultat(frame.copy(), idx, confiance, predictions)

    # Sauvegarder
    chemin_sortie = chemin_image.replace(".", "_resultat.")
    cv2.imwrite(chemin_sortie, frame_resultat)
    print(f"   💾 Sauvegardé : {chemin_sortie}")

    # Afficher la fenêtre
    cv2.imshow("Résultat - Oiseau ou Bruit", frame_resultat)
    print("\n   Appuyez sur une touche pour fermer...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()



def tester_dossier(dossier, model):
    print(f"\n📁 Test dossier : {dossier}")
    EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

    fichiers = [f for f in os.listdir(dossier) if f.lower().endswith(EXTENSIONS)]
    print(f"   {len(fichiers)} images trouvées\n")

    oiseaux = 0
    bruits   = 0

    for fichier in fichiers:
        chemin = os.path.join(dossier, fichier)
        frame  = cv2.imread(chemin)
        if frame is None:
            continue

        idx, confiance, predictions = predire(model, frame)
        label = "OISEAU" if idx == 0 else "BRUIT"

        if idx == 0:
            oiseaux += 1
        else:
            bruits += 1

        print(f"   {fichier:<30} → {label} ({confiance*100:.1f}%)")

    print(f"\n{'='*50}")
    print(f"📊 RÉSULTATS DOSSIER :")
    print(f"   🐦 Oiseaux détectés : {oiseaux}")
    print(f"   ❌ Bruit détecté    : {bruits}")
    print(f"   Total              : {len(fichiers)}")
    print(f"{'='*50}")



def detection_temps_reel(model):
    print("\n🎥 Démarrage webcam...")
    print("   Appuyez sur 'q' pour quitter")
    print("   Appuyez sur 's' pour sauvegarder une capture\n")

    cap = cv2.VideoCapture(0)  # 0 = webcam principale

    if not cap.isOpened():
        print("❌ Webcam introuvable !")
        return

    fps_time = time.time()
    nb_capture = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Prédiction toutes les 10 frames (optimisation CPU)
        idx, confiance, predictions = predire(model, frame)

        # Afficher résultat
        frame = afficher_resultat(frame, idx, confiance, predictions)

        # FPS
        fps = 1.0 / (time.time() - fps_time)
        fps_time = time.time()
        cv2.putText(frame, f"FPS: {fps:.1f}",
                    (frame.shape[1]-120, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 0), 2)

        cv2.imshow("🐦 Détection Oiseau - Appuyez Q pour quitter", frame)

        touche = cv2.waitKey(1) & 0xFF
        if touche == ord('q'):
            break
        elif touche == ord('s'):
            nb_capture += 1
            nom = f"capture_{nb_capture:03d}.jpg"
            cv2.imwrite(nom, frame)
            print(f"📸 Capture sauvegardée : {nom}")

    cap.release()
    cv2.destroyAllWindows()
    print("✅ Webcam fermée")



if __name__ == "__main__":

    print("=" * 55)
    print("🐦 OPENCV — DÉTECTION OISEAU OU BRUIT")
    print("=" * 55)
    print("\nChoisissez un mode :")
    print("  1 → Tester une image")
    print("  2 → Tester un dossier")
    print("  3 → Webcam temps réel")

    choix = input("\nVotre choix (1/2/3) : ").strip()

    # Charger le modèle
    model = charger_modele()

    if choix == "1":
        chemin = input("Chemin de l'image : ").strip()
        tester_image(chemin, model)

    elif choix == "2":
        dossier = input("Chemin du dossier : ").strip()
        tester_dossier(dossier, model)

    elif choix == "3":
        detection_temps_reel(model)

    else:
        print("❌ Choix invalide")
