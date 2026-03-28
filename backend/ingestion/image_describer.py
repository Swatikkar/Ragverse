# backend/ingestion/image_describer.py
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from config import VISION_MODEL
import base64

llm = ChatOllama(model=VISION_MODEL)

def describe_image(image_b64: str, context: str = "", page_num: int = None) -> str:

    prompt = f"""You are analyzing an image extracted from a research document.
Describe this image in detail for research purposes. Include:
- Type of visual (chart, diagram, photo, table, screenshot etc.)
- All text, labels, axes, legends visible
- Key data points or relationships shown
- What insight this image conveys

{'Page context: ' + context if context else ''}
{'Page number: ' + str(page_num) if page_num else ''}

Be thorough — your description will be used to answer research questions."""

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": f"data:image/png;base64,{image_b64}"}
        ]
    )

    response = llm.invoke([message])
    return response.content