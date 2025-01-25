from liteagent import Tools, tool


class Calculator(Tools):
    @tool
    def add(self, x: int, y: int):
        return x + y

    @tool
    def div(self, x: int, y: int):
        return x / y

    @tool
    def sub(self, x: int, y: int):
        return x - y

    @tool
    def multiply(self, x: int, y: int):
        return x * y
