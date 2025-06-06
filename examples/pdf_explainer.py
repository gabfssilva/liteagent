
import asyncio
from liteagent import agent
from liteagent.providers import openai
from liteagent.tools.pdf import read_pdf_from_url


@agent(provider=openai(), tools=[read_pdf_from_url])
async def pdf_explainer(figure: str, pdf_url: str) -> str:
    """ what's on figure {figure} of PDF {pdf_url}? """


if __name__ == "__main__":
    asyncio.run(
        pdf_explainer(
            figure="5.f",
            pdf_url="https://watermark.silverchair.com/biae087.pdf?token=AQECAHi208BE49Ooan9kkhW_Ercy7Dm3ZL_9Cf3qfKAc485ysgAAA18wggNbBgkqhkiG9w0BBwagggNMMIIDSAIBADCCA0EGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMPYMnctHnKIp_4ZNxAgEQgIIDEp3RuhxHksKJo5AjrKT11CHJv8Vxsa1aRI9ydpATS_GHRJ4Pv_Zoh8R97rmFkyhchGRBhLe_USSjaxM0RspYk7Z-AR2dm-m83Wol2pLS4KoF6WnaXxh_zi6cYg8BXnlg_SpYLEG2TO2uq5pVarRMM6t0guFSj74vdM1an0k9Syf305xV7wQIC9ivbRnAt-YuRdSDjuJoc4osRt8MlIZ3vJNMa66nk1nApfdHMiSOcwkJlvOAsSgG1G74DC0pvJDjHN-Qxbrh6e0dvk21V3BWGzBCdUPHSgdAA7I8AtL_ZzA-ITS1fM5ytIjHOdSNDqDxJ26mvOuzW46M2JLHDZpUjWlqcrR-inEbPel5ipRtXCBiyTJcCdt7FC95SVS1WnfbIEyfMMnJw4S9NtmIkTrusjeEizJ13QwcTlyLXbIEhJ-6WBAvQnmzPWfm-AueYSSWLHTEq-kOACmG6aFnMFaFUF567Sz3egDjbPBQT22ypPb8ADqnTw9V61kUaZwtYEhqorrA-7CcY2pV0y2-0PYjf4tC3sXxb5qGfyV5mqOCoKSvFg7tyQkX56nDR90GEKVsqvVsSOUMpRaRet0_qAd9hrLE2euTS6ZNzzNOsqhDQUilKZn3qKLcFc0J7iWgy7Ur-qUozg39TZ8y0G_zPCzbXUdo5P4v3kM7VGBafUzCfBVCjAKs7O5r5mxVTbpxQ7-DJu2esra1dsLYdxxWU8dfE_mZOafAAYZnlFs517ZuiK8r9osqVmij0tB0siX99N6EKqFwG5cBVtiQVieHtUmIqdrXkQDCTP2AFNSx7sP-D7ee4XForm6Fce0-Ejc1qmYO8C3h5Yg9af327KC85Sx5zL8ydWfbc7RaIZMcb_jz32dHIQp8OGq5pjE9p3roMtE6sTxDGX2A2NW5hZaKE7_NTyegI17yYD0CfHqF6gvo38TSDzNEt8D91QA1vO60dRpTCUTrmf2PmPMp6oNwIwDeT7ZB6awi9nmMwySDOAbysDNC6qrBsipK8T8GYFOwgSrJc3TjzsxNiKPxwxlM08Kxg_MWrQ"
        )
    )
