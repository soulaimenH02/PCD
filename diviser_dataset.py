

import os
import shutil
import random


DOSSIER_OISEAU = r"C:\Users\MSI\Desktop\PCD\dataset__img\oiseau"
DOSSIER_BRUIT  = r"C:\Users\MSI\Desktop\PCD\dataset__img\bruit"
DOSSIER_SORTIE = r"C:\Users\MSI\Desktop\PCD\dataset__img\oiseau_ou_bruit"

TRAIN = 0.70
VALID = 0.15
TEST  = 0.15

MAX_PAR_CLASSE = 4000   # ✅ MAX 4000 PAR CLASSE

EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


def diviser_classe(dossier_source, nom_classe):
    print(f"\n📂 Traitement : {nom_classe}")

    # Collecter toutes les images
    images = []
    for root, dirs, files in os.walk(dossier_source):
        for f in files:
            if f.lower().endswith(EXTENSIONS):
                images.append(os.path.join(root, f))

    if not images:
        print(f"   ⚠️  Aucune image trouvée !")
        return


    random.shuffle(images)

   
    if len(images) > MAX_PAR_CLASSE:
        print(f"    Sélection aléatoire : {len(images)} → {MAX_PAR_CLASSE}")
        images = images[:MAX_PAR_CLASSE]

    total   = len(images)
    n_train = int(total * TRAIN)
    n_valid = int(total * VALID)

    train_imgs = images[:n_train]
    valid_imgs = images[n_train:n_train + n_valid]
    test_imgs  = images[n_train + n_valid:]

    print(f"   Total   : {total} images")
    print(f"   Train   : {len(train_imgs)} ({TRAIN*100:.0f}%)")
    print(f"   Valid   : {len(valid_imgs)} ({VALID*100:.0f}%)")
    print(f"   Test    : {len(test_imgs)}  ({TEST*100:.0f}%)")

    # Supprimer ancien et recréer
    for split in ["train", "valid", "test"]:
        d = os.path.join(DOSSIER_SORTIE, split, nom_classe)
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    # Copier
    for split, imgs in [("train", train_imgs),
                         ("valid", valid_imgs),
                         ("test",  test_imgs)]:
        dossier_dest = os.path.join(DOSSIER_SORTIE, split, nom_classe)
        for i, src in enumerate(imgs):
            ext = os.path.splitext(src)[1].lower()
            dst = os.path.join(dossier_dest,
                               f"{nom_classe}_{split}_{i:05d}{ext}")
            try:
                shutil.copy2(src, dst)
            except:
                pass

    print(f"   ✅ Copie terminée !")



if __name__ == "__main__":

    print("=" * 55)
    print("  DIVISION — MAX 4000 IMAGES PAR CLASSE")
    print("=" * 55)

    random.seed(42)

    diviser_classe(DOSSIER_OISEAU, "oiseau")
    diviser_classe(DOSSIER_BRUIT,  "bruit")

    print("\n" + "=" * 55)
    print(" DATASET ÉQUILIBRÉ !")
    print("=" * 55)
    for split in ["train", "valid", "test"]:
        print(f"\n  📂 {split}/")
        for cls in ["oiseau", "bruit"]:
            d = os.path.join(DOSSIER_SORTIE, split, cls)
            if os.path.exists(d):
                n = len(os.listdir(d))
                e = "🐦" if cls == "oiseau" else "🌿"
                print(f"      {e} {cls:<10} → {n} images")

    print("\n Lancer : python entrainement_local.py")