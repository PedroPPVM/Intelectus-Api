import re
import logging
import requests
from typing import Optional, Dict
from bs4 import BeautifulSoup

from app.core.config import settings

# Logger para este módulo
logger = logging.getLogger('intelectus.inpi_pepi_service')

REQUEST_TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class InpiPepiService:
    """
    Service para consultar marcas no portal pePI do INPI.

    Realiza web scraping no portal https://busca.inpi.gov.br/pePI/
    para obter informações de marca e situação de processos.
    """

    def _create_session(self) -> requests.Session:
        """Cria uma requests.Session com headers de navegador."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pt-BR,pt;q=0.9",
        })
        return session

    def _login_anonymous(self, session: requests.Session) -> None:
        """
        POST para LoginController com acesso anônimo.
        Estabelece JSESSIONID necessário para as consultas.
        """
        login_url = f"{settings.pepi_base_url}/servlet/LoginController?action=login"
        logger.debug(f"Realizando login anônimo em: {login_url}")
        response = session.post(login_url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.debug(f"Login anônimo realizado. Cookies: {dict(session.cookies)}")

    def _search_marca(self, session: requests.Session, process_number: str) -> requests.Response:
        """Executa busca de marca por número de processo."""
        search_url = f"{settings.pepi_base_url}/servlet/MarcasServletController"
        params = {
            "Action": "searchMarca",
            "tipoPesquisa": "BY_NUM_PROC",
            "NumPedido": process_number,
        }
        logger.debug(f"Buscando marca com número: {process_number}")
        response = session.get(search_url, params=params, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def _parse_search_results(self, content: bytes, process_number: str) -> str:
        """
        Parseia a página de resultados para encontrar o CodPedido do processo.

        Retorna o CodPedido extraído do link de detalhe.
        Levanta ValueError se o processo não for encontrado.
        """
        soup = BeautifulSoup(content, "html.parser", from_encoding="iso-8859-1")

        # Buscar link de detalhe: <a href='...?Action=detail&CodPedido=XXXXX'>
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "Action=detail" in href and "CodPedido=" in href:
                match = re.search(r"CodPedido=(\d+)", href)
                if match:
                    cod_pedido = match.group(1)
                    logger.info(f"✅ Processo {process_number} encontrado (CodPedido={cod_pedido})")
                    return cod_pedido

        raise ValueError(f"Processo {process_number} não encontrado nos resultados do INPI")

    def _fetch_detail_page(self, session: requests.Session, cod_pedido: str) -> requests.Response:
        """Busca a página de detalhe do processo."""
        detail_url = f"{settings.pepi_base_url}/servlet/MarcasServletController"
        params = {
            "Action": "detail",
            "CodPedido": cod_pedido,
        }
        logger.debug(f"Acessando página de detalhe (CodPedido={cod_pedido})")
        response = session.get(detail_url, params=params, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def _parse_detail_page(self, content: bytes) -> Dict[str, Optional[str]]:
        """
        Extrai 'Marca' e 'Situação' da página de detalhe do processo.

        A página usa tabelas com <td> contendo labels (ex: "Marca:")
        seguidos de <td> com os valores correspondentes.
        """
        soup = BeautifulSoup(content, "html.parser", from_encoding="iso-8859-1")

        marca = None
        situacao = None

        # Buscar todos os <td> que contêm labels
        for td in soup.find_all("td"):
            text = td.get_text(strip=True)

            if text == "Marca:":
                # Próximo <td> irmão contém o valor
                next_td = td.find_next_sibling("td")
                if next_td:
                    marca = next_td.get_text(strip=True)

            elif "Situa" in text and text.endswith(":"):
                # "Situação:" - pode ter encoding diferente
                next_td = td.find_next_sibling("td")
                if next_td:
                    situacao = next_td.get_text(strip=True)

        logger.debug(f"Dados extraídos - Marca: {marca}, Situação: {situacao}")
        return {"marca": marca, "situacao": situacao}

    def lookup_marca(self, process_number: str) -> Dict[str, Optional[str]]:
        """
        Consulta completa de marca no portal pePI do INPI.

        Fluxo:
        1. Login anônimo (JSESSIONID)
        2. Busca por número de processo
        3. Acessa página de detalhe
        4. Extrai Marca e Situação

        Args:
            process_number: Número do processo (ex: "942926668")

        Returns:
            Dict com process_number, marca e situacao

        Raises:
            ValueError: Processo não encontrado
            requests.ConnectionError: INPI indisponível
            requests.Timeout: Timeout na conexão
        """
        logger.info(f"🔍 Consultando marca no INPI pePI: {process_number}")

        session = self._create_session()

        # 1. Login anônimo
        self._login_anonymous(session)

        # 2. Busca por número de processo
        search_response = self._search_marca(session, process_number)

        # 3. Extrair CodPedido dos resultados
        cod_pedido = self._parse_search_results(search_response.content, process_number)

        # 4. Acessar página de detalhe
        detail_response = self._fetch_detail_page(session, cod_pedido)

        # 5. Extrair dados
        data = self._parse_detail_page(detail_response.content)
        data["process_number"] = process_number

        logger.info(f"✅ Consulta concluída para processo {process_number}: Marca={data.get('marca')}, Situação={data.get('situacao')}")
        return data


# Instância singleton
inpi_pepi_service = InpiPepiService()
