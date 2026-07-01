import cv2
import numpy as np
import threading

DIGIT_H = 48
DIGIT_W = 32
MAX_SAMPLES = 20


class DigitTemplateCache:
    def __init__(self):
        self._slots = {i: [] for i in range(10)}
        self._mean_cache = {}
        self._lock = threading.Lock()

    def add_template(self, digit: int, img: np.ndarray):
        norm = _normalize_digit(img)
        if norm is None:
            return
        with self._lock:
            slot = self._slots[digit]
            if len(slot) >= MAX_SAMPLES:
                slot.pop(0)
            slot.append(norm)
            self._mean_cache.pop(digit, None)

    def get_mean_template(self, digit: int) -> np.ndarray | None:
        with self._lock:
            if digit in self._mean_cache:
                return self._mean_cache[digit]
            slot = self._slots[digit]
            if not slot:
                return None
            mean = np.mean(slot, axis=0).astype(np.uint8)
            self._mean_cache[digit] = mean
            return mean

    def has_templates(self) -> bool:
        with self._lock:
            return any(len(s) > 0 for s in self._slots.values())

    def match_digit(self, img: np.ndarray) -> tuple[int, float]:
        norm = _normalize_digit(img)
        if norm is None:
            return -1, 0.0
        best_digit = -1
        best_score = -1.0
        for d in range(10):
            tmpl = self.get_mean_template(d)
            if tmpl is None:
                continue
            res = cv2.matchTemplate(norm, tmpl, cv2.TM_CCOEFF_NORMED)
            score = float(res[0][0])
            if score > best_score:
                best_score = score
                best_digit = d
        return best_digit, best_score


def _normalize_digit(img: np.ndarray) -> np.ndarray | None:
    if img is None or img.size == 0:
        return None
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(img, (DIGIT_W, DIGIT_H), interpolation=cv2.INTER_AREA)
    _, binary = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def segment_digits(roi_img: np.ndarray) -> list[np.ndarray]:
    if roi_img is None or roi_img.size == 0:
        return []
    gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY) if len(roi_img.shape) == 3 else roi_img.copy()
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # invert if background is white (more white pixels than black)
    if np.mean(binary) > 127:
        binary = cv2.bitwise_not(binary)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h_img = roi_img.shape[0]
    min_h = int(h_img * 0.35)

    boxes = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if h >= min_h and w >= 3:
            boxes.append((x, y, w, h))

    boxes.sort(key=lambda b: b[0])

    digits = []
    for x, y, w, h in boxes:
        digit_img = gray[y:y+h, x:x+w]
        digits.append(digit_img)
    return digits


def learn_from_ocr_result(cache: DigitTemplateCache, roi_img: np.ndarray, number: int):
    if number <= 0:
        return
    digit_str = str(number)
    digit_imgs = segment_digits(roi_img)
    if len(digit_imgs) != len(digit_str):
        return
    for ch, img in zip(digit_str, digit_imgs):
        cache.add_template(int(ch), img)


def recognize_by_template(cache: DigitTemplateCache, roi_img: np.ndarray) -> tuple[float, float]:
    if not cache.has_templates():
        return 0.0, 0.0
    digit_imgs = segment_digits(roi_img)
    if not digit_imgs:
        return 0.0, 0.0

    result_digits = []
    total_score = 0.0
    for img in digit_imgs:
        d, score = cache.match_digit(img)
        if d < 0:
            return 0.0, 0.0
        result_digits.append(d)
        total_score += score

    number = int(''.join(str(d) for d in result_digits))
    avg_score = total_score / len(digit_imgs)
    return float(number), avg_score
