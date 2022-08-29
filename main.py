from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequestKeyError
import os
import json
import pandas as pd
from flask import send_from_directory
from pdfconverter import ListenPDFs, empty_folder
from bes_report import Funds


app = Flask(__name__)
UPLOAD_FOLDER = './static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 

main_folder = app.config['UPLOAD_FOLDER'].split('uploads')[0]

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("index.html")

#INVESTMENT
@app.route('/bes', methods=['GET', 'POST'])
def bes():
    empty_folder(f"{app.config['UPLOAD_FOLDER']}/*")
    fund = Funds(main_folder)
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
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    return render_template("bes.html", funds=fund_names)

# MORS
def translate(text):
    with open(f"{main_folder}mors.json", "r") as file:
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
        empty_folder(f"{app.config['UPLOAD_FOLDER']}/*")
        if 'pdf-file' not in request.files:
            flash('No file part.')
            return redirect(request.url)
        pdf_file = request.files['pdf-file']
        if pdf_file.filename == '':
            flash('Select a file.')
            return redirect(request.url)
        if pdf_file.filename.rsplit('.', 1)[1].lower() != "pdf":
            flash('Only PDF files are accepted.')
            return redirect(request.url)
        else:
            filename = secure_filename(pdf_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(file_path)
            if request.form['first-page'] == "":
                first_page = 1
            if request.form['last-page'] == "":
                last_page = -1
            if int(request.form['last-page']) > 0 and int(request.form['last-page']) < int(request.form['first-page']):
                flash('Select at least 1 page.')
                return redirect(request.url)
            else:
                first_page = int(request.form['first-page'])
                last_page = int(request.form['last-page'])
            converter = ListenPDFs(file_path, first_page, last_page)
            text_file = converter.get_text()
            text_path = os.path.join(app.config['UPLOAD_FOLDER'], text_file)
            with open(text_path, "r") as file:
                text = file.read()
            if request.form['type'] == 'mp3':
                mp3 = converter.save_mp3(text)
                return send_from_directory(app.config['UPLOAD_FOLDER'], mp3, as_attachment=True)
            else:
                return send_from_directory(app.config['UPLOAD_FOLDER'], text_file, as_attachment=True)
    return render_template("pdf.html")
    


if __name__ == "__main__":
    app.run(debug=True)
