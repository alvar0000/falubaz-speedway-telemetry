import cv2
import numpy as np
import json
import os

# --- KONFIGURACJA ---
VIDEO_PATH = 'start_np_10.mp4'
VIDEO_DIR = 'source'
COORDS_PATH = 'roi_coords.json'

def main():
    if not os.path.exists(COORDS_PATH):
        print("BŁĄD: Brak ROI! Uruchom skrypt 01.")
        return

    with open(COORDS_PATH, 'r') as f:
        roi = json.load(f)
        rx, ry, rw, rh = roi['x'], roi['y'], roi['w'], roi['h']

    # --- WYSZUKIWANIE PLIKU WIDEO ---
    if os.path.exists(VIDEO_PATH):
        video_file = VIDEO_PATH
    else:
        candidate = os.path.join(VIDEO_DIR, VIDEO_PATH)
        if os.path.exists(candidate):
            video_file = candidate
        else:
            video_file = None
            if os.path.isdir(VIDEO_DIR):
                for f in os.listdir(VIDEO_DIR):
                    if os.path.isfile(os.path.join(VIDEO_DIR, f)) and f.lower().startswith('start'):
                        video_file = os.path.join(VIDEO_DIR, f)
                        break
    if video_file is None:
        print(f"BŁĄD: Nie znaleziono pliku wideo '{VIDEO_PATH}'.")
        return

    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened(): return

    # Pobieramy klatkaż, żeby odtworzyć film w naturalnym tempie
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    delay = int(1000 / fps) # Opóźnienie w milisekundach

    # Inicjalizacja "oczu" algorytmu
    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=40, detectShadows=False)

    win_name = 'Podglad Algorytmu (Oryginal vs Czysta Maska)'
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1280, 400) # Szerokie okno na dwa obrazy

    print("Odtwarzam podgląd maski... Wyjdź klawiszem 'q'.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # Wycinamy tylko ROI
        roi_img = frame[ry:ry+rh, rx:rx+rw].copy()
        
        # --- TAK KOMPUTER PRZETWARZA OBRAZ ---
        # Krok 1: Co się rusza?
        fgmask = fgbg.apply(roi_img)
        
        # Krok 2: Co jest jasne/białe?
        gray_roi = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        _, white_mask = cv2.threshold(gray_roi, 180, 255, cv2.THRESH_BINARY)
        
        # Krok 3: Połączenie (Rusza się I jest białe)
        combined = cv2.bitwise_and(fgmask, white_mask)

        # Krok 4: Filtracja pozioma (Niszczenie dymu i kasków, wzmacnianie taśmy)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        cleaned = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.dilate(cleaned, kernel, iterations=1)

        # --- PRZYGOTOWANIE DO WYŚWIETLANIA ---
        # Maska jest 1-kanałowa (czarno-biała). Aby skleić ją z oryginalnym obrazem (3-kanałowym),
        # musimy "udawać", że maska ma kolory.
        mask_bgr = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)

        # Dodajemy podpisy
        cv2.putText(roi_img, "WIDOK Z KAMERY", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(mask_bgr, "WIDOK ALGORYTMU", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Rysowanie żółtego korytarza z naszej najnowszej wersji (żebyś widział, w jakiej strefie algorytm pracuje na początku)
        #cv2.rectangle(mask_bgr, (0, int(rh*0.35)), (rw, rh), (0, 150, 150), 1)
        #cv2.putText(mask_bgr, "STREFA POSZUKIWAN", (10, int(rh*0.35) + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 150), 1)

        # Sklejamy oba obrazy poziomo (H-Stack)
        comparison = np.hstack((roi_img, mask_bgr))

        cv2.imshow(win_name, comparison)

        # Zamiast czekać 1 ms (co przyspieszy wideo x10), czekamy naturalny 'delay'
        if cv2.waitKey(delay) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()
    print("Zakończono podgląd.")

if __name__ == "__main__":
    main()