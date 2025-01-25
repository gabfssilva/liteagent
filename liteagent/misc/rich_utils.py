# import yaml
# from rich.console import RenderableType
#
# from rich.panel import Panel
# from rich.syntax import Syntax
# 
#
# def pretty_yaml(data, title=None, wrap=False) -> RenderableType:
#     encoded = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()
#     code = Syntax(code=encoded, lexer="yaml", theme='ansicyan')
#
#     if not wrap:
#         return code
#
#     return Panel(
#         renderable=code,
#         title=title,
#     )
