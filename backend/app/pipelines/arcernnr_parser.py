"""ARCERNNR Excel/PDF Parser — deferred to V2.

This pipeline will parse Excel and PDF reports from:
- ARCERNNR (Agencia de Regulación y Control de Energía y Recursos Naturales No Renovables)
- INEC microdata

V2 notes:
- Primary target: "Balance Nacional de Energía Eléctrica (BNEE)" dataset on the
  open data portal — aggregated national data, likely easier to parse than raw PDFs.
- Secondary: annual statistical bulletins (Boletín Estadístico ARCERNNR) in PDF format.
- Use pdfplumber for PDF text extraction, openpyxl for Excel.

Deferred because:
1. CENACE real-time + CKAN quarterly covers the MVP data requirements.
2. ARCERNNR data is annual and adds complexity without unblocking the MVP.
3. BNEE dataset structure needs further investigation before implementation.
"""
