from PyPDF2 import PdfReader
from gtts import gTTS
import glob
import os


class ListenPDFs:
    def __init__(self, file_path, first_page=1, last_page=-1, language="en"):
        """
        file_path: path to PDF file
        page_number: starting page, default is 1 to start from the beginning
        """
        self.file_path = file_path
        self.reader = PdfReader(file_path)
        if last_page == -1:
            self.number_of_pages = len(self.reader.pages)
        else:
            self.number_of_pages = last_page
        self.current_page = first_page-1
        self.lang = language
    
    def get_text(self):
        while self.current_page < self.number_of_pages:
            self.text = self.reader.pages[self.current_page].extract_text()
            text_path = f"{self.file_path.rsplit('.', 1)[0]}.txt"
            with open(text_path, "a+") as file:
                file.write(self.text)
            self.current_page += 1
        return text_path.rsplit('/', 1)[1]

    def save_mp3(self, text, lang="en"):
        tts = gTTS(text=text, lang=lang)
        mp3_path = f"{self.file_path.rsplit('.', 1)[0]}.mp3"
        tts.save(mp3_path)
        return mp3_path.rsplit('/', 1)[1]


def empty_folder(file_path):
    files = glob.glob(file_path)
    for f in files:
        os.remove(f)