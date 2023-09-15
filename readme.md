# Quran Chroma TG Bot

Quran Chroma Generator is a Telegram bot built with Python to generate videos of Quran verses with a black background, which helps create reels and shorts.

## Installation

1. Before any other step, ensure you have [ImageMagick](https://imagemagick.org/index.php) installed on your system. Since the bot makes use of moviepy, installing ImageMagick is mandatory.
2. **Optional:** Create a Python virtual environment.
3. Install the requirements by running

   ```
   pip install -r requirements.txt
   ```

## Deployment

We discuss in this section how to put the bot to work.

### Add a reciter

Adding a reciter should be done in two steps:

1. Add the reciter details under `commands.json`. By details, we mean the name (preferably JSON encoded) and the name of the directory containing recitation audio files.

   ```json
   "reciters": [
           {
               "name": "\u064a\u0627\u0633\u064a\u0646 \u0641\u0642\u064a\u0647 \u0627\u0644\u062c\u0632\u0627\u0626\u0631\u064a",
               "folder": "warsh_yassin_al_jazaery_64kbps"
           },
           {
               "name": "\u0639\u0644\u064a \u0639\u0628\u062f \u0627\u0644\u0644\u0647 \u062c\u0627\u0628\u0631",
               "folder": "ali_jaber_64kbps"
           },
   ...
   ```
2. Place the audio directory of the added recitation under `assets/reciters`. Ensure the added directory name is the same as in `commands.json`. Also, the recitations should be organized in mp3 files for every and each verse.

   ```
   001001.mp3
   001002.mp3
   ...
   114005.mp3
   114006.mp3
   ```

You can download examples for reciter audio files from this [Drive folder](https://drive.google.com/drive/folders/1l2CBX86mNv_k7uzRKB0IY3F9QX9bMlsh?usp=sharing).

The archive should be extracted in `assets/reciters`. If the folder reciters doesn't exist, create it. The result after the extraction shoud be similar to

```
assets/
	reciters/
		reciter_1/
			001001.mp3
			...
			114006.mp3
		reciter_1/
			001001.mp3
			...
			114006.mp3
...
```

### Edit the font

Font files are found in `assets/font`. If you add a new font, ensure the change is reflected in `config/config.json`. Other options are also available in this file.

```json
{
    "video_width": 720,
    "video_height": 1280,
    "font_name": "KFGQPC.otf",
    "text_size": 58
}
```

### Run the bot

1. Refer to Telegram documentation to create a bot and retrieve an API Token. Change the file `quran_bot.py` accordingly.

   ```python
   bot_instance = QuranBot('YOUR_TG_TOKEN')
   asyncio.run(bot_instance.bot.polling())
   ```
2. Run the script `python quran_bot.py`

Please don't forget to report any issues!
