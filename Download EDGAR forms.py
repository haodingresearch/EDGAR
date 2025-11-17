
# # **Download and clean N-CSR files**


import pandas as pd
import os
import requests
import re
from bs4 import BeautifulSoup
import lxml
import string
from nltk.tokenize import word_tokenize
import pickle



from google.colab import drive
drive.mount('/content/drive')



os.chdir("/content/drive/My Drive/shareholder letter/company_idx")
idx_all = sorted(os.listdir())
len(idx_all)/4


for year in range(2023,2024):
    idx_list = idx_all[(year-1994)*4:(year-1993)*4]

    print(idx_list)

    idx = []
    index_file = []
    sum_idx = 0

    for idx in idx_list:
        idx_file = open("/content/drive/My Drive/shareholder letter/company_idx/{}".format(idx),encoding='ISO-8859-1').readlines()
        idx_file1 = idx_file[idx_file.index('---------------------------------------------------------------------------------------------------------------------------------------------\n')+1:]
        idx_length = len(idx_file1)

        index_file.extend(idx_file1)
        sum_idx += idx_length


    find_list = []
    item = 0
    line = 0
    n = 0

    while n in range(0,len(index_file)):
        i = index_file[line]
        loc1 = i.find('N-CSR')
        loc2 = i.find("N-CSRS")

        if (loc2 == -1) and (loc1 != -1):
            find_list.append(i)
        line+=1
        item = len(find_list)
        n += 1

    ReportList = []
    Company_No = []
    i = 0
    for i in find_list:
        split_i = i.split()
        ReportList.append("https://www.sec.gov/Archives/" + split_i[-1])
        Company_No.append(split_i[-3] + "_" + split_i[-2])

    os.chdir("/content/drive/My Drive/shareholder letter/fillings/{}".format(str(year)))

    def createfile(filename, content):
        name= filename + ".txt"  # name of the file
        with open(name, "w") as file:
            file.write(str(content)) #the textual content from the 10-K
            file.close()


    company_order = 0
    unable_request = 0
    a_index = 0

    for a_index in range(len(find_list)):
        web_add = ReportList[a_index]
        filename = Company_No[a_index]

        webpage_response = requests.get(web_add, headers={'User-Agent': 'Mozilla/5.0'})
        # It is very important to use the header, otherwise the SEC will block the requests after the first 5.

        if webpage_response.status_code == 200:
            # The HTTP 200 OK success status response code indicates that the request has succeeded.
            body = webpage_response.content
            createfile(filename, body)
        else:
            print ("Unable to get response with Code : %d " % (webpage_response.status_code))
            unable_request += 1

        a_index +=1

        print(f"{a_index/len(find_list):.2%}", filename)

    print("unable request: ", unable_request)
    print("total downloaded in year:", year, " is ", a_index)

