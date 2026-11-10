import cv2
import json
import os

# Ścieżka do wideo (jeśli plik nie istnieje w cwd, szukaj w `source/`)
VIDEO_PATH = 'start_np_10.mp4'
VIDEO_DIR = 'source'


video_file = VIDEO_PATH if os.path.exists(VIDEO_PATH) else os.path.join(VIDEO_DIR, VIDEO_PATH)

cap = cv2.VideoCapture(video_file)
ret, frame = cap.read()
cap.release()

if not ret:
    print(f"Błąd: Nie można wczytać filmu ({video_file}). Sprawdź ścieżkę!")
    exit()


window_name = "Zaznacz bramke (LPM) i zatwierdz ENTEREM"

#  okno, które można skalować
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL) 

# rozmiar okna 
cv2.resizeWindow(window_name, 1280, 720) 

print("INSTRUKCJA:")
print("1. Użyj myszki, aby narysować prostokąt wokół taśmy.")
print("2. Jak skończysz rysować, naciśnij klawisz ENTER lub SPACJĘ.")
print("3. Jeśli chcesz zacząć od nowa, naciśnij klawisz 'c'.")

# Wywołujemy wybieranie ROI
roi = cv2.selectROI(window_name, frame, fromCenter=False, showCrosshair=True)

# Po naciśnięciu ENTER, zamykamy okno
cv2.destroyAllWindows()

# roi to (x, y, w, h)
x, y, w, h = roi

if w == 0 or h == 0:
    print("Błąd: Nic nie zaznaczono!")
else:
    print(f"Sukces! Zapisano ROI: X={x}, Y={y}, W={w}, H={h}")
    roi_data = {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
    with open('roi_coords.json', 'w') as f:
        json.dump(roi_data, f)
    print("Współrzędne zapisane do roi_coords.json. Możesz odpalać drugi skrypt.")