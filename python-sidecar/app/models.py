from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["en", "hi", "auto"]


class TranscribeRequest(BaseModel):
    audio_base64: str
    mime_type: str = "audio/webm"
    language: Language = "auto"


class TranscribeResponse(BaseModel):
    text: str
    language_detected: Language


class ParseRequest(BaseModel):
    text: str
    language: Language = "en"


class ParsedToken(BaseModel):
    text: str
    lemma: str
    pos: str
    dep: str
    head: int = Field(description="Index of syntactic head in the token list")
    is_stop: bool


class ParsedClause(BaseModel):
    tokens: list[ParsedToken]
    language: Language


class ParseResponse(BaseModel):
    clauses: list[ParsedClause]


class GlossToken(BaseModel):
    gloss: str = Field(description="ALL CAPS sign, or FS_<WORD> for fingerspelled")
    kind: Literal["sign", "fingerspell", "paraphrase", "marker"] = "sign"
    source_text: str = Field(description="Original word(s) this gloss came from")


class GlossRequest(BaseModel):
    text: str
    language: Language = "en"


class GlossResponse(BaseModel):
    gloss: list[GlossToken]
