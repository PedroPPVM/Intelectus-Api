import os
import requests
from app.services import pdf_reader
from app.models.process import ProcessType
from app.crud import process as crud_process
from app.schemas.process import ProcessUpdate

DOWNLOAD_DIR = 'downloads'
BASE_URL = 'https://revistas.inpi.gov.br/rpi/'

class ScrapingService:
    """
    Service para buscar e atualizar processos a partir da revista RPI mais recente.
    """
    def __init__(self):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    def _get_latest_links(self):
        """Busca os links dos PDFs mais recentes para cada tipo de processo."""
        from bs4 import BeautifulSoup
        response = requests.get(BASE_URL)
        soup = BeautifulSoup(response.content, 'html.parser')
        row = soup.select('table tr')[1:2][0]
        cells = row.find_all('a')
        links = {
            ProcessType.DESIGN: self._extract_link(cells[3]),
            ProcessType.BRAND: self._extract_link(cells[5]),
            ProcessType.PATENT: self._extract_link(cells[7]),
            ProcessType.SOFTWARE: self._extract_link(cells[9]),
        }
        return links

    def _extract_link(self, cell):
        import re
        return re.findall(r'"(.*?)"', str(cell))[0]

    def _download_pdf(self, url):
        file_name = os.path.join(DOWNLOAD_DIR, url.split('/')[-1])
        print(f"[DEBUG] Baixando PDF de: {url}")
        response = requests.get(url)
        with open(file_name, 'wb') as f:
            f.write(response.content)
        print(f"[DEBUG] PDF salvo em: {file_name}")
        return file_name

    def _remove_pdf(self, file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    def scrape_and_update_process(self, db, process_number, process_type, company_id):
        """
        Busca o processo na revista RPI mais recente, atualiza o banco se necessário e retorna resposta padronizada.
        """
        links = self._get_latest_links()
        pdf_url = links.get(process_type)
        print(f"[DEBUG] Link do PDF selecionado: {pdf_url}")
        if not pdf_url:
            return {"response": "Tipo de processo não suportado.", "status": None}
        pdf_path = self._download_pdf(pdf_url)
        print(f"[DEBUG] Buscando processo: {process_number}")
        try:
            # Chama o leitor de PDF correto
            if process_type == ProcessType.BRAND:
                data = pdf_reader.search_status_marcas(process_number, pdf_path)
            elif process_type == ProcessType.PATENT:
                data = pdf_reader.search_status_patentes(process_number, pdf_path)
            elif process_type == ProcessType.DESIGN:
                data = pdf_reader.search_status_desenhos_industriais(process_number, pdf_path)
            elif process_type == ProcessType.SOFTWARE:
                data = pdf_reader.search_status_programa_de_computador(process_number, pdf_path)
            else:
                data = None
            print(f"[DEBUG] Resultado do pdf_reader: {data}")
            if not data:
                return {"response": "Processo não encontrado na revista.", "status": None}
            # Buscar processo no banco
            proc = crud_process.get_by_company_and_number(db, company_id=company_id, process_number=process_number)
            if not proc:
                return {"response": "Processo não cadastrado no sistema.", "status": None}
            # Atualizar status se necessário
            status_atual = proc.status
            status_novo = data.get('status')
            if status_novo and status_novo != status_atual:
                # Atualiza apenas o status (pode expandir para outros campos)
                crud_process.update(db, db_obj=proc, obj_in=ProcessUpdate(status=status_novo))
                return {"response": "Processo atualizado!", "status": status_novo}
            else:
                return {"response": "Nenhuma atualização necessária.", "status": status_atual}
        finally:
            self._remove_pdf(pdf_path)

scraping_service = ScrapingService()
