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

    # ====================== PATENTES ======================

    def _load_patente_search_page(self, session: requests.Session) -> None:
        """
        Carrega a página de busca de patentes (PatenteSearchBasico.jsp).

        O portal pePI exige que o usuário passe pela página do formulário
        antes de submeter a busca, caso contrário a sessão é redirecionada
        de volta para o login.
        """
        search_page_url = f"{settings.pepi_base_url}/jsp/patentes/PatenteSearchBasico.jsp"
        logger.debug(f"Carregando página de busca de patentes: {search_page_url}")
        response = session.get(search_page_url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

    def _search_patente(self, session: requests.Session, process_number: str) -> requests.Response:
        """
        Executa busca de patente por número de pedido (POST no form).

        O formulário da página Basica usa Action=SearchBasico e espera o
        número em NumPedido (formato com espaços, ex: "BR 10 2023 002986").
        """
        search_url = f"{settings.pepi_base_url}/servlet/PatenteServletController"
        form_data = {
            "NumPedido": process_number,
            "NumGru": "",
            "NumProtocolo": "",
            "FormaPesquisa": "Todas",
            "ExpressaoPesquisa": "",
            "Coluna": "Titulo",
            "RegisterPerPage": "20",
            "Action": "SearchBasico",
        }
        logger.debug(f"Buscando patente com número: {process_number}")
        response = session.post(search_url, data=form_data, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def _parse_patente_search_results(self, content: bytes, process_number: str) -> str:
        """
        Encontra o CodPedido do processo na tabela de resultados.

        A coluna "Pedido" possui um link do tipo:
            <a href='...?Action=detail&CodPedido=1693529&...'>BR 10 2023 002986 8</a>
        """
        soup = BeautifulSoup(content, "html.parser", from_encoding="iso-8859-1")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "Action=detail" in href and "CodPedido=" in href:
                match = re.search(r"CodPedido=(\d+)", href)
                if match:
                    cod_pedido = match.group(1)
                    logger.info(f"✅ Patente {process_number} encontrada (CodPedido={cod_pedido})")
                    return cod_pedido

        raise ValueError(f"Patente {process_number} não encontrada nos resultados do INPI")

    def _fetch_patente_detail_page(self, session: requests.Session, cod_pedido: str) -> requests.Response:
        """Busca a página de detalhe da patente."""
        detail_url = f"{settings.pepi_base_url}/servlet/PatenteServletController"
        params = {
            "Action": "detail",
            "CodPedido": cod_pedido,
        }
        logger.debug(f"Acessando detalhe da patente (CodPedido={cod_pedido})")
        response = session.get(detail_url, params=params, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def _parse_patente_detail_page(self, content: bytes) -> Dict[str, Optional[str]]:
        """
        Extrai o 'Título' da página de detalhe da patente.

        O label aparece no padrão WIPO como "(54)Título:" em um <td>,
        com o valor no <td> irmão seguinte.
        """
        soup = BeautifulSoup(content, "html.parser", from_encoding="iso-8859-1")

        title = None

        for td in soup.find_all("td"):
            text = td.get_text(strip=True)
            # Label pode vir como "Título:" ou "(54)Título:"; aceita variantes de encoding.
            if "tulo" in text.lower() and text.endswith(":"):
                next_td = td.find_next_sibling("td")
                if next_td:
                    title = next_td.get_text(strip=True)
                    break

        logger.debug(f"Dados extraídos - Título: {title}")
        return {"title": title}

    def lookup_patente(self, process_number: str) -> Dict[str, Optional[str]]:
        """
        Consulta completa de patente no portal pePI do INPI.

        Fluxo:
        1. Login anônimo (JSESSIONID)
        2. Carrega página de busca de patentes
        3. POST do formulário de busca por número de pedido
        4. Extrai CodPedido do link na coluna "Pedido"
        5. Acessa página de detalhe
        6. Extrai o Título

        Args:
            process_number: Número do pedido (ex: "BR 10 2023 002986")

        Returns:
            Dict com process_number e title

        Raises:
            ValueError: Patente não encontrada
            requests.ConnectionError: INPI indisponível
            requests.Timeout: Timeout na conexão
        """
        logger.info(f"🔍 Consultando patente no INPI pePI: {process_number}")

        session = self._create_session()

        self._login_anonymous(session)
        self._load_patente_search_page(session)

        search_response = self._search_patente(session, process_number)
        cod_pedido = self._parse_patente_search_results(search_response.content, process_number)

        detail_response = self._fetch_patente_detail_page(session, cod_pedido)
        data = self._parse_patente_detail_page(detail_response.content)
        data["process_number"] = process_number

        logger.info(f"✅ Consulta concluída para patente {process_number}: Título={data.get('title')}")
        return data

    # ============== PROGRAMA DE COMPUTADOR ==============

    def _load_programa_search_page(self, session: requests.Session) -> None:
        """
        Carrega a página de busca de programa de computador (ProgramaSearchBasico.jsp).

        Igual ao fluxo de patente, o portal exige visita ao formulário
        antes de submeter a busca, sob pena de redirecionar ao login.
        """
        search_page_url = f"{settings.pepi_base_url}/jsp/programas/ProgramaSearchBasico.jsp"
        logger.debug(f"Carregando página de busca de programa: {search_page_url}")
        response = session.get(search_page_url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

    def _search_programa(self, session: requests.Session, process_number: str) -> requests.Response:
        """
        Executa busca de programa de computador por número de pedido (POST no form).

        O formulário usa Action=SearchBasico e espera o número no formato
        com espaços e hífen (ex: "BR 51 2026 002418-8").
        """
        search_url = f"{settings.pepi_base_url}/servlet/ProgramaServletController"
        form_data = {
            "NumPedido": process_number,
            "FormaPesquisa": "Todas",
            "ExpressaoPesquisa": "",
            "Coluna": "Titulo",
            "RegisterPerPage": "20",
            "Action": "SearchBasico",
        }
        logger.debug(f"Buscando programa com número: {process_number}")
        response = session.post(search_url, data=form_data, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def _parse_programa_search_results(self, content: bytes, process_number: str) -> str:
        """
        Encontra o CodPedido do programa na tabela de resultados.

        A coluna "Pedido" possui um link do tipo:
            <a href='...?Action=detail&CodPedido=57162&...'>BR 51 2026 002418 8</a>
        """
        soup = BeautifulSoup(content, "html.parser", from_encoding="iso-8859-1")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "Action=detail" in href and "CodPedido=" in href:
                match = re.search(r"CodPedido=(\d+)", href)
                if match:
                    cod_pedido = match.group(1)
                    logger.info(f"✅ Programa {process_number} encontrado (CodPedido={cod_pedido})")
                    return cod_pedido

        raise ValueError(f"Programa {process_number} não encontrado nos resultados do INPI")

    def _fetch_programa_detail_page(self, session: requests.Session, cod_pedido: str) -> requests.Response:
        """Busca a página de detalhe do programa de computador."""
        detail_url = f"{settings.pepi_base_url}/servlet/ProgramaServletController"
        params = {
            "Action": "detail",
            "CodPedido": cod_pedido,
        }
        logger.debug(f"Acessando detalhe do programa (CodPedido={cod_pedido})")
        response = session.get(detail_url, params=params, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def _parse_programa_detail_page(self, content: bytes) -> Dict[str, Optional[str]]:
        """
        Extrai o 'Título' da página de detalhe do programa de computador.

        O label aparece como "Título:" em um <td>, com o valor no <td>
        irmão seguinte.
        """
        soup = BeautifulSoup(content, "html.parser", from_encoding="iso-8859-1")

        title = None

        for td in soup.find_all("td"):
            text = td.get_text(strip=True)
            if "tulo" in text.lower() and text.endswith(":"):
                next_td = td.find_next_sibling("td")
                if next_td:
                    title = next_td.get_text(strip=True)
                    break

        logger.debug(f"Dados extraídos - Título: {title}")
        return {"title": title}

    def lookup_programa(self, process_number: str) -> Dict[str, Optional[str]]:
        """
        Consulta completa de programa de computador no portal pePI do INPI.

        Fluxo:
        1. Login anônimo (JSESSIONID)
        2. Carrega página de busca de programa
        3. POST do formulário de busca por número de pedido
        4. Extrai CodPedido do link na coluna "Pedido"
        5. Acessa página de detalhe
        6. Extrai o Título

        Args:
            process_number: Número do pedido (ex: "BR 51 2026 002418-8")

        Returns:
            Dict com process_number e title

        Raises:
            ValueError: Programa não encontrado
            requests.ConnectionError: INPI indisponível
            requests.Timeout: Timeout na conexão
        """
        logger.info(f"🔍 Consultando programa de computador no INPI pePI: {process_number}")

        session = self._create_session()

        self._login_anonymous(session)
        self._load_programa_search_page(session)

        search_response = self._search_programa(session, process_number)
        cod_pedido = self._parse_programa_search_results(search_response.content, process_number)

        detail_response = self._fetch_programa_detail_page(session, cod_pedido)
        data = self._parse_programa_detail_page(detail_response.content)
        data["process_number"] = process_number

        logger.info(f"✅ Consulta concluída para programa {process_number}: Título={data.get('title')}")
        return data


    # ============== DESENHO INDUSTRIAL ==============

    def _load_desenho_search_page(self, session: requests.Session) -> None:
        """
        Carrega a página de busca de desenho industrial (DesenhoSearchBasico.jsp).

        Mesmo padrão de patente/programa: o portal exige visita ao formulário
        antes de submeter a busca, sob pena de redirecionar ao login.
        """
        search_page_url = f"{settings.pepi_base_url}/jsp/desenhos/DesenhoSearchBasico.jsp"
        logger.debug(f"Carregando página de busca de desenho: {search_page_url}")
        response = session.get(search_page_url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

    def _search_desenho(self, session: requests.Session, process_number: str) -> requests.Response:
        """
        Executa busca de desenho industrial por número de pedido (POST no form).

        O formulário usa Action=SearchBasico e aceita o número no formato
        compacto com hífen (ex: "BR302025008066-5").
        """
        search_url = f"{settings.pepi_base_url}/servlet/DesenhoServletController"
        form_data = {
            "NumPedido": process_number,
            "FormaPesquisa": "Todas",
            "ExpressaoPesquisa": "",
            "Coluna": "Titulo",
            "RegisterPerPage": "20",
            "Action": "SearchBasico",
        }
        logger.debug(f"Buscando desenho industrial com número: {process_number}")
        response = session.post(search_url, data=form_data, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def _parse_desenho_search_results(self, content: bytes, process_number: str) -> str:
        """
        Encontra o CodPedido do desenho na tabela de resultados.

        A coluna "Pedido" possui um link do tipo:
            <a href='...?Action=detail&CodPedido=1738519&...'>BR 30 2025 008066 5</a>
        """
        soup = BeautifulSoup(content, "html.parser", from_encoding="iso-8859-1")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "Action=detail" in href and "CodPedido=" in href:
                match = re.search(r"CodPedido=(\d+)", href)
                if match:
                    cod_pedido = match.group(1)
                    logger.info(f"✅ Desenho {process_number} encontrado (CodPedido={cod_pedido})")
                    return cod_pedido

        raise ValueError(f"Desenho industrial {process_number} não encontrado nos resultados do INPI")

    def _fetch_desenho_detail_page(self, session: requests.Session, cod_pedido: str) -> requests.Response:
        """Busca a página de detalhe do desenho industrial."""
        detail_url = f"{settings.pepi_base_url}/servlet/DesenhoServletController"
        params = {
            "Action": "detail",
            "CodPedido": cod_pedido,
        }
        logger.debug(f"Acessando detalhe do desenho (CodPedido={cod_pedido})")
        response = session.get(detail_url, params=params, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def _parse_desenho_detail_page(self, content: bytes) -> Dict[str, Optional[str]]:
        """
        Extrai a 'Descrição' da página de detalhe do desenho industrial.

        A página possui vários <td> com texto "Descrição" (uma para o objeto,
        outras para classificação de Locarno e despachos). A primeira ocorrência
        exata é a descrição do objeto (equivalente ao "título" do desenho).

        O valor fica em um <td> de outra linha (não é sibling direto),
        então usamos find_next('td') para pegar o próximo em ordem de documento.
        """
        soup = BeautifulSoup(content, "html.parser", from_encoding="iso-8859-1")

        title = None

        for td in soup.find_all("td"):
            text = td.get_text(strip=True)
            if text.lower() == "descrição":
                next_td = td.find_next("td")
                if next_td:
                    title = next_td.get_text(strip=True)
                    break

        logger.debug(f"Dados extraídos - Descrição: {title}")
        return {"title": title}

    def lookup_desenho(self, process_number: str) -> Dict[str, Optional[str]]:
        """
        Consulta completa de desenho industrial no portal pePI do INPI.

        Fluxo:
        1. Login anônimo (JSESSIONID)
        2. Carrega página de busca de desenho
        3. POST do formulário de busca por número de pedido
        4. Extrai CodPedido do link na coluna "Pedido"
        5. Acessa página de detalhe
        6. Extrai a Descrição (campo title)

        Args:
            process_number: Número do pedido (ex: "BR302025008066-5")

        Returns:
            Dict com process_number e title (Descrição extraída)

        Raises:
            ValueError: Desenho não encontrado
            requests.ConnectionError: INPI indisponível
            requests.Timeout: Timeout na conexão
        """
        logger.info(f"🔍 Consultando desenho industrial no INPI pePI: {process_number}")

        session = self._create_session()

        self._login_anonymous(session)
        self._load_desenho_search_page(session)

        search_response = self._search_desenho(session, process_number)
        cod_pedido = self._parse_desenho_search_results(search_response.content, process_number)

        detail_response = self._fetch_desenho_detail_page(session, cod_pedido)
        data = self._parse_desenho_detail_page(detail_response.content)
        data["process_number"] = process_number

        logger.info(f"✅ Consulta concluída para desenho {process_number}: Descrição={data.get('title')}")
        return data


# Instância singleton
inpi_pepi_service = InpiPepiService()
