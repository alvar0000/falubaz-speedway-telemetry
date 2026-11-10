import cv2
import os

# --- KONFIGURACJA ---
INPUT_VIDEO = 'source/start_np_05.mp4'  # Podaj ścieżkę do swojego nagrania
OUTPUT_VIDEO = 'zblizenie_kolo.avi'     # Nazwa wygenerowanego pliku

def main():
    if not os.path.exists(INPUT_VIDEO):
        print(f"Błąd: Nie znaleziono pliku {INPUT_VIDEO}")
        return

    cap = cv2.VideoCapture(INPUT_VIDEO)
    ret, frame = cap.read()
    
    if not ret:
        print("Błąd: Nie można odczytać wideo.")
        return

    # --- KROK 1: ZAZNACZANIE OBSZARU ---
    print("Zaznacz obszar, który chcesz wyciąć i wciśnij SPACJĘ.")
    window_name = "Zaznacz obszar do prezentacji"
    
    # Skalowalne okno, żebyś dobrze widział cały stadion
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720) 
    
    bbox = cv2.selectROI(window_name, frame, False)
    cv2.destroyWindow(window_name)

    x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

    # Zabezpieczenie przed pustym zaznaczeniem
    if w == 0 or h == 0:
        print("Anulowano zaznaczanie.")
        cap.release()
        return

    # --- KROK 2: KONFIGURACJA ZAPISU ---
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (w, h))

    print(f"Trwa wycinanie i zapisywanie do {OUTPUT_VIDEO}...")

    # Cofamy wideo do samego początku
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # --- KROK 3: WYCINANIE I ZAPIS ---
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Twarde wycięcie tylko interesującego nas obszaru
        crop_frame = frame[y:y+h, x:x+w]

        # Zapisz do pliku
        out.write(crop_frame)
        
        # Podgląd na żywo (możesz wcisnąć 'q', żeby przerwać wcześniej)
        cv2.imshow("Trwa wycinanie... (wcisnij 'q' aby przerwac)", crop_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("Gotowe! Wycięty fragment został zapisany.")

if __name__ == "__main__":
    main()