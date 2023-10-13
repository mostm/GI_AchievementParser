import json
import logging
from time import sleep

import httpx
from tqdm import tqdm

from utils import get_asset_path


def submit_ids(ids_to_submit: list[int], cookies: str):
    cookies_as_dict = {cookie.split('=', 1)[0]: cookie.split('=', 1)[1] for cookie in cookies.split(';')}

    with httpx.Client(http2=True, cookies=cookies_as_dict) as client:
        for id_to_submit in tqdm(ids_to_submit):
            # print(f'Загружаем achievementId {id_to_submit}')
            result = client.post('https://genshin-center.com/api/achievements/update',
                                 json={'achievementId': id_to_submit, 'done': True})
            result.raise_for_status()
            sleep(0.1)


def main():
    cookies = input('Введите свои куки из genshin-center.com и нажмите "Enter": ')
    assets = get_asset_path()
    with open("results\\achievements.json", "r", encoding='utf-8') as file:
        completed_achievements = json.load(file)
    with open(assets['gc_achievements.json'], "r", encoding='utf-8') as file:
        gc_achievements = json.load(file)
    # gc_map = {v['name']: k for k, v in gc_achievements.items()}
    gc_map = {}
    for k, v in gc_achievements.items():
        ach_name = v['name']
        if gc_map.get(ach_name):
            gc_map[ach_name].append(int(k))
        else:
            gc_map[ach_name] = [int(k)]

    ids_to_submit = []
    for k in completed_achievements.keys():
        gc_ids = gc_map.get(k)
        if not gc_ids:
            print(f'Пропускаем {k} (нет в базе)')
            continue
        # if gc_achievements.get(str(gc_ids[0]), {'category_id': 123})['category_id'] == 0:
        ids_to_submit += gc_ids
    submit_ids(ids_to_submit, cookies)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARN, format='%(asctime)s %(levelname)s %(message)s')
    try:
        main()
    except Exception as exc:
        logging.exception(exc)
    input('Нажмите "Enter" для выхода.')
