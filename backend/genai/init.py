"""
backend/genai/

Generative AI narrative layer for UrbanPulse.

Contains:
  gemini_narrator.py — generate_relocation_narrative() using Google Gemini
                        1.5-flash with in-memory caching and a clean
                        template-string fallback if the API call fails.
"""