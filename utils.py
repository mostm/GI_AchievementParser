import io
import os.path
import sys
import threading
import timeit

import psutil
import pytesseract
from PIL import Image, ImageChops
from pywinauto.win32structures import RECT


def find_process(name: str):
    matching = [x for x in psutil.process_iter() if x.name() == name]
    if len(matching) == 0:
        return None
    return matching[0]


def scale_coords_to_resolution(coords: tuple, resolution: tuple):
    x, y = coords
    base_x, base_y = x / 2560, y / 1440
    return int(base_x * resolution[0]), int(base_y * resolution[1])


def scale_box_to_resolution(box: RECT, window_rect: RECT):
    left, top, right, bottom = int(box.left), int(box.top), int(box.right), int(box.bottom)
    base_left, base_top, base_right, base_bottom = left / 2560, top / 1440, right / 2560, bottom / 1440
    low_res_left = int(base_left * window_rect.width()) + int(window_rect.left)
    low_res_top = int(base_top * window_rect.height()) + int(window_rect.top)
    low_res_right = int(base_right * window_rect.width()) + low_res_left
    low_res_bottom = int(base_bottom * window_rect.height()) + low_res_top
    return RECT(low_res_left, low_res_top, low_res_right, low_res_bottom)


def bold_color_mask(image: Image.Image, target_color=(85, 85, 85), threshold=50):
    # Create a mask for the gradient effect
    start_mask = timeit.default_timer()

    mask = Image.new("L", image.size)
    for x in range(image.width):
        for y in range(image.height):
            pixel = image.getpixel((x, y))
            color_difference = sum((a - b) ** 2 for a, b in zip(pixel, target_color))
            if color_difference <= threshold ** 2:
                mask.putpixel((x, y), 0)
            else:
                mask.putpixel((x, y), 255)

    end_mask = timeit.default_timer()

    # Apply the mask to the original image
    composited = ImageChops.composite(Image.new("RGB", image.size, (255, 255, 255)), image, mask)
    end_composite = timeit.default_timer()
    # print(f"Mask: {end_mask - start_mask}, Composite: {end_composite - end_mask}")
    return composited


def generate_achievement_boxes(achievement: RECT, status: RECT | None, height_adjust: int,
                               key: str = "end_achievement", count: int = 6, inversed: bool = False) -> dict:
    box_coords = {}

    for adjust_count in range(0, count):
        generated_achievement_y = int(achievement.top) - (adjust_count * height_adjust)
        if inversed:
            generated_achievement_y = int(achievement.top) + (adjust_count * height_adjust)

        box_coords[f"{key}_{adjust_count}"] = RECT(achievement.left, generated_achievement_y,
                                                   achievement.right,
                                                   achievement.bottom)  # it's actually width and height
        if status is not None:
            generated_status_y = int(status.top) - (adjust_count * height_adjust)
            if inversed:
                generated_status_y = int(status.top) + (adjust_count * height_adjust)

            box_coords[f"{key}_{adjust_count}_status"] = RECT(status.left, generated_status_y,
                                                              status.right, status.bottom)

    return box_coords


def scan_image(image: str | bytes) -> str:
    data = image
    if isinstance(image, str):
        with open(image, 'rb') as file:
            data = file.read()

    default_tesseract_path = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    if not os.path.exists(default_tesseract_path):
        raise Exception(f"Can't find tesseract at {default_tesseract_path}")
    else:
        pytesseract.pytesseract.tesseract_cmd = default_tesseract_path
        fake_file = io.BytesIO(data)
        return pytesseract.image_to_string(Image.open(fake_file), lang='eng')


def get_asset_path():
    assets = {
        'gc_achievements.json': 'assets\\gc_achievements.json',
        'gc_categories.json': 'assets\\gc_categories.json',
    }
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return {k: os.path.join(sys._MEIPASS, v) for k, v in assets.items()}
    return assets
