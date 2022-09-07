from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequestKeyError
import os
import json
from flask import send_from_directory
from pdfconverter import ListenPDFs, empty_folder
from bes_report import Funds
import boto3

app = Flask(__name__)
S3_BUCKET = "ezgiyobucket"

MYDIR = os.path.dirname(__file__)
STATIC_FOLDER = 'static/'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("index.html")

#INVESTMENT
@app.route('/bes', methods=['GET', 'POST'])
def bes():
    empty_folder(f"{os.path.join(MYDIR, app.config['UPLOAD_FOLDER'])}/*")
    fund = Funds(os.path.join(MYDIR, STATIC_FOLDER))
    fund_names = fund.get_fund_names()
    selected_funds = []
    if request.method == "POST":
        for f in fund_names[0]:
            try:
                request.form[f[0]]
            except BadRequestKeyError:
                pass
            else:
                selected_funds.append(f[0])
        for f in fund_names[1]:
            try:
                request.form[f[0]]
            except BadRequestKeyError:
                pass
            else:
                selected_funds.append(f[0])
        filename = fund.output(selected_funds)
        redirect(request.url)
        return send_from_directory(os.path.join(MYDIR, app.config['UPLOAD_FOLDER']), filename, as_attachment=True)
    return render_template("bes.html", funds=fund_names)

# MORS
def translate(text):
    with open(f"{os.path.join(MYDIR, STATIC_FOLDER)}mors.json", "r") as file:
        alphabet = json.load(file)
    mors = []
    for letter in text:
        try:
            mors.append(alphabet[letter.lower()])
        except KeyError as message:
            return f"The character {message} is not accepted."
    return (' ').join(mors)

@app.route('/mors', methods=["GET", "POST"])
def mors():
    if request.method == "POST":
        mors = translate(request.form['message'])
        return render_template('mors.html', mors=mors)

    return render_template('mors.html')

# PDF CONVERTER
@app.route('/pdf', methods=['GET', 'POST'])
def pdf():
    if request.method == "POST":
        empty_folder(f"{os.path.join(MYDIR, app.config['UPLOAD_FOLDER'])}/*")
        if 'pdf-file' not in request.files:
            flash('No file part.')
            return redirect(request.url)
        pdf_file = request.files['pdf-file']
        filename = secure_filename(pdf_file.filename)
        if pdf_file.filename == '':
            flash('Select a file.')
            return redirect(request.url)
        if pdf_file.filename.rsplit('.', 1)[1].lower() != "pdf":
            flash('Only PDF files are accepted.')
            return redirect(request.url)
        else:
            if request.form['first-page'] == "":
                first_page = 1
            else:
                first_page = int(request.form['first-page'])
            if request.form['last-page'] == "":
                last_page = -1
            else:
                last_page = int(request.form['last-page'])
            if last_page > 0 and last_page < first_page:
                flash('Select at least 1 page.')
                return redirect(request.url)
            s3 = boto3.client(
                "s3")
            out = upload_file_to_s3(s3, pdf_file, filename, pdf_file.content_type)
            if out == False:
                flash("Unable to upload, try again")
                return redirect(request.url)
            else:
                pdf_url = s3.generate_presigned_url('get_object',
                                    Params={'Bucket': S3_BUCKET, 'Key': filename},
                                    ExpiresIn=3600)
                # print(pdf_url)
                converter = ListenPDFs(pdf_url, first_page, last_page)
                status = converter.save_mp3(f"{filename.rsplit('.', 1)[0]}.mp3")
                # upload_file_to_s3(s3, mp3_file, f"{filename.rsplit('.', 1)[0]}.mp3", "audio/mpeg")
                if status:
                    mp3_url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': S3_BUCKET, 'Key': f"{filename.rsplit('.', 1)[0]}.mp3"},
                                        ExpiresIn=3600)
                    return redirect(mp3_url)
    return render_template("pdf.html")
    

def upload_file_to_s3(s3, file, filename, content_type, acl="public-read"):
    try:
        s3.upload_fileobj(
            file,
            S3_BUCKET,
            filename,
            ExtraArgs={
                "ACL": acl
            }
        )
    except Exception as e:
        print("Something Happened: ", e)
        return False
    return True


if __name__ == "__main__":
    app.run(debug=True)
