import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
ROOT=Path(__file__).resolve().parents[1]


class GeminiService:
    def __init__(self):
        self.api_key=os.getenv("GEMINI_API_KEY","").strip()
        self.model=os.getenv("GEMINI_MODEL","").strip()
        self.client=None
        if self.api_key:
            try:
                from google import genai
                self.client=genai.Client(api_key=self.api_key)
            except Exception:
                self.client=None

    @property
    def available(self): return self.client is not None and bool(self.model)

    def generate(self,prompt,contents=None):
        if not self.available: raise RuntimeError("Gemini is not configured. Add GEMINI_API_KEY and GEMINI_MODEL to your .env file.")
        response=self.client.models.generate_content(model=self.model,contents=contents if contents is not None else prompt, config={"system_instruction":prompt})
        result=getattr(response,"text",None)
        if not result: raise RuntimeError("Gemini returned an empty response. Please try again.")
        return result.strip()

    def analyze_project_material(self,filename,text,path=None):
        prompt=(ROOT/"prompts"/"extraction.txt").read_text(encoding="utf-8")
        contents=[f"Source filename: {filename}\nExtracted text:\n{text[:30000]}"]
        if path and Path(path).suffix.lower() in {".png",".jpg",".jpeg"}:
            from google.genai import types
            contents=[types.Part.from_bytes(data=Path(path).read_bytes(),mime_type="image/jpeg" if Path(path).suffix.lower() in {".jpg",".jpeg"} else "image/png"),contents[0]]
        elif path and Path(path).suffix.lower()==".pdf" and not text.strip():
            from google.genai import types
            contents=[types.Part.from_bytes(data=Path(path).read_bytes(),mime_type="application/pdf"),contents[0]]
        raw=self.generate(prompt,contents)
        raw=raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)

    def extract_memory(self,*args,**kwargs): return self.analyze_project_material(*args,**kwargs)

    def ask_project_question(self,question,context):
        prompt=(ROOT/"prompts"/"chat.txt").read_text(encoding="utf-8")
        return self.generate(prompt,[f"PROJECT CONTEXT\n{context}\n\nUSER QUESTION\n{question}"])

    def generate_catchup(self,context):
        return self.generate((ROOT/"prompts"/"catchup.txt").read_text(encoding="utf-8"),context)

    def generate_handoff(self,context):
        return self.generate((ROOT/"prompts"/"handoff.txt").read_text(encoding="utf-8"),context)
