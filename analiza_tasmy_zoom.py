import cv2
import numpy as np
import json
import os

# --- KONFIGURACJA ---
VIDEO_PATH = 'start_np_11.mp4'
VIDEO_DIR = 'source'
OUTPUT_DIR = 'results'
OUTPUT_NAME = 'falubaz_TELEMETRIA_ZOOM2.avi'

DISPLAY_PAD = 150   
ZOOM_SCALE  = 2     

CONFIGS = {
    'tasma': 'roi_coords.json',
    'czerwony': 'roi_rider_1.json',
    'niebieski': 'roi_rider_2.json',
    'bialy': 'roi_rider_3.json',
    'zolty': 'roi_rider_4.json'
}

# ==========================================
# FUNKCJE DO KONFIGURACJI ROI
# ==========================================
def get_standard_roi(video_file, json_path, window_title):
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            if data['w'] > 5: return data['x'], data['y'], data['w'], data['h']

    print(f"\n[KONFIGURACJA] Zaznacz: {window_title}")
    cap_temp = cv2.VideoCapture(video_file)
    ret, frame_temp = cap_temp.read()

    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_title, 1280, 720)
    bbox = cv2.selectROI(window_title, frame_temp, False)

    with open(json_path, 'w') as f:
        json.dump({'x': int(bbox[0]), 'y': int(bbox[1]), 'w': int(bbox[2]), 'h': int(bbox[3])}, f)

    cap_temp.release()
    cv2.destroyWindow(window_title)
    return int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

def get_zoomed_roi(video_file, json_path, rider_name):
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            if data['w'] > 5:
                return data['x'], data['y'], data['w'], data['h'], True
            if data['w'] == 0:
                return 0, 0, 0, 0, False

    print(f"\n[LUPA - KROK 1] Zaznacz ZGRUBNIE okolice koła: {rider_name}")
    print("-> Jeśli zawodnika NIE MA: po prostu wciśnij SPACJĘ (bez rysowania kwadratu).")

    cap_temp = cv2.VideoCapture(video_file)
    ret, frame_temp = cap_temp.read()

    win_rough = f"Zaznacz: {rider_name} (SPACJA bez rysowania = WYKLUCZONY)"
    cv2.namedWindow(win_rough, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_rough, 1280, 720)

    rough_bbox = cv2.selectROI(win_rough, frame_temp, False)
    cv2.destroyWindow(win_rough)

    if rough_bbox[2] == 0 or rough_bbox[3] == 0:
        print(f"-> {rider_name} OZNACZONY JAKO WYKLUCZONY.")
        with open(json_path, 'w') as f:
            json.dump({'x': 0, 'y': 0, 'w': 0, 'h': 0}, f)
        cap_temp.release()
        return 0, 0, 0, 0, False

    rx, ry, rw, rh = int(rough_bbox[0]), int(rough_bbox[1]), int(rough_bbox[2]), int(rough_bbox[3])

    ZOOM = 3
    zoomed_img = cv2.resize(frame_temp[ry:ry+rh, rx:rx+rw], (rw * ZOOM, rh * ZOOM), interpolation=cv2.INTER_CUBIC)

    print(f"[LUPA - KROK 2] Zaznacz PRECYZYJNIE styk koła z ziemią!")
    win_precise = f"KROK 2: PRECYZYJNE ZAZNACZANIE (Powiekszenie 300%)"
    cv2.namedWindow(win_precise, cv2.WINDOW_NORMAL)
    precise_bbox = cv2.selectROI(win_precise, zoomed_img, False)
    cv2.destroyWindow(win_precise)

    final_x = rx + int(precise_bbox[0] / ZOOM)
    final_y = ry + int(precise_bbox[1] / ZOOM)
    final_w = int(precise_bbox[2] / ZOOM)
    final_h = int(precise_bbox[3] / ZOOM)

    with open(json_path, 'w') as f:
        json.dump({'x': final_x, 'y': final_y, 'w': final_w, 'h': final_h}, f)

    cap_temp.release()
    return final_x, final_y, final_w, final_h, True

# ==========================================
# GŁÓWNY PROGRAM
# ==========================================
def main():
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

    rx, ry, rw, rh = get_standard_roi(video_file, CONFIGS['tasma'], "1. Zaznacz CALA TASME STARTOWA")

    r1_x, r1_y, r1_w, r1_h, a1 = get_zoomed_roi(video_file, CONFIGS['czerwony'], "Kask CZERWONY (Tor 1)")
    r2_x, r2_y, r2_w, r2_h, a2 = get_zoomed_roi(video_file, CONFIGS['niebieski'], "Kask NIEBIESKI (Tor 2)")
    r3_x, r3_y, r3_w, r3_h, a3 = get_zoomed_roi(video_file, CONFIGS['bialy'], "Kask BIALY (Tor 3)")
    r4_x, r4_y, r4_w, r4_h, a4 = get_zoomed_roi(video_file, CONFIGS['zolty'], "Kask ZOLTY (Tor 4)")

    rider_coords = [(r1_x, r1_y, r1_w, r1_h), (r2_x, r2_y, r2_w, r2_h), (r3_x, r3_y, r3_w, r3_h), (r4_x, r4_y, r4_w, r4_h)]
    riders_active = [a1, a2, a3, a4]

    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened(): return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    ms_per_frame = 1000.0 / fps
    W, H = int(cap.get(3)), int(cap.get(4))

    cx1 = max(0, rx - DISPLAY_PAD)
    cy1 = max(0, ry - DISPLAY_PAD)
    cx2 = min(W, rx + rw + DISPLAY_PAD)
    cy2 = min(H, ry + rh + DISPLAY_PAD)
    crop_w = cx2 - cx1
    crop_h = cy2 - cy1
    out_w = crop_w * ZOOM_SCALE
    out_h = crop_h * ZOOM_SCALE

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, OUTPUT_NAME)
    out_video = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'XVID'), fps, (out_w, out_h))

    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=40, detectShadows=False)
    riders_fgbg = [cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=25, detectShadows=False) for _ in range(4)]

    win_name = 'Telemetria Startu - Czas Reakcji (ZOOM)'
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, 1280, 720)

    last_valid_line = None
    missing_frames = 0
    MAX_MISSING = 9999
    num_columns = 20
    col_width = rw // num_columns
    frame_count = 0
    WARMUP_FRAMES = 5
    state = "OCZEKIWANIE"
    initial_y = None
    prev_y = None
    exact_start_ms = 0.0
    exact_end_ms = 0.0
    min_y_reached = None
    time_at_min_y = 0.0
    frames_without_progress = 0
    smoothed_m = None

    riders_data = [[0.0, False, "Czekam..."] if riders_active[i] else [0.0, True, "WYKLUCZONY"] for i in range(4)]
    rider_colors = [(0, 255, 255), (255, 0, 0), (255, 255, 255), (0, 0, 255)] 
    
    # NOWOŚĆ: Pamięć pikseli z poprzedniej klatki dla każdego zawodnika
    riders_prev_pixels = [0, 0, 0, 0]

    print(f"Telemetria ZOOM włączona... Wycinek: {out_w}x{out_h} px ({ZOOM_SCALE}x)")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame_count += 1
        current_time_ms = frame_count * ms_per_frame

        # =========================================================
        # 1. ZAWODNICY - Z WEHIKUŁEM CZASU (INTERPOLACJĄ)
        # =========================================================
        kernel_rider = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

        for i, (kx, ky, kw, kh) in enumerate(rider_coords):
            if not riders_active[i]:
                continue

            crop = frame[ky:ky+kh, kx:kx+kw].copy()
            mask = riders_fgbg[i].apply(crop)
            _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_rider)

            active_pixels = cv2.countNonZero(mask)

            box_color = (0, 255, 0) if riders_data[i][1] else rider_colors[i]
            cv2.rectangle(frame, (kx, ky), (kx + kw, ky + kh), box_color, 2)

            if frame_count > WARMUP_FRAMES and not riders_data[i][1]:
                if active_pixels > 35:
                    riders_data[i][1] = True
                    if state == "OCZEKIWANIE":
                        riders_data[i][0] = -1.0
                        riders_data[i][2] = "FALSTART!"
                    else:
                        # NOWOŚĆ: Interpolacja dla zawodników (odzyskiwanie ułamków z 50ms)
                        prev_p = riders_prev_pixels[i]
                        if active_pixels != prev_p:
                            ratio = (35.0 - prev_p) / (active_pixels - prev_p)
                        else:
                            ratio = 0
                            
                        # Zabezpieczenie przed dziwnymi skokami matematycznymi
                        ratio = max(0.0, min(1.0, ratio)) 
                        exact_rider_ms = (current_time_ms - ms_per_frame) + (ratio * ms_per_frame)
                        riders_data[i][0] = exact_rider_ms

            # Zapisujemy stan do kolejnej klatki
            riders_prev_pixels[i] = active_pixels

        # =========================================================
        # 2. TAŚMA
        # =========================================================
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

            search_top = int(rh * 0.35) if last_valid_line is None else max(0, int((last_valid_line[0] + last_valid_line[1]) / 2) - 150)
            search_bottom = rh if last_valid_line is None else min(rh, int((last_valid_line[0] + last_valid_line[1]) / 2) + 25)

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

                    m, c = np.polyfit(X, Y, 1)

                    if abs(m) < 0.4:
                        raw_y_center = np.mean(Y)

                        if smoothed_m is None:
                            smoothed_m = m
                        else:
                            smoothed_m = 0.85 * smoothed_m + 0.15 * m

                        x_center = rw / 2.0
                        new_c = raw_y_center - (smoothed_m * x_center)

                        y_left = smoothed_m * 0 + new_c
                        y_right = smoothed_m * rw + new_c
                        current_line = (y_left, y_right)

            if current_line is not None and last_valid_line is not None:
                prev_line_y = (last_valid_line[0] + last_valid_line[1]) / 2
                curr_line_y = (current_line[0] + current_line[1]) / 2
                if curr_line_y > prev_line_y + 15:
                    current_line = None

            curr_y_center = (current_line[0] + current_line[1]) / 2 if current_line else None

            if state == "OCZEKIWANIE":
                if curr_y_center is not None:
                    if initial_y is None:
                        initial_y = curr_y_center

                    if curr_y_center <= initial_y - 3.0 and prev_y is not None:
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

                    if curr_y_center > min_y_reached + 12.0:
                        exact_end_ms = time_at_min_y
                        state = "ZAKONCZONO"
                else:
                    frames_without_progress += 1

                if state == "RUCH" and frames_without_progress >= 10:
                    exact_end_ms = time_at_min_y
                    state = "ZAKONCZONO"

                prev_y = curr_y_center

            if current_line is not None:
                last_valid_line = current_line
                missing_frames = 0
                color = (0, 255, 0)
            else:
                missing_frames += 1
                color = (0, 180, 0)
                if missing_frames >= MAX_MISSING:
                    last_valid_line = None
                    smoothed_m = None

            if last_valid_line is not None:
                pt1 = (rx, ry + int(last_valid_line[0]))
                pt2 = (rx + rw, ry + int(last_valid_line[1]))
                cv2.line(frame, pt1, pt2, color, 3)

        cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (50, 50, 50), 1)

        # =========================================================
        # 3. WYCINEK + POWIĘKSZENIE
        # =========================================================
        crop_frame = frame[cy1:cy2, cx1:cx2]
        scaled = cv2.resize(crop_frame, (out_w, out_h), interpolation=cv2.INTER_LINEAR)

        # =========================================================
        # 4. OSD HUD
        # =========================================================
        cv2.rectangle(scaled, (10, 10), (620, 360), (0, 0, 0), -1)

        cv2.putText(scaled, f"STATUS: {state}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(scaled, f"Czas wideo: {current_time_ms:.1f} ms", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)

        if exact_start_ms > 0:
            cv2.putText(scaled, f"Zwolnienie zamka: {exact_start_ms:.1f} ms", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(scaled, "Zwolnienie zamka: --- ms", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

        if state == "RUCH":
            obecny_czas_unoszenia = current_time_ms - exact_start_ms
            cv2.putText(scaled, f"Czas unoszenia: {obecny_czas_unoszenia:.1f} ms", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        elif state == "ZAKONCZONO":
            calkowity_czas_unoszenia = exact_end_ms - exact_start_ms
            cv2.putText(scaled, f"Czas unoszenia: {calkowity_czas_unoszenia:.1f} ms", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(scaled, "Czas unoszenia: --- ms", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

        cv2.putText(scaled, "-------------------------------------------------", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

        names = ["Kask ZOLTY (T1):", "Kask NIEBIESKI (T2):", "Kask BIALY    (T3):", "Kask CZERWONY (T4):"]
        for j in range(4):
            y_pos = 200 + (j * 40)

            if riders_active[j] and riders_data[j][1] and riders_data[j][0] > 0 and state in ["RUCH", "ZAKONCZONO"]:
                rt = riders_data[j][0] - exact_start_ms
                riders_data[j][2] = f"{rt:.1f} ms"

            text_color = (0, 255, 0) if "ms" in riders_data[j][2] else ((0, 0, 255) if "FALSTART" in riders_data[j][2] else (150, 150, 150))

            cv2.putText(scaled, names[j], (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.7, rider_colors[j], 2)
            cv2.putText(scaled, riders_data[j][2], (300, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)

        out_video.write(scaled)

        cv2.imshow(win_name, scaled)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    out_video.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()