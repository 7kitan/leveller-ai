"""
PII Masking Utilities for Work History

Provides additional PII masking for work history data before database storage.
"""
import re
import logging

logger = logging.getLogger(__name__)


def mask_company_name(company_name: str) -> str:
    """
    Mask potentially sensitive company names.
    
    Args:
        company_name: Original company name
        
    Returns:
        Masked company name if it appears to be a small/private company,
        otherwise returns original name for well-known companies.
    """
    if not company_name or company_name == "N/A":
        return company_name
    
    # List of well-known companies that don't need masking
    # (public companies, large corporations)
    KNOWN_COMPANIES = {
        "google", "microsoft", "amazon", "facebook", "meta", "apple",
        "netflix", "uber", "grab", "shopee", "lazada", "tiki",
        "vng", "fpt", "viettel", "vnpt", "momo", "zalopay",
        "samsung", "lg", "sony", "intel", "nvidia", "amd"
    }
    
    company_lower = company_name.lower().strip()
    
    # Check if it's a well-known company
    for known in KNOWN_COMPANIES:
        if known in company_lower:
            return company_name  # Don't mask well-known companies
    
    # For other companies, mask if they appear to be small/private
    # Keep first 2 chars + "***" + last char
    if len(company_name) > 4:
        masked = company_name[:2] + "***" + company_name[-1]
        logger.debug(f"Masked company name: {company_name} -> {masked}")
        return masked
    
    return company_name


def mask_work_history(work_history: list) -> list:
    """
    BUG-005 FIX: Apply PII masking to work history before database storage.
    
    Args:
        work_history: List of work history entries
        
    Returns:
        Work history with masked company names
    """
    masked_history = []
    
    for entry in work_history:
        masked_entry = entry.copy()
        
        # Mask company name if present
        if "company" in masked_entry:
            masked_entry["company"] = mask_company_name(masked_entry["company"])
        
        # Mask any email addresses in description
        if "description" in masked_entry and masked_entry["description"]:
            desc = masked_entry["description"]
            # Mask email addresses
            desc = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                         '[EMAIL]', desc)
            # Mask phone numbers
            desc = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', desc)
            masked_entry["description"] = desc
        
        masked_history.append(masked_entry)
    
    return masked_history
