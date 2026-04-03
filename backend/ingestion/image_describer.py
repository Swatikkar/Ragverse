from langchain_core.messages import HumanMessage
from config import ENV, VISION_MODEL

def get_vision_llm():
    if ENV == "local":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=VISION_MODEL)
    
    elif ENV == "production":
        from langchain_google_genai import ChatGoogleGenerativeAI
        from config import GEMINI_API_KEY
        return ChatGoogleGenerativeAI(
            model=VISION_MODEL,
            google_api_key=GEMINI_API_KEY
        )

llm = get_vision_llm()

def describe_image(image_b64: str, context: str = "", page_num: int = None) -> str:
    prompt = f"""Look at this image carefully and describe exactly what you see.

Be specific and factual:
- What type of image is this? (logo, QR code, photo, ticket, chart, banner, icon, etc.)
- What text is visible? Extract ALL text exactly as it appears
- What information does this image convey?
- Any numbers, dates, names, places visible?

{('Context from surrounding page: ' + context) if context else ''}

Important:
- Only describe what you actually see
- Do not assume or make up information
- Do not call this a research document
- Keep it concise and factual"""

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": f"data:image/png;base64,{image_b64}"}
        ]
    )

    response = llm.invoke([message])
    return response.content