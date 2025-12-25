from pydantic import BaseModel, Field
from typing import Annotated, List

class CodeReview(BaseModel):
    file: str
    line_number: int = Field(description="The absolute line number in the new file")
    type: str
    severity: str = Field(description="critical, major or minor")
    comment: str
    suggestion: str
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(description="A float value between zero and one signifing strength of the review")

class ReviewResponse(BaseModel):
    reviews: List[CodeReview]
