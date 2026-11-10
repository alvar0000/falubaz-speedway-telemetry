import cv2
import numpy as np
import json
import os

# --- KONFIGURACJA ---
VIDEO_PATH = 'start_np_10.mp4'
VIDEO_DIR = 'source'
COORDS_PATH = 'roi_coords.json'
OUTPUT_DIR = 'results'
OUTPUT_NAME = 'falubaz_V10_KROPKI_LSQ4.avi'

def main():
    if not os.path.exists(COORDS_PATH): return

    with open(COORDS_PATH, 'r') as f:
        roi = json.load(f)
        rx, ry, rw, rh = roi['x'], roi['y'], roi['w'], roi['h']

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
    if video_file is None: return

    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened(): return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    W, H = int(cap.get(3)), int(cap.get(4))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, OUTPUT_NAME)
    out_video = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'XVID'), fps, (W, H))

    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=40, detectShadows=False)

    win_name = 'V10 LSQ - Pancerny Tracker'
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1280, 720)

    last_valid_line = None
    missing_frames = 0
    MAX_MISSING = 9999 # Linia zostaje na zawsze po dojechaniu na górę

    num_columns = 20 
    col_width = rw // num_columns

    frame_count = 0
    WARMUP_FRAMES = 5

    print("Analiza LSQ z korytarzem śledzącym uruchomiona...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame_count += 1
        roi_img = frame[ry:ry+rh, rx:rx+rw].copy()
        
        fgmask = fgbg.apply(roi_img)

        if frame_count > WARMUP_FRAMES:
            gray_roi = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            _, white_mask = cv2.threshold(gray_roi, 180, 255, cv2.THRESH_BINARY)
            combined = cv2.bitwise_and(fgmask, white_mask)

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            cleaned = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
            cleaned = cv2.dilate(cleaned, kernel, iterations=1)
            
            # --- WYZNACZANIE KORYTARZA ŚLEDZENIA (ZABEZPIECZENIE PRZED TŁEM) ---
            search_top = 0
            search_bottom = rh
            
            if last_valid_line is not None:
                # Obliczamy gdzie była taśma w poprzedniej klatce
                prev_y_center = (last_valid_line[0] + last_valid_line[1]) / 2
                # Szukamy tylko do 60px w górę (kierunek ruchu) i max 15px w dół od ostatniej pozycji
                search_top = max(0, int(prev_y_center) - 60)
                search_bottom = min(rh, int(prev_y_center) + 15)

            top_points = []
            
            for i in range(num_columns):
                x_start = i * col_width
                x_end = x_start + col_width
                
                # Zamiast skanować całą kolumnę, skanujemy tylko wyznaczony KORYTARZ
                col_mask = cleaned[search_top:search_bottom, x_start:x_end]
                y_indices = np.where(col_mask > 0)[0]
                
                if len(y_indices) > 0:
                    # Odtwarzamy prawdziwe Y dodając search_top
                    top_y = np.min(y_indices) + search_top 
                    mid_x = x_start + (col_width // 2)
                    top_points.append((mid_x, top_y))

            current_line = None

            if len(top_points) > int(num_columns * 0.3):
                # --- FILTR MEDIANY (USUWANIE ZBŁĄKANYCH KROPEK) ---
                y_values = [p[1] for p in top_points]
                median_y = np.median(y_values)
                
                # Akceptujemy tylko kropki, które są nie dalej niż 20px od większości grupy
                filtered_points = [p for p in top_points if abs(p[1] - median_y) < 20]
                
                # Rysujemy kropki (zielone to zaakceptowane, czerwone to odrzucony szum)
                for p in top_points:
                    color_dot = (0, 255, 0) if p in filtered_points else (0, 0, 255)
                    cv2.circle(frame, (rx + p[0], ry + p[1]), 4, color_dot, -1)

                if len(filtered_points) > int(num_columns * 0.25):
                    X = [p[0] for p in filtered_points]
                    Y = [p[1] for p in filtered_points]
                    
                    m, c = np.polyfit(X, Y, 1)
                    
                    if abs(m) < 0.4:
                        y_left = m * 0 + c
                        y_right = m * rw + c
                        current_line = (y_left, y_right)

            # ZASADA: TAŚMA NIE SPADA W DÓŁ
            if current_line is not None and last_valid_line is not None:
                prev_y_center = (last_valid_line[0] + last_valid_line[1]) / 2
                curr_y_center = (current_line[0] + current_line[1]) / 2
                
                if curr_y_center > prev_y_center + 10:
                    current_line = None 

            if current_line is not None:
                last_valid_line = current_line
                missing_frames = 0
                color = (0, 255, 0)
            else:
                missing_frames += 1
                color = (0, 180, 0)
                if missing_frames >= MAX_MISSING:
                    last_valid_line = None

            if last_valid_line is not None:
                pt1 = (rx, ry + int(last_valid_line[0]))
                pt2 = (rx + rw, ry + int(last_valid_line[1]))
                
                cv2.line(frame, pt1, pt2, color, 3)
                cv2.putText(frame, "TASMA", (pt1[0], pt1[1] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (50, 50, 50), 1)

        if W == 0 or H == 0: H, W = frame.shape[:2]
        final_frame = cv2.resize(frame, (W, H))
        out_video.write(final_frame)
        
        cv2.imshow(win_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    out_video.release()
    cv2.destroyAllWindows()
    print(f"Zapisano w: {out_path}")

if __name__ == "__main__":
    main()