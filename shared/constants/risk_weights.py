# Risk calculation constants for fraud detection

RISK_SCORES = {
    "LOW": 0.25,
    "MEDIUM": 0.50,
    "HIGH": 0.75,
    "CRITICAL": 1.0,
}

THRESHOLDS = {
    "large_transaction": 10000,
    "rapid_transfers": 5,
    "rapid_transfer_window_hours": 1,
    "same_address_entities": 3,
    "shell_company_hops": 3,
    "offshore_jurisdiction_score": 0.8,
    "cyclical_transfer_threshold": 0.9,
    "risk_score_high": 0.7,
    "risk_score_critical": 0.9,
}

WEIGHTS = {
    "transaction_amount": 0.30,
    "network_centrality": 0.25,
    "behavioral_anomaly": 0.20,
    "pattern_match": 0.15,
    "community_risk": 0.10,
}

ENTITY_TYPES = ["Person", "Company", "BankAccount", "Device", "Address", "Transaction"]
TRANSACTION_TYPES = ["WIRE", "ACH", "CASH", "CHECK", "CRYPTO"]
ACCOUNT_TYPES = ["CHECKING", "SAVINGS", "BUSINESS", "TRUST", "OFFSHORE"]

OFFSHORE_JURISDICTIONS = [
    "BS", "BM", "KY", "LU", "CH", "VG", "KY", "JE", "GG", "IM",
    "PA", "CR", "BZ", "SC", "MT", "AD", "LI", "MH", "WS"
]

HIGH_RISK_INDUSTRIES = [
    "Casinos", "Money Services", "Jewelry", "Real Estate",
    "Charities", "Political Organizations"
]

COMPLIANCE_FLAGS = {
    "CTR": "Currency Transaction Report (> $10,000)",
    "SAR": "Suspicious Activity Report",
    "CMIR": "Currency/Monetary Instrument Report",
    "FBAR": "Foreign Bank Account Report",
    "Form 8300": "Report of Cash Payments Over $10,000",
}
