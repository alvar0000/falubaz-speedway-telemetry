import cv2
import numpy as np
import json
import os

# --- KONFIGURACJA ---
VIDEO_PATH = 'start_np_05.mp4'
VIDEO_DIR = 'source'
COORDS_PATH = 'roi_coords.json'
OUTPUT_DIR = 'results'
OUTPUT_NAME = 'falubaz_TELEMETRIA8.avi'

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
    ms_per_frame = 1000.0 / fps
    W, H = int(cap.get(3)), int(cap.get(4))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, OUTPUT_NAME)
    out_video = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'XVID'), fps, (W, H))

    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=40, detectShadows=False)

    win_name = 'Telemetria Startu (Stabilizacja Kata)'
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1280, 720)

    last_valid_line = None
    missing_frames = 0
    MAX_MISSING = 9999 

    num_columns = 20 
    col_width = rw // num_columns

    frame_count = 0
    WARMUP_FRAMES = 5

    # --- ZMIENNE TELEMETRII ---
    state = "OCZEKIWANIE" 
    initial_y = None
    prev_y = None
    exact_start_ms = 0.0
    exact_end_ms = 0.0
    min_y_reached = None
    time_at_min_y = 0.0
    frames_without_progress = 0
    
    # --- NOWOŚĆ: Zmienna do stabilizacji kąta taśmy ---
    smoothed_m = None
    
    print("Telemetria i Stabilizacja Żyroskopowa włączona...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame_count += 1
        current_time_ms = frame_count * ms_per_frame
        roi_img = frame[ry:ry+rh, rx:rx+rw].copy()
        
        fgmask = fgbg.apply(roi_img)
        current_line = None

        if frame_count > WARMUP_FRAMES:
            gray_roi = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            _, white_mask = cv2.threshold(gray_roi, 180, 255, cv2.THRESH_BINARY)
            combined = cv2.bitwise_and(fgmask, white_mask)

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            cleaned = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
            cleaned = cv2.dilate(cleaned, kernel, iterations=1)
            
            search_top = int(rh * 0.35) if last_valid_line is None else max(0, int((last_valid_line[0] + last_valid_line[1]) / 2) - 60)
            search_bottom = rh if last_valid_line is None else min(rh, int((last_valid_line[0] + last_valid_line[1]) / 2) + 15)

            top_points = []
            for i in range(num_columns):
                x_start = i * col_width
                x_end = x_start + col_width
                col_mask = cleaned[search_top:search_bottom, x_start:x_end]
                y_indices = np.where(col_mask > 0)[0]
                
                if len(y_indices) > 0:
                    top_y = np.min(y_indices) + search_top 
                    mid_x = x_start + (col_width // 2)
                    top_points.append((mid_x, top_y))

            if len(top_points) > int(num_columns * 0.3):
                y_values = [p[1] for p in top_points]
                median_y = np.median(y_values)
                filtered_points = [p for p in top_points if abs(p[1] - median_y) < 20]
                
                for p in top_points:
                    color_dot = (0, 255, 0) if p in filtered_points else (0, 0, 255)
                    cv2.circle(frame, (rx + p[0], ry + p[1]), 4, color_dot, -1)

                if len(filtered_points) > int(num_columns * 0.25):
                    X = [p[0] for p in filtered_points]
                    Y = [p[1] for p in filtered_points]
                    
                    # --- NOWA MATEMATYKA (STABILIZACJA) ---
                    m, c = np.polyfit(X, Y, 1)
                    
                    if abs(m) < 0.4:
                        # 1. Bezwzględna wysokość środka z kropek (Zero-lag dla stopera)
                        raw_y_center = np.mean(Y)
                        
                        # 2. Filtr EMA dla skosu (85% stary kąt, 15% nowy)
                        if smoothed_m is None:
                            smoothed_m = m
                        else:
                            smoothed_m = 0.85 * smoothed_m + 0.15 * m
                            
                        # 3. Rekonstrukcja idealnej prostej z wygładzonym kątem
                        x_center = rw / 2.0
                        new_c = raw_y_center - (smoothed_m * x_center)
                        
                        y_left = smoothed_m * 0 + new_c
                        y_right = smoothed_m * rw + new_c
                        current_line = (y_left, y_right)

            # Prawa fizyki
            if current_line is not None and last_valid_line is not None:
                prev_line_y = (last_valid_line[0] + last_valid_line[1]) / 2
                curr_line_y = (current_line[0] + current_line[1]) / 2
                if curr_line_y > prev_line_y + 10:
                    current_line = None 

            # =========================================================
            # --- MODUŁ TELEMETRII (BOUNCE DETECTION) ---
            # =========================================================
            curr_y_center = (current_line[0] + current_line[1]) / 2 if current_line else None

            if state == "OCZEKIWANIE":
                if curr_y_center is not None:
                    if initial_y is None:
                        initial_y = curr_y_center
                    
                    # Czekamy na ewidentny ruch (3 px), żeby uniknąć szumu...
                    if curr_y_center <= initial_y - 3.0 and prev_y is not None:
                        
                        # ...ALE matematycznie cofamy stoper do momentu startu (0.5 px od ziemi)!
                        target_y = initial_y - 0.5 
                        
                        ratio = (target_y - prev_y) / (curr_y_center - prev_y) if curr_y_center != prev_y else 0
                        exact_start_ms = (current_time_ms - ms_per_frame) + ratio * ms_per_frame
                        
                        state = "RUCH"
                        min_y_reached = curr_y_center
                        time_at_min_y = current_time_ms
                    
                    prev_y = curr_y_center

            elif state == "RUCH":
                if curr_y_center is not None:
                    if curr_y_center < min_y_reached - 0.5:
                        min_y_reached = curr_y_center
                        time_at_min_y = current_time_ms
                        frames_without_progress = 0
                    else:
                        frames_without_progress += 1

                    if curr_y_center > min_y_reached + 3.0:
                        exact_end_ms = time_at_min_y
                        state = "ZAKONCZONO"
                else:
                    frames_without_progress += 1

                if state == "RUCH" and frames_without_progress >= 10:
                    exact_end_ms = time_at_min_y
                    state = "ZAKONCZONO"

                prev_y = curr_y_center

            # =========================================================
            # --- RYSOWANIE LINII I PAMIĘĆ ---
            if current_line is not None:
                last_valid_line = current_line
                missing_frames = 0
                color = (0, 255, 0)
            else:
                missing_frames += 1
                color = (0, 180, 0)
                if missing_frames >= MAX_MISSING:
                    last_valid_line = None
                    smoothed_m = None # Reset stabilizatora kąta, jeśli całkowicie zgubi taśmę

            if last_valid_line is not None:
                pt1 = (rx, ry + int(last_valid_line[0]))
                pt2 = (rx + rw, ry + int(last_valid_line[1]))
                cv2.line(frame, pt1, pt2, color, 3)

        cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (50, 50, 50), 1)

        # --- OSD HUD ---
        cv2.rectangle(frame, (10, 10), (620, 215), (0, 0, 0), -1) 
        cv2.putText(frame, f"STATUS: {state}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(frame, f"Czas wideo: {current_time_ms:.1f} ms", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
        
        if exact_start_ms > 0:
            cv2.putText(frame, f"Zwolnienie zamka: {exact_start_ms:.1f} ms", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "Zwolnienie zamka: --- ms", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

        if state == "RUCH":
            obecny_czas_unoszenia = current_time_ms - exact_start_ms
            cv2.putText(frame, f"Czas unoszenia: {obecny_czas_unoszenia:.1f} ms", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        elif state == "ZAKONCZONO":
            calkowity_czas_unoszenia = exact_end_ms - exact_start_ms
            cv2.putText(frame, f"Czas unoszenia: {calkowity_czas_unoszenia:.1f} ms", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "Czas unoszenia: --- ms", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

        if W == 0 or H == 0: H, W = frame.shape[:2]
        final_frame = cv2.resize(frame, (W, H))
        out_video.write(final_frame)
        
        cv2.imshow(win_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    out_video.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()