
import pandas as pd
import os
import requests
import zipfile
from datetime import date, timedelta
from multiprocessing import Pool


#import idx list
idx1 = pd.read_csv('ncsrs_list.csv')
idx1


#Set up which year to download
YY = 2017

#Initiate date_list
def get_quarter(date_str):
  """
  Returns the quarter for a given date string in YYYYMMDD format.
  """
  year = int(date_str[:4])
  month = int(date_str[4:6])
  if 1 <= month <= 3:
    return '1'
  elif 4 <= month <= 6:
    return '2'
  elif 7 <= month <= 9:
    return '3'
  else:
    return '4'

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

start_date = date(YY, 1, 1)
end_date = date(YY, 12, 31)
date_list = []

for dt in daterange(start_date, end_date):
    date_list.append(dt.strftime("%Y%m%d"))


#download EDGAR traffic log files

unable_request = 0


for day in date_list:
  os.chdir("/content/drive/My Drive/paper3/data/log_file")

  # Define the URL and user agent
  quarter = get_quarter(day)
  url = "http://www.sec.gov/dera/data/Public-EDGAR-log-file-data/{}/Qtr{}/log{}.zip".format(YY, quarter, day)
  headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'} # Update User-Agent to mimic Safari on Mac

  # Download the file
  response = requests.get(url, headers=headers)

  # Check if the request was successful
  if response.status_code == 200:
    # Save the file to disk
    with open("log{}.zip".format(day), "wb") as f:
        f.write(response.content)

    # Unzip the file
    with zipfile.ZipFile("log{}.zip".format(day), "r") as zip_ref:
        zip_ref.extractall(".")

    # Get the first file in the extracted directory
    files = os.listdir(".")

    for file in files:
      if file.endswith(".zip") or file.endswith(".txt"):
        open(file, 'w').close()
        os.remove(file)

    # Open the first file as a CSV
    edgar = pd.read_csv("log{}.csv".format(day), engine="pyarrow", usecols=['ip','date','cik','accession','extention','code','size','idx','noagent','crawler'])

    edgar = edgar[(edgar['code'] == 200) & (edgar['idx'] == 0) & (edgar['crawler'] == 0)]
    edgar.drop(columns=['code','idx','crawler'], inplace=True)

    edgar = edgar[edgar['extention'].str[-3:].isin(['htm', 'txt'])]
    edgar['extention'] = edgar['extention'].str[-3:]
    edgar.reset_index(drop=True, inplace=True)

    # Select N-CSR, N-CSRS requests according to file identifier "accession"
    df = pd.merge(idx1, edgar, left_on='file', right_on='accession', how='left')
    df.dropna(subset=['ip'],inplace=True)
    df.reset_index(drop=True, inplace=True)

    #Delete daily traffic log, clean up space
    open("log{}.csv".format(day), 'w').close()
    os.remove("log{}.csv".format(day))

    os.chdir("/content/drive/My Drive/paper3/data/clean_file/{}".format(YY))
    df.to_csv('edgar{}.csv'.format(day), index=False)

  else:
    unable_request += 1

    print(f"Failed to download file: {day}",)


  print(f"Total failed count: {unable_request}")


# check how many files in clean_file folder

directory = "/content/drive/My Drive/paper3/data/clean_file/{}".format(YY)
files = os.listdir(directory)
num_files = len(files)

print(f"There are {num_files} files in the year {YY}.")


# check clean_file folder size

!du -sh "/content/drive/My Drive/paper3/data/clean_file"



