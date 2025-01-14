# import json
# from typing import final
#
# # import yaml
# from pydantic import BaseModel, create_model
# from rich.panel import Panel
# from rich.syntax import Syntax
#
# from rich.console import RenderableType
#
#
# class PrettyModel(BaseModel):
#     class Config:
#         extra = "allow"
#
#     def __init__(self, _rich_title=None, **data):
#         super().__init__(**data)
#         self._rich_title = lambda: _rich_title
#
#     def __rich__(self) -> RenderableType:
#         return pretty_yaml(self.model_dump(), title=self._rich_title())
#
#
# def create_pretty_model(rich_title, **kwargs) -> PrettyModel:
#     return PrettyModel(_rich_title=rich_title, **kwargs)
#
# 
# def pretty_yaml(data, title=None) -> RenderableType:
#     encoded = yaml.dump(data, default_flow_style=False, sort_keys=True, allow_unicode=True).strip()
#
#     return Panel(
#         renderable=Syntax(code=encoded, lexer="yaml", theme='colorful'),
#         title=title,
#     )
#
# #
# # from pygments.styles import get_all_styles
# #
# # styles = list(get_all_styles())
# #
# # print(styles)
