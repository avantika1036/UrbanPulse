"""
backend/routes/reports.py

Endpoints for PDF report generation.
"""

import os
import sys
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, PROJECT_ROOT)

from reports.generate_pdf_report import generate_report

router = APIRouter()


class PDFRequest(BaseModel):
    """Request body for PDF generation."""
    persona: str
    cities_compared: list[str]
    best_city: str
    monthly_income: float
    source_city: Optional[str] = None
    scores: dict
    top_positive: dict
    top_negative: dict
    drivers: dict
    health_data: dict
    salary_equivalence: Optional[dict] = None
    narrative: Optional[str] = None


@router.post("/generate-pdf")
def generate_pdf_report(request: PDFRequest):
    """
    Generates a PDF relocation intelligence report.
    
    Takes the comparison data and optional AI narrative, then generates
    a professionally formatted PDF report using fpdf2.
    
    Returns the filename of the generated PDF which can be downloaded
    from /reports/download/{filename}.
    """
    try:
        # Convert Pydantic model to dict for the PDF generator
        comparison_data = request.model_dump()
        
        # Generate PDF
        pdf_path = generate_report(
            comparison_data=comparison_data,
            narrative=comparison_data.get("narrative")
        )
        
        # Extract just the filename for the response
        filename = os.path.basename(pdf_path)
        
        return {
            "status": "success",
            "filename": filename,
            "message": "PDF generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(e)}"
        )
