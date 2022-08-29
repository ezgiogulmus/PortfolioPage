from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By 
import datetime
import time
import pandas as pd 
import matplotlib.pyplot as plt
from fpdf import FPDF
import os


class Funds:
    def __init__(self, main_folder, save=False):
        self.main_folder = main_folder
        self.fund_names = pd.read_csv(f"{self.main_folder}fundnames.csv")
        self.save_csv = save

    def get_fund_names(self):
        interest = list(zip(self.fund_names[self.fund_names['Interest (+/-)'] == 1]["Fund"], self.fund_names[self.fund_names['Interest (+/-)'] == 1]["Name"]))
        no_interest = list(zip(self.fund_names[self.fund_names['Interest (+/-)'] == 0]["Fund"], self.fund_names[self.fund_names['Interest (+/-)'] == 0]["Name"]))
        return [interest, no_interest]
    
    def changes(self, selection):
        change = [[] for s in range(len(selection))]
        date = []
        file_list = os.listdir(f"{self.main_folder}BES/")
        file_list.sort()
        for file in file_list:
            df = pd.read_csv(f"{self.main_folder}BES/{file}", index_col=0).loc[selection]["Change % (since new year)"]
            date.append(file.split('_')[1].split('.')[0])
            for s in range(len(selection)):
                change[s].append(float(df.values[s].replace(",", ".")))

        if (datetime.datetime.strptime(max(date), "%Y-%m-%d")-datetime.datetime.today()).days > 14:
            self.save_csv = True
        else:
            self.save_csv = False
        return (change, date)
        
    def get_new_file(self):
        bes_url = "https://thefon.turkiyehayatemeklilik.com.tr/TurkiyeHayatEmeklilik/Fonlar/Getiri"

        chromeDriverPath = f'{self.main_folder}chromedriver'
        opts = Options()
        opts.add_experimental_option("detach", True)
        opts.add_argument('headless')
        driver = Chrome(chromeDriverPath, options=opts)
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
        new_file = new_file.set_index("Fund").join(self.fund_names.set_index("Fund"), lsuffix="1_", rsuffix="2_")
        if self.save_csv == True:
            new_file.to_csv(f"{self.main_folder}BES/BES_{datetime.date.today()}.csv", index=False)
        
        return new_file

    def output(self, selection):
        
        change, dates = self.changes(selection)
        new_file = self.get_new_file()

        new_numbers = [float(i.replace(",", ".")) for i in new_file.loc[selection]["Change % (since new year)"]]

        fig_selected = plt.figure(figsize=(14, 7))
        dates.append(str(datetime.date.today()))
        for i in range(len(selection)):
            change[i].append(new_numbers[i])
            plt.plot(dates, change[i], label=selection[i], linewidth=4)
        plt.legend(fontsize=16)
        plt.xticks(rotation=45, fontsize=16)
        plt.yticks(fontsize=16)
        plt.ylabel("YTD (%)", fontsize=20, labelpad=30)
        plt.title("Year to date change in your selected funds", fontsize=24, pad=50)

        tops = new_file.sort_values(["Change % (since new year)"], ascending=False)[:10]
        fig_tops = plt.figure(figsize=(14, 7))
        for i in tops.index:
            annual_chn = tops["Change % (since new year)"].loc[i]
            plt.bar(i, float(annual_chn.replace(",", ".")), label=i)
        for i in range(len(selection)):
            plt.bar(selection[i], new_numbers[i], label=f"{selection[i]}**")
        lgd = plt.legend(fontsize=16, bbox_to_anchor=(1, 1), loc="upper left")
        plt.xticks(rotation=45, fontsize=16)
        plt.yticks(fontsize=16)
        plt.ylabel("YTD (%)", fontsize=20, labelpad=30)
        text = plt.title("Top performing and your selected funds(**)", fontsize=24, pad=50)

        fig_selected.savefig(f"{self.main_folder}uploads/selected.png", bbox_inches='tight')
        fig_tops.savefig(f"{self.main_folder}uploads/top.png", bbox_extra_artists=(lgd,text), bbox_inches='tight')

        pdf = FPDF(unit="in", format="A4")
        pdf.set_font('Arial', 'B', 14)
        pdf.add_page()
        pdf.image(name="%scorner_left.png" %self.main_folder, w=.5, x=.1, y=.1)
        pdf.image(name="%scorner_right.png" %self.main_folder, w=.5, x=7.7, y=.1)
        pdf.add_font('Walkway', '', "%sWalkway.ttf" %self.main_folder, uni=True)
        pdf.set_font('Walkway', '', 40)
        pdf.cell(1.5)
        pdf.cell(w=0, h=.3, txt="Investment Update", ln=1)
        pdf.ln(h=.5)
        pdf.image(x=1, name="%suploads/selected.png" %self.main_folder, w=6)
        pdf.ln(h=.5)
        pdf.image(x=1, name="%suploads/top.png" %self.main_folder, w=7)
        pdf.set_font('Arial', size=8)
        pdf.set_y(-.8)
        pdf.cell(w=0, txt="The data is taken from Turkiye Sigorta and the report is created by Ezgi Ogulmus.", link="https://www.turkiyesigorta.com.tr", align="C")      
        pdf.output(f"{self.main_folder}uploads/InvUpdate{datetime.date.today()}.pdf")

        return f"InvUpdate{datetime.date.today()}.pdf"