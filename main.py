import ctypes
import io
import json
import logging
import sys
from time import sleep
from typing import Dict, List, Tuple

from PIL import ImageOps, Image
from rapidfuzz import process, fuzz
from rapidfuzz.utils import default_process
from pywinauto import Application
from pywinauto.controls.hwndwrapper import DialogWrapper
from pywinauto.win32structures import RECT

from utils import find_process, scale_coords_to_resolution, scale_box_to_resolution, bold_color_mask, \
    generate_achievement_boxes, scan_image, get_asset_path

button_coords = {
    "main_achievement_button": (885, 542),
    "main_achievement_category": (249, 384),
    "achievement_category": (500, 290),
    "achievement_scroll": (969, 448),
    "category_scroll": (53, 448),
}
box_coords = {
    "achievement_category": RECT(152, 240, 658, 106),
    # "achievement": RECT(1167, 208, 878, 138),
    # "achievement_categories": RECT(1167, 393, 878, 138),
    # "achievement_status": RECT(2208, 195, 220, 161),
}


class AchievementScanner(object):
    debug_mode: bool = True
    debug_disable_postprocessing: bool = False
    window_rect: RECT = None

    buttons: Dict[str, tuple] = {}  # both are scaled for user's resolution
    boxes: Dict[str, RECT] = {}

    achievements: Dict[str, bool] = {}  # title - completed
    categories: List[str] = []
    database: List[str] = []

    # loop
    achievement_id: int = 0
    category_id: int = 0

    def scale_for_resolution(self):
        end_achievement = RECT(1167, 1148, 881, 140)
        end_achievement_status = RECT(2219, 1148, 220, 140)
        end_achievement_adjust = 167
        box_coords.update(generate_achievement_boxes(end_achievement, end_achievement_status, end_achievement_adjust,
                                                     key="end_achievement", count=5))

        end_category = RECT(173, 1213, 697, 109)
        end_category_adjust = 138
        box_coords.update(generate_achievement_boxes(end_category, None, end_category_adjust,
                                                     key="end_category", count=7))

        start_achievement_category = RECT(1167, 400, 900, 126)
        start_achievement_category_status = RECT(2224, 400, 192, 126)
        start_achievement_category_adjust = 167
        box_coords.update(
            generate_achievement_boxes(start_achievement_category, start_achievement_category_status,
                                       start_achievement_category_adjust,
                                       key="start_achievement_category", count=5, inversed=True))

        start_achievement = RECT(1167, 176, 878, 138)
        start_achievement_status = RECT(2208, 176, 220, 138)
        start_achievement_adjust = 167
        box_coords.update(
            generate_achievement_boxes(start_achievement, start_achievement_status, start_achievement_adjust,
                                       key="start_achievement", count=5, inversed=True))

        self.window_rect = self.window.element_info.rectangle
        resolution = (self.window_rect.width(), self.window_rect.height())
        self.buttons = {k: scale_coords_to_resolution(v, resolution) for k, v in button_coords.items()}
        self.boxes = {k: scale_box_to_resolution(v, self.window_rect) for k, v in box_coords.items()}
        self.logger.debug('ready')

    def __init__(self, window: DialogWrapper):
        self.window = window
        self.logger = logging.getLogger("AchievementScanner")
        self.scale_for_resolution()

    def scroll_mouse(self, steps: int, coords: tuple):
        self.logger.debug(f"Scrolling {steps} times at {coords}")
        max_scroll = steps
        scrolled = 0
        while scrolled < max_scroll:
            self.window.wheel_mouse_input(coords=coords, wheel_dist=-100)
            scrolled += 1
            sleep(0.02)
            self.logger.debug(f"{scrolled} / {max_scroll}")
        sleep(0.5)

    def adjust_scroll_steps(self, category: bool = False):
        steps = 35
        if self.achievement_id % 15 == 0:
            steps -= 1
        """
        if self.achievement_id % 14 == 0 or self.achievement_id % 41 == 0:
            steps -= 1
        if self.achievement_id % 42 == 0:
            steps += 1
        """

        if category:
            steps = 6
            if self.category_id % 4 == 0:
                steps -= 1
            if self.category_id % 33 == 0:
                steps -= 1

        return steps

    @staticmethod
    def improve_achievement_text(image: Image.Image) -> Image.Image:
        improved = ImageOps.expand(image, border=20, fill='#f0e9dc')
        improved = bold_color_mask(improved)
        improved = ImageOps.grayscale(improved)
        return improved

    @staticmethod
    def improve_achievement_status(image: Image.Image) -> Image.Image:
        improved = bold_color_mask(image, target_color=(187, 167, 145), threshold=50)
        improved = ImageOps.grayscale(improved)
        return improved

    @staticmethod
    def improve_achievement_category(image: Image.Image) -> Image.Image:
        improved = bold_color_mask(image, target_color=(73, 83, 102), threshold=100)
        improved = ImageOps.grayscale(improved)
        return improved

    def left_click(self, coords: tuple):
        self.logger.debug(f"Clicking at {coords}")
        max_width, max_height = self.window_rect.width(), self.window_rect.height()
        if coords[0] > max_width or coords[1] > max_height:
            self.logger.warning(f"Coords {coords} are out of window bounds ({max_width}, {max_height})")

        self.window.click_input(button='left', coords=coords)

    def go_to_achievements(self):
        for _ in range(0, 4):
            self.window.type_keys('{ESC}')
            sleep(1)
        self.left_click(coords=self.buttons['main_achievement_button'])
        sleep(2)
        self.left_click(coords=self.buttons['main_achievement_category'])
        sleep(2)

    def load_database(self):
        if len(self.database) == 0:
            assets = get_asset_path()

            with open(assets['gc_achievements.json'], "r", encoding='utf-8') as file:
                gc_achievements = json.load(file)
            gc_achievements = [v['name'] for k, v in gc_achievements.items()]
            with open(assets['gc_categories.json'], "r", encoding='utf-8') as file:
                gc_categories = json.load(file)
            gc_categories = [v for k, v in gc_categories.items()]
            self.database = gc_achievements + gc_categories
            self.database.sort()  # Leads to faster results down the line
        return

    def fix_title_by_database(self, title: str):
        self.load_database()
        result, confidence, choices_type = process.extractOne(title, self.database, processor=default_process)
        self.logger.info(f"fix_title_by_database: {title} -> {result} ({confidence} / {choices_type})")
        if confidence >= 90.0:
            return result
        else:
            return title

    def capture_image(self, box: RECT, improve_func: callable = None, debug_name: str = None):
        image = self.window.capture_as_image(rect=box)
        if improve_func and not self.debug_disable_postprocessing:
            image = improve_func(image)
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')
        if self.debug_mode:
            image_path = f'results\\debug_images\\{debug_name}.png'
            image.save(image_path)

        return image_bytes

    def get_center_of_rect(self, box: RECT) -> Tuple[int, int]:
        x, y = int(box.left), int(box.top)
        x += int(box.width() / 2)
        y += int(box.height() / 2)
        # it needs to be within window coords for some reason, when capturing is not
        if self.window_rect.left != 0:
            x -= self.window_rect.left
        if self.window_rect.top != 0:
            y -= self.window_rect.top

        return x, y

    def scan_achievement(self, achievement_name_rect: RECT, status_rect: RECT):
        # Capture
        self.logger.info(f"Capturing achievement {self.achievement_id}")
        self.left_click(coords=self.get_center_of_rect(achievement_name_rect))
        title_image_bytes = self.capture_image(achievement_name_rect, improve_func=self.improve_achievement_text,
                                               debug_name=f"{self.achievement_id}")
        status_image_bytes = self.capture_image(status_rect, improve_func=self.improve_achievement_status,
                                                debug_name=f"{self.achievement_id}_status")

        # Scan
        self.logger.info(f"Sending {self.achievement_id} over for scanning to OCR server")
        self.left_click(coords=self.get_center_of_rect(status_rect))
        scanned_title: str = scan_image(title_image_bytes.getvalue())
        scanned_status: str = scan_image(status_image_bytes.getvalue())

        # Fix small fuckups
        scanned_title = scanned_title.strip()
        if scanned_title == '':
            return '', False
        if scanned_title == "":
            scanned_title = "\n"  # so .splitlines doesn't crash the thing
        scanned_title = scanned_title.splitlines()[0].replace(
            "”", "\"").replace("“", "\"").replace('Deja', 'Déjà')
        scanned_title = self.fix_title_by_database(scanned_title)

        # OCR Result
        self.logger.info(f"Found achievement {self.achievement_id}: {scanned_title}")
        self.logger.info(f"Status: {scanned_status}")
        return scanned_title, fuzz.partial_ratio("Completed", scanned_status, processor=default_process) >= 90.0

    def scan_category(self, category_name_rect, skip: bool = False):
        end_of_list_mode = False  # debug switch
        if end_of_list_mode:
            for _ in range(int(285 / 5)):
                self.scroll_mouse(35, self.buttons['achievement_scroll'])

        category_image_bytes = self.capture_image(category_name_rect, improve_func=self.improve_achievement_category,
                                                  debug_name=f"category_{self.category_id}")
        scanned_category: str = scan_image(category_image_bytes.getvalue()).strip().replace('and\nEternity',
                                                                                            'and Eternity')
        scanned_category = self.fix_title_by_database(scanned_category)
        self.logger.info(f"Found category {self.category_id}: {scanned_category}")
        if scanned_category in self.categories or skip:
            return scanned_category
        self.categories.append(scanned_category)

        last_achievement = None
        skip_scroll = True
        scanned = []
        while not end_of_list_mode:
            if not skip_scroll:
                self.logger.info(f"Scrolling...")
                self.scroll_mouse(self.adjust_scroll_steps(), self.buttons['achievement_scroll'])
                sleep(0.5)

            for i in range(0, 5):  # scan start-of-page items
                self.achievement_id += 1
                skip_scroll = False

                if self.category_id <= 2:
                    self.logger.info('Selected normal achievement boxes')
                    achievement_name_rect = self.boxes[f"start_achievement_{i}"]
                    status_rect = self.boxes[f"start_achievement_{i}_status"]
                else:
                    self.logger.info('Selected namecard achievement boxes')
                    achievement_name_rect = self.boxes[f"start_achievement_category_{i}"]
                    status_rect = self.boxes[f"start_achievement_category_{i}_status"]

                title, completed = self.scan_achievement(achievement_name_rect, status_rect)

                # In-case we are stuck (end-of-page)
                if last_achievement == title or title in scanned:
                    end_of_list_mode = True
                    break
                else:
                    last_achievement = title
                    scanned.append(title)

                if completed:
                    self.achievements[title] = completed

        for i in range(0, 5):  # scan end-of-page items
            self.achievement_id += 1
            achievement_name_rect = self.boxes[f"end_achievement_{i}"]
            status_rect = self.boxes[f"end_achievement_{i}_status"]

            title, completed = self.scan_achievement(achievement_name_rect, status_rect)
            if completed:
                self.achievements[title] = completed

            if title in scanned:  # leave faster whenever possible (caught on Challenger IV)
                break

        return scanned_category

    def scan_categories(self):
        skip_data = False  # debug switch

        last_category = None
        while True:
            self.category_id += 1
            if self.category_id != 1:
                self.logger.info(f"Scrolling to category {self.category_id}")
                self.left_click(coords=self.buttons['category_scroll'])
                sleep(0.5)
                self.scroll_mouse(self.adjust_scroll_steps(category=True), self.buttons['category_scroll'])
                sleep(0.5)
                self.logger.info(f"Clicking on category {self.category_id}")
                self.left_click(coords=self.buttons['achievement_category'])
                sleep(0.5)

            self.logger.info(f"Scanning category {self.category_id}")
            category_name = self.scan_category(self.boxes['achievement_category'], skip=skip_data)
            if category_name == last_category:
                break
            last_category = category_name
            sleep(1)

        for i in range(0, 7):
            self.category_id += 1
            self.logger.info(f"Scanning category (end-of-page) {self.category_id}")
            category_box: RECT = self.boxes[f"end_category_{i}"]
            self.left_click(coords=self.get_center_of_rect(category_box))
            sleep(0.5)
            category_name = self.scan_category(category_box, skip=skip_data)
            if category_name is None:
                break

        return

    @classmethod
    def run(cls):
        app = Application().connect(process=find_process("GenshinImpact.exe").pid)
        main_window: DialogWrapper = app.windows()[0]
        main_window.set_focus()

        inst = cls(main_window)
        inst.go_to_achievements()
        inst.scan_categories()
        with open('results\\achievements.json', 'w') as file:
            json.dump(inst.achievements, file, indent=4)
        return inst


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def check_if_tesseract_is_available():
    default_tesseract_path = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    import os
    if not os.path.exists(default_tesseract_path):
        print("Tesseract не установлен. Пожалуйста, установите его из интернета.")
        print("Tesseract is not installed. Please, install it from the web.")
        print("https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe")
        return False
    return True


if __name__ == '__main__':
    if is_admin():
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.getLogger('PIL').setLevel(logging.WARNING)
        # logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)
        if not check_if_tesseract_is_available():
            input("Press \"Enter\" to exit ")
            sys.exit(1)
        # input("Press \"Enter\" to start ")
        try:
            AchievementScanner.run()
        except Exception as exc:
            logging.exception(exc)
        input("Press \"Enter\" to exit ")
    else:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
