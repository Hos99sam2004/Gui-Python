#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to create the project report document
"""
from docx import Document
from utils import setup_document_margins
from sections import (
    add_header,
    add_objectives_section,
    add_achievements_section,
    add_progress_section,
    add_summary_section,
    add_next_steps_section,
    add_footer
)


def create_report():
    """Create the main project report document"""
    # Create document
    doc = Document()
    
    # Setup document margins
    setup_document_margins(doc)
    
    # Add all sections
    add_header(doc)
    add_objectives_section(doc)
    add_achievements_section(doc)
    add_progress_section(doc)
    add_summary_section(doc)
    add_next_steps_section(doc)
    add_footer(doc)
    
    # Save
    doc.save('تقرير_المشروع_محسّن.docx')
    print("✓ تم إنشاء الملف: تقرير_المشروع_محسّن.docx")


if __name__ == "__main__":
    create_report()
