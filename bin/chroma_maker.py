import os
import json
import tempfile
from io import BytesIO
from PIL import ImageFont
from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, concatenate_audioclips, AudioFileClip
import moviepy.audio.fx.all as afx


class ChromaMaker:

    def __init__(self, config_file="config.json", surah=1, start_ayah=1, end_ayah=1, reciter_dir="warsh_yassin_al_jazaery_64kbps", background="#000000"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        asset_dir = '../assets'
        config_dir = '../config'
        
        config = self.load_config(os.path.join(base_dir, config_dir, config_file))
        self.quran_dir = os.path.join(base_dir, asset_dir, 'quran')
        self.font_dir = os.path.join(base_dir, asset_dir, 'font')
        self.reciters_dir = os.path.join(base_dir, asset_dir, 'reciters')

        self.video_width = config.get("video_width", 720)
        self.video_height = config.get("video_height", 1280)
        self.font_size = config.get("font_size", 48)
        self.font_path = os.path.join(self.font_dir, config.get("font_name"))
        self.audio_dir = os.path.join(self.reciters_dir, reciter_dir)
        self.surah = surah
        self.start_ayah = start_ayah
        self.end_ayah = end_ayah
        self.background = background

    def load_config(self, filename):
        try:
            with open(filename, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Error loading configuration from {filename}")
            return {}

    def generate_video(self):
        verses = self.wrap_verses()
        if verses != None:
            return self.create_scrolling_text_video(verses, self.load_audio())
        pass

    def create_scrolling_text_video(self, input_text, audio_clip):
        # Video parameters
        video_duration = audio_clip.duration  # in seconds
        video_size = (self.video_width, self.video_height)  # width x height

        input_text = self.preprocess_text(input_text)

        color_video = ColorClip(size=video_size, 
                                color=self.hex_to_rgb(self.background), 
                                duration=video_duration)

        text_clip = TextClip(input_text, 
                             fontsize=self.font_size, 
                             color=self.get_text_color(self.background), 
                             font=self.font_path, 
                             align='center')

        # Calculate the start and end positions for the scrolling effect
        start_y = video_size[1]  # start from the bottom
        end_y = -text_clip.size[1]  # end when the text is no longer visible

        # Define a function to calculate the position of the text at any given time
        def scroll_position(t):
            return ('center', start_y - t * (start_y - end_y) / video_duration)

        fade = video_duration/3
        # Set the position of the text clip based on the current time
        scrolling_text = text_clip.set_position(scroll_position).set_duration(video_duration).crossfadein(fade - 1).crossfadeout(fade)

        final_video = CompositeVideoClip([color_video, scrolling_text])

        # Set the audio of the final video to the provided audio_clip
        final_video = final_video.set_audio(audio_clip)

        # Generate a temporary filename
        temp_filename = tempfile.mktemp(suffix=".mp4")

        # Save the final video with audio to the temporary file
        final_video.write_videofile(
            temp_filename,  
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="64K", 
            threads=32, 
            ffmpeg_params=['-safe', '0'],
            fps=25)

        # Read the contents of the temporary file into a BytesIO object
        with open(temp_filename, 'rb') as temp_file:
            video_stream = BytesIO(temp_file.read())

        # Delete the temporary file
        os.remove(temp_filename)

        # Return the BytesIO object containing the video data
        return video_stream
    
    def load_audio(self):
        audio_array = []
        for v in range(self.start_ayah, self.end_ayah + 1):
            audio_file_path = os.path.join(self.audio_dir, f"{self.format_audio_filename(self.surah, v)}")
            
            if os.path.exists(audio_file_path):
                audio_array.append(AudioFileClip(audio_file_path, buffersize=500000))
            else:
                print(f"File not found: {audio_file_path}")
            
        audio_clip = concatenate_audioclips(audio_array)
        audio_clip = afx.audio_fadein(audio_clip, 0.5)
        audio_clip = afx.audio_fadeout(audio_clip, 1)
        return audio_clip

    def get_text_color(self, bg_color):        
        rgb_values = self.hex_to_rgb(bg_color)

        # Normalize RGB values to [0, 1]
        r, g, b = [x/255.0 for x in rgb_values]
        
        # Calculate the luminance
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        
        if luminance > 0.5:
            return 'black'  # Black
        else:
            return 'white'  # White
        
    def hex_to_rgb(self, hex_color):
        # Remove the '#' at the start if it's there
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]

        # Ensure the hex string is valid
        if len(hex_color) != 6:
            raise ValueError("Invalid hexadecimal color format")

        # Split the hex string into RGB components and convert them to integers
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        return (r, g, b)
    
    def format_audio_filename(self, surah, ayah):
        return f"{surah:03}{ayah:03}.mp3"

    def get_verse(self, verse):
        surah_path = os.path.join(self.quran_dir, f'surah_{self.surah}.json')
        try:
            with open(surah_path, 'r', encoding="utf8") as surah_file:
                json_load = json.load(surah_file)
                return json_load['verse'][f'verse_{verse}']
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            print(f"Error accessing verse {verse} in Surah {self.surah}: {e}")
            return None
    
    def is_supported(self, character):
        problematic_chars = ["ۭ"]  # Add any other known problematic characters to this list
        return character not in problematic_chars
    
    def preprocess_text(self, text):
        # Preprocess the text to remove unsupported characters.
        return ''.join([char if self.is_supported(char) else '' for char in text])

    def text_width(self, text):
        font = ImageFont.truetype(self.font_path, self.font_size)
        return font.getlength(text)
    
    def wrap_verses(self):
        wrapped_text = []
        for v in range(self.start_ayah, self.end_ayah + 1):
            text = self.get_verse(v)
            if text:
                words = text.split()
                lines = []
                current_line = words[0]
                for word in words[1:]:
                    if self.text_width(current_line + ' ' + word) <= self.video_width:
                        current_line += ' ' + word
                    else:
                        lines.append(current_line)
                        current_line = word
                lines.append(current_line)
                wrapped_text.append('\n'.join(lines))
        return '\n\n'.join(wrapped_text)