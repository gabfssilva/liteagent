from liteagents import Agent, tools, auditors, providers

openalex_agent = Agent(
    name="OpenAlex",
    description="An agent specialized in interacting with OpenAlex APIs",
    provider=providers.deepseek(),
    tools=tools.openalex.all + [tools.read_pdf_from_url],
    intercept=auditors.console()
)

*_, _ = openalex_agent.sync("""
I want you to search for 3 pagers on large language models.
Based on their abstract, choose one of them, the one you find the most amusing.
After that, I want you to:

- Download their PDF
- Summarize it for me
- Elaborate some key points of your own.

 (for arxiv urls, you must change the /abs/ to /pdf/ before downloading the PDF)
""")
