import pandas as pd
import time


file_path = "C:/Users/Oleg/PycharmProjects/data_analytic/parsing/gas_stoves.xlsx"
data = pd.read_excel(file_path)
print(data)
df = data.copy()
print(df.info())