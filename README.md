[English](https://github.com/mostm/GI_AchievementParser/blob/main/README.md) | [Русский](https://github.com/mostm/GI_AchievementParser/blob/main/README_ru.md)

# GI_AchievementParser
In-game achievement parser for Genshin Impact

## Installing
- Download and install [Tesseract OCR](https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe)
- Unpack latest [release](https://github.com/mostm/GI_AchievementParser/releases/latest) in any folder
- Set the game up by following [Inventory Kamera's settings](https://github.com/Andrewthe13th/Inventory_Kamera#setting-up-genshin-impact) - this software operates the same way.

## Running
Run `GI_AchievementParser.exe` (it will ask for admin rights - this is normal) and press Enter in the console window.

Before you do that, keep in mind - do not touch keyboard or mouse during scanning (or you will have to start over).

In-case you want to quit scanning, just spam `Windows` key. It should stop after a few tries.

## Uploading data to Genshin Center

After scan is complete, you might want to upload that data somewhere.

For that, I've included my script for uploading to [Genshin Center](https://genshin-center.com/)

To do that, copy your "Cookies" from Chrome (as a string)

Quick how-to:
1. Press `Ctrl+Shift+I` in open "Genshin Center" window.
2. Open "Network" tab.
3. Select any request out of "session", "profile" or "achievements" (with that exact name).
4. Scroll a bit, until you get to "Request headers". You should see text "Cookie:" and it's data on the right side. Copy it.
![image](https://github.com/mostm/GI_AchievementParser/assets/23155159/1a2f815c-f401-480b-a66a-682ffcc5f519)
5. Run `Загрузчик в Genshin-Center.exe` (it should be in the same folder as `GI_AchievementParser.exe` and it's `results` folder)
6. Paste your Cookies that you just copied.
7. ...
8. PROFIT!

## Known issues
- Does not scan achievements with "steps" (5, 10 and 20 primogems) correctly.
- Achievements with "steps" only counted as "Completed" on the last step (20 primo).
- Achievements besides first category might not parse correctly (most of them are correct), keep this in mind and recheck manually after scanning.
