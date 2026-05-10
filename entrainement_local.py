

import os
import time
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import backend as K
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ReduceLROnPlateau, ModelCheckpoint, EarlyStopping
from tensorflow.keras import applications as app
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten, Dropout, GlobalAveragePooling2D


BASE_DIR     = r"C:\Users\MSI\Desktop\PCD\dataset__img\oiseau_ou_bruit"
train_folder = os.path.join(BASE_DIR, "train")
val_folder   = os.path.join(BASE_DIR, "valid")
test_folder  = os.path.join(BASE_DIR, "test")

# Dossier pour sauvegarder les résultats
SAVE_DIR = r"C:\Users\MSI\Desktop\PCD\modeles"
os.makedirs(SAVE_DIR, exist_ok=True)


IMG_SIZE  = (224, 224)   # Taille des images
BATCH     = 16           # Réduit pour PC local (évite les erreurs mémoire)
EPOCHS    = 30           # Nombre d'époques
CLASSES   = 2            # oiseau / bruit

print("=" * 60)
print(" ENTRAÎNEMENT LOCAL — OISEAU OU BRUIT")
print("=" * 60)
print(f" Dataset  : {BASE_DIR}")
print(f"Modèles  : {SAVE_DIR}")
print(f"️  Taille   : {IMG_SIZE}")
print(f"Batch    : {BATCH}")
print(f"Epochs   : {EPOCHS}")

# Vérifier GPU disponible
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    print(f" GPU détecté : {gpus[0].name}")
else:
    print("Mode CPU (plus lent mais fonctionne)")
print("=" * 60)



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



def charger_donnees():
    print("\n Chargement des données...")

    train_datagen = ImageDataGenerator(
        rescale=1.0/255,
        horizontal_flip=True,
        shear_range=0.2,
        zoom_range=0.2,
        brightness_range=[0.8, 1.2],
        rotation_range=15,
        fill_mode='nearest'
    )
    test_datagen = ImageDataGenerator(rescale=1.0/255)

    gen_train = train_datagen.flow_from_directory(
        train_folder,
        target_size=IMG_SIZE,
        batch_size=BATCH,
        class_mode='categorical',
        classes=['oiseau', 'bruit'],
        shuffle=True
    )
    gen_valid = test_datagen.flow_from_directory(
        val_folder,
        target_size=IMG_SIZE,
        batch_size=BATCH,
        class_mode='categorical',
        classes=['oiseau', 'bruit']
    )
    gen_test = test_datagen.flow_from_directory(
        test_folder,
        target_size=IMG_SIZE,
        batch_size=BATCH,
        class_mode='categorical',
        classes=['oiseau', 'bruit']
    )

    print(f"\n Classes  : {gen_train.class_indices}")
    print(f"   Train    : {gen_train.samples} images")
    print(f"   Valid    : {gen_valid.samples} images")
    print(f"   Test     : {gen_test.samples} images")

    return gen_train, gen_valid, gen_test



def build_model():
    print("\n🤖 Construction du modèle MobileNetV2...")

    # Base pré-entraînée
    base = app.MobileNetV2(
        input_shape=(IMG_SIZE[0], IMG_SIZE[1], 3),
        include_top=False,
        weights='imagenet'
    )
    base.trainable = False  # Geler la base

    # Modèle complet
    model = Sequential([
        base,
        GlobalAveragePooling2D(),
        Dense(256, activation='relu'),
        Dropout(0.4),
        Dense(64, activation='relu'),
        Dropout(0.2),
        Dense(CLASSES, activation='softmax')  # oiseau / bruit
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy', get_f1, get_precision, get_recall]
    )

    print(f" Modèle construit !")
    print(f"   Paramètres totaux     : {model.count_params():,}")
    print(f"   Paramètres entraînables : {sum([K.count_params(p) for p in model.trainable_weights]):,}")

    return model



def entrainer(model, gen_train, gen_valid):
    print(f"\n  Entraînement en cours ({EPOCHS} époques)...")
    print("   Patience : arrêt automatique si pas d'amélioration\n")

    chemin_modele = os.path.join(SAVE_DIR, "model_oiseau_bruit.h5")

    callbacks = [
        # Arrêt si pas d'amélioration après 7 époques
        EarlyStopping(
            monitor='val_accuracy',
            patience=7,
            verbose=1,
            restore_best_weights=True
        ),
        # Réduire le taux d'apprentissage
        ReduceLROnPlateau(
            monitor='val_accuracy',
            patience=3,
            factor=0.5,
            min_lr=0.00001,
            verbose=1
        ),
        # Sauvegarder le meilleur modèle
        ModelCheckpoint(
            filepath=chemin_modele,
            monitor='val_accuracy',
            mode='max',
            save_best_only=True,
            verbose=1
        )
    ]

    start = time.time()
    history = model.fit(
        gen_train,
        validation_data=gen_valid,
        epochs=EPOCHS,
        callbacks=callbacks,
        verbose=1
    )
    duree = round(time.time() - start, 2)

    print(f"\n  Durée totale : {duree} secondes ({duree/60:.1f} minutes)")
    print(f" Meilleure précision validation : {max(history.history['val_accuracy'])*100:.1f}%")
    print(f" Modèle sauvegardé : {chemin_modele}")

    return history, chemin_modele


# ─────────────────────────────────────────────────────────────
# 📊 ÉVALUATION FINALE
# ─────────────────────────────────────────────────────────────
def evaluer(model, gen_test):
    print("\n Évaluation sur les données de TEST...")
    res = model.evaluate(gen_test, verbose=1)

    print(f"\n{'='*50}")
    print(f" RÉSULTATS FINAUX")
    print(f"{'='*50}")
    print(f"  Loss        : {res[0]:.4f}")
    print(f"  Accuracy    : {res[1]*100:.1f}%")
    print(f"  F1 Score    : {res[2]:.4f}")
    print(f"  Précision   : {res[3]:.4f}")
    print(f"  Rappel      : {res[4]:.4f}")
    print(f"{'='*50}")


# ─────────────────────────────────────────────────────────────
# 📈 GRAPHIQUES DES RÉSULTATS
# ─────────────────────────────────────────────────────────────
def afficher_courbes(history):
    print("\nSauvegarde des courbes d'entraînement...")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Courbe Accuracy
    axes[0].plot(history.history['accuracy'],     label='Train', color='blue')
    axes[0].plot(history.history['val_accuracy'], label='Valid', color='orange')
    axes[0].set_title('🎯 Précision (Accuracy)')
    axes[0].set_xlabel('Époque')
    axes[0].set_ylabel('Accuracy')
    axes[0].legend()
    axes[0].grid(True)

    # Courbe Loss
    axes[1].plot(history.history['loss'],     label='Train', color='blue')
    axes[1].plot(history.history['val_loss'], label='Valid', color='orange')
    axes[1].set_title('📉 Perte (Loss)')
    axes[1].set_xlabel('Époque')
    axes[1].set_ylabel('Loss')
    axes[1].legend()
    axes[1].grid(True)

    plt.tight_layout()
    chemin_graph = os.path.join(SAVE_DIR, "courbes_entrainement.png")
    plt.savefig(chemin_graph)
    plt.show()
    print(f"✅ Graphique sauvegardé : {chemin_graph}")



def convertir_tflite(chemin_modele):
    print("\n🍓 Conversion en TFLite pour Raspberry Pi...")
    try:
        model = tf.keras.models.load_model(
            chemin_modele,
            custom_objects={
                'get_f1': get_f1,
                'get_precision': get_precision,
                'get_recall': get_recall
            }
        )
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()

        chemin_tflite = os.path.join(SAVE_DIR, "model_oiseau_bruit.tflite")
        with open(chemin_tflite, 'wb') as f:
            f.write(tflite_model)

        taille = os.path.getsize(chemin_tflite) / (1024 * 1024)
        print(f"✅ TFLite sauvegardé : {chemin_tflite}")
        print(f"   Taille : {taille:.2f} MB")
    except Exception as e:
        print(f"❌ Erreur TFLite : {e}")


def tester_image(chemin_image, chemin_modele):
    from PIL import Image

    model = tf.keras.models.load_model(
        chemin_modele,
        custom_objects={
            'get_f1': get_f1,
            'get_precision': get_precision,
            'get_recall': get_recall
        }
    )

    img = Image.open(chemin_image).convert("RGB")
    img = img.resize(IMG_SIZE)
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    pred = model.predict(img_array, verbose=0)
    idx  = np.argmax(pred[0])
    conf = pred[0][idx]

    resultat = "✅ OISEAU" if idx == 0 else "❌ BRUIT"
    print(f"\n🔮 {os.path.basename(chemin_image)}")
    print(f"   Résultat  : {resultat}")
    print(f"   Confiance : {conf*100:.1f}%")
    print(f"   ✅ Oiseau : {pred[0][0]*100:.1f}%")
    print(f"   ❌ Bruit  : {pred[0][1]*100:.1f}%")



if __name__ == "__main__":

    # 1. Charger les données
    gen_train, gen_valid, gen_test = charger_donnees()

    # 2. Construire le modèle
    model = build_model()

    # 3. Entraîner
    history, chemin_modele = entrainer(model, gen_train, gen_valid)

    # 4. Évaluer
    evaluer(model, gen_test)

    # 5. Afficher les courbes
    afficher_courbes(history)

    # 6. Convertir pour Raspberry Pi
    convertir_tflite(chemin_modele)

    print("\n" + "=" * 60)
    print(" TOUT EST TERMINÉ !")
    print(f" Résultats dans : {SAVE_DIR}")
    print(f"    model_oiseau_bruit.h5")
    print(f"   model_oiseau_bruit.tflite")
    print(f"   courbes_entrainement.png")
    print("=" * 60)

    # 7. Tester une image (décommentez et mettez votre image)
    # tester_image(r"C:\Users\MSI\Desktop\test_bird.jpg", chemin_modele)
