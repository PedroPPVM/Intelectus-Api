import os
import re
import requests
from bs4 import BeautifulSoup

BASE_URL = 'https://revistas.inpi.gov.br/rpi/'
SAVE_DIR = 'downloads'

os.makedirs(SAVE_DIR, exist_ok=True)

response = requests.get(BASE_URL)
soup = BeautifulSoup(response.content, 'html.parser')

row = soup.select('table tr')[1:2][0]

cells = row.find_all('a')

links = []
links.append(re.findall(r'"(.*?)"', str(cells[3]))[0])  # Desenhos industriais
links.append(re.findall(r'"(.*?)"', str(cells[5]))[0])  # Marcas
links.append(re.findall(r'"(.*?)"', str(cells[7]))[0])  # Patentes
links.append(re.findall(r'"(.*?)"', str(cells[9]))[0])  # Programa de Computador    

for link in links:
    file_name = os.path.join(SAVE_DIR, link.split('/')[-1])

    print(f"Baixando: {link}")
    file_response = requests.get(link)

    with open(file_name, 'wb') as f:
        f.write(file_response.content)
