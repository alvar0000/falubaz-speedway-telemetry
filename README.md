# Analiza startu żużlowego z nagrań wideo

Projekt w Pythonie i OpenCV do automatycznej analizy startów żużlowych. Projekt realizowany we współpracy z klubem **Falubaz Zielona Góra**, miastem oraz Uniwersytetem Zielonogórskim. Program wykrywa ruch taśmy startowej, oblicza moment jej zwolnienia i mierzy czas reakcji zawodników na podstawie ruchu w zaznaczonych obszarach przy ich kołach.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-komputerowe%20widzenie-5C3EE8?logo=opencv&logoColor=white)

## Co potrafi projekt

- wykrywa białą, poruszającą się taśmę startową;
- dopasowuje do niej stabilną linię metodą najmniejszych kwadratów;
- mierzy moment zwolnienia zamka i czas unoszenia taśmy;
- mierzy reakcję maksymalnie czterech zawodników;
- sygnalizuje ruch przed zwolnieniem taśmy jako potencjalny falstart;
- generuje film wynikowy z linią detekcji i panelem telemetrycznym;
- oferuje powiększony widok oraz interpolację czasu reakcji pomiędzy klatkami.

## Jak to działa

1. Użytkownik zaznacza ROI, czyli obszar zawierający taśmę oraz małe obszary przy kołach zawodników.
2. Algorytm łączy detekcję ruchu tła (`MOG2`) z maską jasnych pikseli, aby odseparować taśmę od tła.
3. Obraz jest czyszczony filtrem morfologicznym nastawionym na elementy poziome.
4. Z punktów znalezionych w kolejnych kolumnach ROI wybierane są wartości zgodne z medianą, a następnie dopasowywana jest prosta opisująca położenie taśmy.
5. Zmiana wysokości tej prostej wyznacza początek i zakończenie unoszenia taśmy.
6. Ruch w ROI zawodnika, po zwolnieniu taśmy, wyznacza jego czas reakcji. W wersji `zoom` moment przekroczenia progu ruchu jest interpolowany w obrębie pojedynczej klatki.

## Najważniejsze skrypty

| Plik | Zastosowanie |
| --- | --- |
| `analiza_tasmy_zoom.py` | Główna, rekomendowana wersja analizy: powiększony wycinek, HUD i interpolowany czas reakcji. |
| `analiza_tasmy.py` | Pełnokadrowa analiza taśmy i reakcji maksymalnie czterech zawodników. |
| `telemetria.py` | Analiza samej taśmy wraz z czasem zwolnienia i unoszenia. |
| `analiza_pro.py` | Wizualizacja stabilnego śledzenia linii taśmy metodą LSQ. |
| `wybierz_roi.py` | Ręczne zaznaczanie ROI taśmy i zapis do `roi_coords.json`. |
| `mask_visual.py` | Podgląd maski używanej przez algorytm — przydatny podczas strojenia parametrów. |
| `wycinarka.py` | Przycinanie nagrania do wskazanego fragmentu kadru. |
| `count_frames.py` | Kontrola rzeczywistej liczby klatek i FPS pliku wideo. |

## Uruchomienie

### Wymagania

- Python 3.10 lub nowszy
- `opencv-python`
- `numpy`

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install opencv-python numpy
```

### 1. Dodaj materiał wideo

Umieść nagranie w katalogu `source/`. Nazwę pliku ustaw w stałej `VIDEO_PATH` w wybranym skrypcie, np.:

```python
VIDEO_PATH = "start_np_11.mp4"
```

### 2. Zaznacz obszar taśmy

```bash
python wybierz_roi.py
```

Zaznaczenie zostanie zapisane w `roi_coords.json`.

### 3. Uruchom analizę

```bash
python analiza_tasmy_zoom.py
```

Przy pierwszym uruchomieniu skrypt poprosi też o zaznaczenie precyzyjnych ROI przy kołach zawodników. Są one zapisywane jako `roi_rider_1.json`–`roi_rider_4.json`, dzięki czemu przy kolejnym uruchomieniu nie trzeba wybierać ich ponownie.

Film wynikowy trafia do katalogu `results/`. Podgląd można przerwać klawiszem `q`.

## Struktura katalogów

```text
.
├── source/                 # nagrania wejściowe
├── results/                # wygenerowane filmy wynikowe
├── roi_coords.json         # ROI taśmy
├── roi_rider_*.json        # ROI zawodników
├── analiza_tasmy_zoom.py   # główny pipeline
└── ...
```

## Konfiguracja i wskazówki

- Do każdego ujęcia kamery należy wybrać nowe ROI — współrzędne są zapisane w pikselach.
- Czułość detekcji jest regulowana m.in. przez `varThreshold`, próg jasności (`180`) oraz liczbę pikseli ruchu przy zawodniku (`35`).
- Program zakłada, że taśma przemieszcza się ku górze w obrazie. Ta reguła ogranicza błędne detekcje spowodowane dymem, kaskami lub tłumem.
- Wyniki mają charakter analityczny. Dokładność zależy od FPS, jakości nagrania, widoczności taśmy i prawidłowego dobrania ROI.

## Technologie

- Python
- OpenCV
- NumPy
- przetwarzanie wideo i klasyczne metody computer vision

