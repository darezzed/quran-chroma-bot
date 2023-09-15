import re
import json
import logging
import asyncio
import time
from datetime import datetime
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from concurrent.futures import ThreadPoolExecutor
from bin.chroma_maker import ChromaMaker

class QuranBot:
    def __init__(self, token):
        self.bot = AsyncTeleBot(token)
        self.user_data = {}
        self.command_file = 'commands.json'
        self.quran_json = 'assets/quran.json'
        self._load_strings()
        self.executor = ThreadPoolExecutor(max_workers=16)  # Adjust the number of workers as needed

        # Register handlers
        self.bot.message_handler(commands=['start'])(self.start)
        self.bot.message_handler(func=lambda message: not self.user_data.get(message.chat.id, {}).get('surah'))(self.get_surah)
        self.bot.message_handler(func=lambda message: not self.user_data.get(message.chat.id, {}).get('ayah_range'))(self.get_ayah_range)
        self.bot.message_handler(func=lambda message: self.user_data.get(message.chat.id, {}).get('state') == 'awaiting_reciter')(self.process_text_input)
        self.bot.callback_query_handler(func=lambda call: True)(self.callback_query)

    def _load_strings(self):
        with open(self.command_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        self.select_surah = data["select_surah"]
        self.select_ayah = data["select_ayah"]
        self.select_reciter = data["select_reciter"]
        self.error_surah = data["error_surah"]
        self.error_ayah = data["error_ayah"]
        self.error_reciter = data["error_reciter"]
        self.error_range = data["error_range"]
        self.generating = data["generating"]
        self.feedback_prompt = data["feedback_prompt"]
        self.reciters = self._load_reciters(data)
        with open(self.quran_json, 'r', encoding="utf8") as surah_file:
            self.json_data = json.load(surah_file)

    def _load_reciters(self, data=None):
        if data is None:
            with open(self.command_file, "r", encoding="utf-8") as content:
                data = json.load(content)
        
        return data["reciters"]

    def _add_surah_name(self, string, surah_number):
        title = self.json_data[str(surah_number)]["titleAr"]
        return string.replace("{placeholder}", title)
    
    def _add_reciter_name(self, string, reciter_name):
        return string.replace("{placeholder}", reciter_name)

    def _get_surah_index_from_name(self, surah_name):
        for surah_index, surah_info in self.json_data.items():
            if surah_info["title"] == surah_name or surah_info["titleAr"] == surah_name:
                return int(surah_index)
        return None  # Return None if the surah name is not found

    def _show_reciter_btns(self, markup):
        self.reciters = self._load_reciters()
        row_btns = []

        for reciter in self.reciters:
            # Add the button to the current row
            row_btns.append(InlineKeyboardButton(reciter["name"], callback_data=reciter["name"]))
            
            # If we have 2 buttons in the row, add them to the markup and reset the row
            if len(row_btns) == 2:
                markup.add(*row_btns)
                row_btns = []

        # Add any remaining buttons if the total number of reciters is odd
        if row_btns:
            markup.add(*row_btns)
        
        return markup

    async def _send_reciter_buttons(self, chat_id):
        markup = self._show_reciter_btns(InlineKeyboardMarkup())
        await self.bot.send_message(chat_id, self.select_reciter, reply_markup=markup)

    async def start(self, message):
        await self.bot.send_message(message.chat.id, self.select_surah)
        self.user_data[message.chat.id] = {}

    async def get_surah(self, message):
        user_input = message.text.strip()
        # Try to interpret the input as a surah number
        try:
            surah_number = int(user_input)
            if str(surah_number) not in self.json_data:
                await self.bot.send_message(message.chat.id, self.error_surah)
                return  # Exit the function early
            self.user_data[message.chat.id]['surah'] = surah_number
            
        except ValueError:  # The input is not a number, so treat it as a surah name
            surah_name = user_input
            surah_index = self._get_surah_index_from_name(surah_name)
            
            if surah_index is None:  # Surah name not found in the JSON data
                await self.bot.send_message(message.chat.id, self.error_surah)
                return  # Exit the function early
            self.user_data[message.chat.id]['surah'] = surah_index

        await self.bot.send_message(message.chat.id, self._add_surah_name(self.select_ayah, self.user_data[message.chat.id]['surah']))

    async def get_ayah_range(self, message):
        ayah_input = message.text.strip()
        surah_index = str(self.user_data[message.chat.id]['surah'])
        max_ayah = self.json_data[surah_index]['verses']

        # Use regex to capture the desired patterns
        range_pattern = re.compile(r"(\d+)\s*-\s*(\d+)")
        single_pattern = re.compile(r"(\d+)")

        range_match = range_pattern.match(ayah_input)
        single_match = single_pattern.match(ayah_input)

        if range_match:
            start_ayah, end_ayah = map(int, range_match.groups())

            if end_ayah - start_ayah + 1 > 5:
                await self.bot.send_message(message.chat.id, self.error_range)
                return

            if start_ayah > end_ayah or start_ayah < 1 or end_ayah > max_ayah:
                await self.bot.send_message(message.chat.id, self.error_ayah)
                return
            self.user_data[message.chat.id]['ayah_range'] = (start_ayah, end_ayah)

        elif single_match:
            ayah_number = int(single_match.group(1))
            if ayah_number < 1 or ayah_number > max_ayah:
                await self.bot.send_message(message.chat.id, self.error_ayah)
                return
            self.user_data[message.chat.id]['ayah_range'] = ayah_number

        else:
            await self.bot.send_message(message.chat.id, self.error_ayah)
            return
        
        markup = self._show_reciter_btns(InlineKeyboardMarkup())
        
        await self.bot.send_message(message.chat.id, self.select_reciter, reply_markup=markup)
        self.user_data[message.chat.id]['state'] = 'awaiting_reciter'

    async def process_text_input(self, message):
        chat_id = message.chat.id
        user_state = self.user_data.get(chat_id, {}).get('state')

        if user_state == 'awaiting_reciter':
            reciter_name = message.text.strip()
            
            if any(reciter["name"] == reciter_name for reciter in self.reciters):
                self.user_data[chat_id]['reciter'] = reciter_name
                await self.generate_video(message)
            else:
                await self.bot.send_message(chat_id, self.error_reciter)
                await self._send_reciter_buttons(chat_id)


    async def callback_query(self, call):
        chosen_reciter_name = call.data

        # Retrieve the reciter's folder from the list
        reciter_folder = next((reciter["folder"] for reciter in self.reciters if reciter["name"] == chosen_reciter_name), None)

        if reciter_folder == None:
            await self.bot.send_message(call.message.chat.id, self.error_reciter)
            await self._send_reciter_buttons(call.message.chat.id)
            return

        # Store the chosen reciter name in user_data
        self.user_data[call.message.chat.id]['reciter'] = chosen_reciter_name

        surah = self.user_data[call.message.chat.id]['surah']
        ayah_range = self.user_data[call.message.chat.id]['ayah_range']
        await self.bot.answer_callback_query(call.id)
        await self.bot.send_message(call.message.chat.id, f"{self._add_reciter_name(self.generating, chosen_reciter_name)}")
        
        if isinstance(ayah_range, int):
            # Handle single Ayah number
            start_ayah = end_ayah = ayah_range
        elif isinstance(ayah_range, tuple):
            # Handle Ayah range
            start_ayah, end_ayah = ayah_range

        video_maker = ChromaMaker( 
                    surah=surah, 
                    start_ayah=start_ayah,
                    end_ayah=end_ayah,
                    reciter_dir=reciter_folder)
            
        # Run the synchronous video generation in a separate thread
        video_stream = await asyncio.get_event_loop().run_in_executor(self.executor, video_maker.generate_video)

        # Send the generated video back in the conversation
        await self.bot.send_video(call.message.chat.id, video_stream)
        with open("log.txt", "a") as file:
            log_entry = f"{datetime.now()} [{surah}][{start_ayah},{end_ayah}][{reciter_folder}]\n"
            file.write(log_entry)
        # Close the BytesIO stream after sending
        video_stream.close()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('telebot')
    logger.setLevel(logging.DEBUG)  # This will show all messages sent to/from the bot

    while True:
        try:
            bot_instance = QuranBot('YOUR_TG_TOKEN')
            asyncio.run(bot_instance.bot.polling())
        except Exception as e:
            logger.error(f"Exception occurred: {e}")
            time.sleep(10)  # Sleep for 10 seconds before retrying

