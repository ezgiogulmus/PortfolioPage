from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By 
import datetime
import time
import pandas as pd 
import matplotlib.pyplot as plt
from fpdf import FPDF
import os
import requests
import boto3
import operator
import io


class Funds:
    def __init__(self, static_folder, bucket_name):
        self.fund_names = pd.read_csv(f"{static_folder}fundnames.csv")
        self.s3_client = boto3.client("s3")

    def get_fund_names(self):
        interest = list(zip(self.fund_names[self.fund_names['Interest (+/-)'] == 1]["Fund"], self.fund_names[self.fund_names['Interest (+/-)'] == 1]["Name"]))
        no_interest = list(zip(self.fund_names[self.fund_names['Interest (+/-)'] == 0]["Fund"], self.fund_names[self.fund_names['Interest (+/-)'] == 0]["Name"]))
        return [interest, no_interest]
    
    def changes(self, selection):
        change = [[] for s in range(len(selection))]
        bucket_content = self.s3_client.list_objects(Bucket=bucket_name)["Contents"]
        bes_files = [i["Key"] for i in bucket_content if "BES" in i["Key"]]
        bes_files.sort()
        dates = [file.split('_')[1].split('.')[0] for file in bes_files]

        for file in bes_files:
            bes_url = self.s3_client.generate_presigned_url('get_object',
                                            Params={'Bucket': bucket_name, 'Key': file},
                                            ExpiresIn=3600)
            data = requests.get(bes_url).content.decode("utf-8")
            new_data = dict(zip(data.split("{")[2].split('"')[3:-1:4], data.split("{")[4].split('"')[3:-1:4]))
            for s in range(len(selection)):
                change[s].append(new_data[selection[s]].replace(",", "."))

        sorted_funds = dict(sorted(new_data.items(), key=operator.itemgetter(1),reverse=True))
        return (change, dates, sorted_funds)
        
    def get_new_file(self):
        bes_url = "https://thefon.turkiyehayatemeklilik.com.tr/TurkiyeHayatEmeklilik/Fonlar/Getiri"

        opts = ChromeOptions()
        opts.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
        opts.add_argument("--headless")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        opts.add_experimental_option("detach", True)
        driver = Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=opts)
        driver.get(bes_url)

        time.sleep(3)
        faizsiz_table = driver.find_element(By.ID, 'GetiriTable').text

        name, interest, annually, monthly, weekly = [], [], [], [], []
        for i in faizsiz_table.split("\n")[1:]:
            content = i.split(" ")
            name.append(content[0])
            interest.append(0)
            annually.append(content[-1])
            monthly.append(content[-2])
            weekly.append(content[-3])
            
        faiz = driver.find_element(By.XPATH, "/html/body/article/div/div/div[2]/div[1]/div[1]/input")
        faiz.click()

        time.sleep(3)
        faizli_table = driver.find_element(By.ID, 'GetiriTable').text

        for i in faizli_table.split("\n")[1:]:
            content = i.split(" ")
            name.append(content[0])
            interest.append(1)
            annually.append(content[-1])
            monthly.append(content[-2])
            weekly.append(content[-3])

        new_file = pd.DataFrame({
            "Fund": name,
            "Interest (+/-)": interest,
            "Change % (since new year)": annually,
            "Change % (month)": monthly,
            "Change % (week)": weekly
        })
        new_file = new_file.set_index("Fund").join(self.fund_names.set_index("Fund"), lsuffix="1_", rsuffix="2_").reset_index()

        s3 = boto3.resource('s3')
        object = s3.Object(bucket_name, f'BES_{datetime.date.today()}.csv')
        object.put(Body=new_file.to_json().encode(), ACL="public-read")

    def output(self, selection):
        self.get_new_file()
        change, dates, sorted_funds = self.changes(selection)

        fig_selected = plt.figure(figsize=(14, 7))
        for i in range(len(selection)):
            plt.plot(dates, change[i], label=selection[i], linewidth=4)
        plt.legend(fontsize=16)
        plt.xticks(rotation=45, fontsize=16)
        plt.yticks(fontsize=16)
        plt.ylabel("YTD (%)", fontsize=20, labelpad=30)
        plt.title("Year to date change in your selected funds", fontsize=24, pad=50)

        
        fig_tops = plt.figure(figsize=(14, 7))
        for i in list(sorted_funds.items())[:10]:
            plt.bar(i[0], float(i[1].replace(",", ".")), label=i)
        for s in selection:
            plt.bar(s, sorted_funds[s], label=f"{s}**")
        lgd = plt.legend(fontsize=16, bbox_to_anchor=(1, 1), loc="upper left")
        plt.xticks(rotation=45, fontsize=16)
        plt.yticks(fontsize=16)
        plt.ylabel("YTD (%)", fontsize=20, labelpad=30)
        text = plt.title("Top performing and your selected funds(**)", fontsize=24, pad=50)

        # fig_selected.savefig(f"{self.main_folder}uploads/selected.png")
        # fig_tops.savefig(f"{self.main_folder}uploads/top.png")

        b1 = io.BytesIO()
        fig_selected.savefig(b1, format='png', bbox_inches='tight')
        self.s3_client.put_object(Body=b1.getvalue(), Bucket=bucket_name, Key="fig_selected.png", ACL="public-read")
        b2 = io.BytesIO()
        fig_tops.savefig(b2, format='png', bbox_extra_artists=(lgd,text), bbox_inches='tight')
        self.s3_client.put_object(Body=b2.getvalue(), Bucket=bucket_name, Key="fig_tops.png", ACL="public-read")

        sel_url = self.s3_client.generate_presigned_url('get_object',
                                            Params={'Bucket': bucket_name, 'Key': "fig_selected.png"},
                                            ExpiresIn=3600)
        top_url = self.s3_client.generate_presigned_url('get_object',
                                            Params={'Bucket': bucket_name, 'Key': "fig_tops.png"},
                                            ExpiresIn=3600)
        pdf = FPDF(unit="in", format="A4")
        pdf.set_font('Arial', 'B', 14)
        pdf.add_page()
        pdf.image(name="%scorner_left.png" %static_folder, w=.5, x=.1, y=.1)
        pdf.image(name="%scorner_right.png" %static_folder, w=.5, x=7.7, y=.1)
        pdf.add_font('Walkway', '', "%sWalkway.ttf" %static_folder, uni=True)
        pdf.set_font('Walkway', '', 40)
        pdf.cell(1.5)
        pdf.cell(w=0, h=.3, txt="Investment Update", ln=1)
        pdf.ln(h=.5)
        pdf.image(x=1, name=sel_url.split("?", 1)[0], w=6)
        pdf.ln(h=.5)
        pdf.image(x=1, name=top_url.split("?", 1)[0], w=7)
        pdf.set_font('Arial', size=8)
        pdf.set_y(-.8)
        pdf.cell(w=0, txt="The data is taken from Turkiye Sigorta and the report is created by Ezgi Ogulmus.", link="https://www.turkiyesigorta.com.tr", align="C")      
        content = io.BytesIO(bytes(pdf.output(dest = 'S'), encoding='latin1'))
        self.s3_client.put_object(Body=content.getvalue(), Bucket=bucket_name, Key="output.pdf", ACL="public-read")

        pdf_url = self.s3_client.generate_presigned_url('get_object',
                                            Params={'Bucket': bucket_name, 'Key': "output.pdf"},
                                            ExpiresIn=3600)
        return pdf_url

    def dene(self):
        sel_url = self.s3_client.generate_presigned_url('get_object',
                                        Params={'Bucket': bucket_name, 'Key': "fig_selected.png"},
                                        ExpiresIn=3600)
        top_url = self.s3_client.generate_presigned_url('get_object',
                                            Params={'Bucket': bucket_name, 'Key': "fig_tops.png"},
                                            ExpiresIn=3600)
        pdf = FPDF(unit="in", format="A4")
        pdf.set_font('Arial', 'B', 14)
        pdf.add_page()
        pdf.image(name="%scorner_left.png" %static_folder, w=.5, x=.1, y=.1)
        pdf.image(name="%scorner_right.png" %static_folder, w=.5, x=7.7, y=.1)
        pdf.add_font('Walkway', '', "%sWalkway.ttf" %static_folder, uni=True)
        pdf.set_font('Walkway', '', 40)
        pdf.cell(1.5)
        pdf.cell(w=0, h=.3, txt="Investment Update", ln=1)
        pdf.ln(h=.5)
        pdf.image(x=1, name=sel_url.split("?", 1)[0], w=6)
        pdf.ln(h=.5)
        pdf.image(x=1, name=top_url.split("?", 1)[0], w=7)
        pdf.set_font('Arial', size=8)
        pdf.set_y(-.8)
        pdf.cell(w=0, txt="The data is taken from Turkiye Sigorta and the report is created by Ezgi Ogulmus.", link="https://www.turkiyesigorta.com.tr", align="C")      
        content = io.BytesIO(bytes(pdf.output(dest = 'S'), encoding='latin1'))
        self.s3_client.put_object(Body=content.getvalue(), Bucket=bucket_name, Key="output.pdf", ACL="public-read")

        pdf_url = self.s3_client.generate_presigned_url('get_object',
                                            Params={'Bucket': bucket_name, 'Key': "output.pdf"},
                                            ExpiresIn=3600)
        return pdf_url