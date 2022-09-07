from cgitb import text
from fileinput import filename
from PyPDF2 import PdfReader, PdfFileReader
from gtts import gTTS
import glob
import os
import requests
from io import BytesIO
import boto3

class ListenPDFs:
    def __init__(self, file_path, first_page=1, last_page=-1, language="en"):
        """
        file_path: path to PDF file
        page_number: starting page, default is 1 to start from the beginning
        """
        self.file_path = file_path        
        self.raw_data = requests.get(file_path).content
        self.data =  BytesIO(self.raw_data)  
        self.reader = PdfReader(self.data)
    
        if last_page == -1:
            self.last_page = len(self.reader.pages)
        else:
            self.last_page = last_page
        self.current_page = first_page-1
        self.lang = language
    
    def get_text(self):
        text_data = []
        while self.current_page < self.last_page:
            text_data.append(self.reader.pages[self.current_page].extract_text())
            self.current_page += 1
        return (' ').join(text_data)

    # def save_mp3(self, lang="en"):
    #     mp3_file = BytesIO()
    #     tts = gTTS(text=self.get_text(), lang=lang)
    #     tts.write_to_fp(mp3_file)
    #     return mp3_file
    def save_mp3(self, file_name, lang="en"):
        tts = gTTS(text=self.get_text(), lang=lang)
        tts.save(file_name)
        s3 = boto3.client('s3')
        with open(file_name, "rb") as file:
            s3.upload_fileobj(file, S3_BUCKET, file_name, ExtraArgs={
                "ACL": "public-read"
            })
        return True

def empty_folder(file_path):
    files = glob.glob(file_path)
    for f in files:
        os.remove(f)

# import boto3
# from werkzeug.utils import secure_filename
S3_BUCKET = "ezgiyobucket"


# def upload_file_to_s3(file, acl="public-read"):
#     s3 = boto3.client("s3")
#     filename = "mp3_file.mp3"
#     try:
#         s3.upload_fileobj(
#             file,
#             S3_BUCKET,
#             filename,
#             ExtraArgs={
#                 "ACL": acl,
#                 "ContentType": "audio/mpeg"
#             }
#         )
#     except Exception as e:
#         print("Something Happened: ", e)
#         return False
#     return True

# s3 = boto3.client("s3")
# filepath = s3.generate_presigned_url('get_object',
#                                      Params={'Bucket': S3_BUCKET, 'Key': "endpoint_acrejection.pdf"},
#                                      ExpiresIn=3600)
# print(filepath)
# converter = ListenPDFs(filepath, 1, 1)
# print(converter.save_mp3())