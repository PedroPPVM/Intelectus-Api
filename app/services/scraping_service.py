import os
import requests
import re
import hashlib
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.services import pdf_reader
from app.models.process import ProcessType
from app.crud import process as crud_process
from app.crud.crud_rpi_magazine import rpi_magazine as crud_rpi_magazine
from app.schemas.process import ProcessUpdate
from bs4 import BeautifulSoup

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
        return re.findall(r'"(.*?)"', str(cell))[0]
    
    def _extract_magazine_identifier(self, url: str) -> str:
        """
        Extrair identificador único da revista da URL ou nome do arquivo.
        
        Tenta extrair do nome do arquivo (ex: rpi_2024_001.pdf -> 2024_001)
        Se não conseguir, usa hash da URL como fallback.
        """
        # Extrair nome do arquivo da URL
        file_name = url.split('/')[-1]
        
        # Tentar extrair padrão do nome (ex: rpi_2024_001.pdf)
        match = re.search(r'rpi[_\s]*(\d{4}[_\s]*\d{3})', file_name, re.IGNORECASE)
        if match:
            # Normalizar: remover espaços e underscores
            identifier = match.group(1).replace('_', '').replace(' ', '')
            return identifier
        
        # Fallback: usar hash da URL (primeiros 16 caracteres)
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        return f"hash_{url_hash}"
    
    def _extract_publication_date(self, soup: BeautifulSoup, process_type: ProcessType) -> Optional[datetime]:
        """
        Extrair data de publicação da revista do HTML.
        
        Tenta extrair da tabela HTML. Se não disponível, retorna None.
        """
        try:
            # A primeira linha da tabela geralmente contém a data
            row = soup.select('table tr')[1:2][0]
            # Tentar extrair data de células da tabela
            cells = row.find_all(['td', 'th'])
            for cell in cells:
                text = cell.get_text(strip=True)
                # Procurar padrões de data (DD/MM/YYYY ou YYYY-MM-DD)
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})|(\d{4}-\d{2}-\d{2})', text)
                if date_match:
                    date_str = date_match.group(0)
                    try:
                        if '/' in date_str:
                            return datetime.strptime(date_str, '%d/%m/%Y')
                        else:
                            return datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        continue
        except Exception:
            pass
        
        return None
    
    def get_or_create_magazine(
        self,
        db: Session,
        process_type: ProcessType,
        url: str,
        soup: Optional[BeautifulSoup] = None
    ):
        """
        Buscar ou criar registro de revista no banco.
        
        Args:
            db: Sessão do banco
            process_type: Tipo de processo
            url: URL da revista
            soup: BeautifulSoup do HTML (opcional, para extrair data de publicação)
            
        Returns:
            tuple: (revista, criada) - onde criada é True se foi criada agora
        """
        # Extrair identificador da revista
        magazine_identifier = self._extract_magazine_identifier(url)
        
        # Extrair data de publicação se soup fornecido
        publication_date = None
        if soup:
            pub_date = self._extract_publication_date(soup, process_type)
            if pub_date:
                publication_date = pub_date.date()
        
        # Buscar ou criar revista
        magazine, created = crud_rpi_magazine.get_or_create(
            db,
            process_type=process_type,
            magazine_identifier=magazine_identifier,
            url=url,
            publication_date=publication_date,
            last_checked_at=datetime.now(timezone.utc)
        )
        
        return magazine, created

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
        
        Agora também cria/atualiza registro de revista e associa ao processo.
        """
        # Buscar links das últimas revistas disponíveis
        links = self._get_latest_links()
        pdf_url = links.get(process_type)
        print(f"[DEBUG] Link do PDF selecionado: {pdf_url}")
        if not pdf_url:
            return {"response": "Tipo de processo não suportado.", "status": None}
        
        # Extrair identificador da última revista
        latest_identifier = self._extract_magazine_identifier(pdf_url)
        
        # Verificar se já temos essa revista no banco
        existing_magazine = crud_rpi_magazine.get_by_type_and_identifier(
            db, process_type, latest_identifier
        )
        
        # Buscar processo no banco primeiro para verificar otimização
        proc = crud_process.get_by_company_and_number(db, company_id=company_id, process_number=process_number)
        if not proc:
            return {"response": "Processo não cadastrado no sistema.", "status": None}
        
        # OTIMIZAÇÃO: Se a revista já foi processada e o processo já está associado a ela,
        # verificar se o status ainda está atualizado (pode ter mudado mesmo com a mesma revista)
        if existing_magazine and existing_magazine.processed_at is not None:
            if proc.magazine_id == existing_magazine.id:
                # Processo já está associado à última revista processada
                # Retornar status atual sem processar novamente
                return {
                    "response": "Processo já está atualizado com a última revista disponível.",
                    "status": proc.status,
                    "magazine_identifier": existing_magazine.magazine_identifier,
                    "skipped": True
                }
        
        # Buscar soup para extrair data de publicação (se necessário)
        response = requests.get(BASE_URL)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscar ou criar registro de revista
        magazine, magazine_created = self.get_or_create_magazine(
            db, process_type, pdf_url, soup
        )
        
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
            # Atualizar status e revista se necessário
            status_atual = proc.status
            status_novo = data.get('status')
            update_data = {}
            
            if status_novo and status_novo != status_atual:
                update_data['status'] = status_novo
            
            # Sempre atualizar magazine_id para rastrear qual revista foi usada
            if proc.magazine_id != magazine.id:
                update_data['magazine_id'] = magazine.id
            
            if update_data:
                crud_process.update(db, db_obj=proc, obj_in=ProcessUpdate(**update_data))
                # Atualizar processed_at da revista
                from app.schemas.rpi_magazine import RPIMagazineUpdate
                crud_rpi_magazine.update(
                    db,
                    db_obj=magazine,
                    obj_in=RPIMagazineUpdate(processed_at=datetime.now(timezone.utc))
                )
                return {"response": "Processo atualizado!", "status": status_novo if status_novo else status_atual}
            else:
                return {"response": "Nenhuma atualização necessária.", "status": status_atual}
        finally:
            self._remove_pdf(pdf_path)

scraping_service = ScrapingService()
