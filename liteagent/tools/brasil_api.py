from liteagent import tool, Tools
from liteagent.tools import http

class BrasilApi(Tools):
    @tool
    @http(url='https://brasilapi.com.br/api/cep/v1/{cep}')
    async def address_by_cep(self, cep: str) -> str:
        """Use this tool to fetch the address of a given CEP."""

    @tool
    @http(url='https://brasilapi.com.br/api/banks/v1')
    async def get_all_banks(self) -> str:
        """Use this tool to fetch information about all banks in Brazil."""

    @tool
    @http(url='https://brasilapi.com.br/api/banks/v1/{code}')
    async def get_bank_by_code(self, code: str) -> str:
        """Use this tool to fetch bank information using a bank code."""

    @tool
    @http(url='https://brasilapi.com.br/api/cambio/v1/moedas')
    async def get_exchange_currencies(self) -> str:
        """Use this tool to fetch available exchange currencies."""

    @tool
    @http(url='https://brasilapi.com.br/api/cambio/v1/cotacao/{moeda}/{data}')
    async def get_exchange_rate(self, moeda: str, data: str) -> str:
        """Use this tool to fetch the exchange rate of a given currency for a specific date."""

    @tool
    @http(url='https://brasilapi.com.br/api/cnpj/v1/{cnpj}')
    async def get_company_by_cnpj(self, cnpj: str) -> str:
        """Use this tool to fetch company data using a CNPJ."""

    @tool
    @http(url='https://brasilapi.com.br/api/ddd/v1/{ddd}')
    async def get_ddd_info(self, ddd: str) -> str:
        """Use this tool to fetch state and city information by DDD."""

    @tool
    @http(url='https://brasilapi.com.br/api/feriados/v1/{ano}')
    async def get_holidays(self, ano: str) -> str:
        """Use this tool to fetch national holidays for a given year."""

    @tool
    @http(url='https://brasilapi.com.br/api/fipe/marcas/v1/{tipoVeiculo}')
    async def get_vehicle_brands(self, tipoVeiculo: str) -> str:
        """Use this tool to fetch vehicle brands for a given type of vehicle (caminhoes, carros, motos)."""

    @tool
    @http(url='https://brasilapi.com.br/api/fipe/preco/v1/{codigoFipe}')
    async def get_vehicle_price(self, codigoFipe: str) -> str:
        """Use this tool to fetch the price of a vehicle according to FIPE table."""

    @tool
    @http(url='https://brasilapi.com.br/api/ibge/municipios/v1/{siglaUF}')
    async def get_municipios_by_uf(self, siglaUF: str) -> str:
        """Use this tool to fetch municipalities of a given state."""

    @tool
    @http(url='https://brasilapi.com.br/api/ibge/uf/v1')
    async def get_all_states(self) -> str:
        """Use this tool to fetch all states in Brazil."""

    @tool
    @http(url='https://brasilapi.com.br/api/ibge/uf/v1/{code}')
    async def get_state_by_code(self, code: str) -> str:
        """Use this tool to fetch state information using a code or abbreviation."""

    @tool
    @http(url='https://brasilapi.com.br/api/isbn/v1/{isbn}')
    async def get_book_by_isbn(self, isbn: str) -> str:
        """Use this tool to fetch book information using an ISBN."""

    @tool
    @http(url='https://brasilapi.com.br/api/ncm/v1/{code}')
    async def get_ncm_info(self, code: str) -> str:
        """Use this tool to fetch NCM information using a code."""

    @tool
    @http(url='https://brasilapi.com.br/api/pix/v1/participants')
    async def get_pix_participants(self) -> str:
        """Use this tool to fetch information about PIX participants."""

    @tool
    @http(url='https://brasilapi.com.br/api/registrobr/v1/{domain}')
    async def check_domain_status(self, domain: str) -> str:
        """Use this tool to evaluate the status of a .br domain."""

    @tool
    @http(url='https://brasilapi.com.br/api/taxas/v1')
    async def get_interest_rates(self) -> str:
        """Use this tool to fetch interest rates and official indexes in Brazil."""

    @tool
    @http(url='https://brasilapi.com.br/api/taxas/v1/{sigla}')
    async def get_interest_rate_by_code(self, sigla: str) -> str:
        """Use this tool to fetch interest rate information using a specific name or acronym."""

brasil_api = BrasilApi()