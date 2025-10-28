"""
Configurações e fixtures compartilhadas entre todos os testes.
"""


async def extract_text(result) -> str:
    """
    Helper para extrair texto de diferentes tipos de retorno de agent.

    Agents podem retornar:
    - str diretamente
    - Message com content TextStream
    - Message com content str
    """
    if isinstance(result, str):
        return result

    if hasattr(result, 'content'):
        content = result.content
        if hasattr(content, 'await_complete'):
            return await content.await_complete()
        return str(content)

    return str(result)
