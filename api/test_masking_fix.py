#!/usr/bin/env python3
"""
Test script for the enhanced PII masking functionality.
"""

import os
import tempfile
from enhanced_pii_masker import EnhancedPIIMasker, MaskingConfig

def test_masking_strategies():
    """Test different masking strategies with a simple PDF."""
    
    # Create test masking configurations
    test_configs = [
        MaskingConfig(
            text="Aaron Mehta",
            pii_type="PERSON", 
            strategy="pseudo",
            page_num=0,
            x0=100.0, y0=200.0, x1=200.0, y1=220.0,
            priority=1
        ),
        MaskingConfig(
            text="aaron.mehta@example-test.com",
            pii_type="EMAIL",
            strategy="mask", 
            page_num=0,
            x0=100.0, y0=240.0, x1=300.0, y1=260.0,
            priority=2
        ),
        MaskingConfig(
            text="12/07/1989",
            pii_type="DATE_OF_BIRTH",
            strategy="redact",
            page_num=0, 
            x0=100.0, y0=280.0, x1=200.0, y1=300.0,
            priority=3
        )
    ]
    
    print("Testing masking strategies:")
    print(f"- Redaction: '[REDACTED]'")
    print(f"- Masking: asterisks (*)")
    print(f"- Pseudo: fake replacement data")
    
    masker = EnhancedPIIMasker()
    
    # Test replacement text generation
    for config in test_configs:
        # Create a single config region for testing
        from enhanced_pii_masker import CoordinateRegion
        region = CoordinateRegion(
            x0=config.x0, y0=config.y0, x1=config.x1, y1=config.y1,
            configs=[config], page_num=config.page_num
        )
        
        replacement = masker.generate_replacement_text(region)
        print(f"Original: '{config.text}' -> Strategy: {config.strategy} -> Replacement: '{replacement}'")
    
    print("\nMasking strategy test completed!")

if __name__ == "__main__":
    test_masking_strategies()
