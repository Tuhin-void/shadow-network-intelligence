# Jurisdiction codes and compliance requirements

JURISDICTIONS = {
    "US": {
        "name": "United States",
        "regulator": "FinCEN",
        "codes": ["CTR", "SAR", "CMIR", "FBAR", "8300"],
        "threshold_usd": 10000,
    },
    "EU": {
        "name": "European Union",
        "regulator": "EBA",
        "codes": ["STR", "CTR", "ECDD"],
        "threshold_eur": 15000,
    },
    "UK": {
        "name": "United Kingdom",
        "regulator": "FCA",
        "codes": ["SAR", "CTR", "NCA"],
        "threshold_gbp": 10000,
    },
    "CA": {
        "name": "Canada",
        "regulator": "FINTRAC",
        "codes": ["STR", "CTR", "EVT"],
        "threshold_cad": 10000,
    },
    "AU": {
        "name": "Australia",
        "regulator": "AUSTRAC",
        "codes": ["SMR", "CTR", "IIT"],
        "threshold_aud": 10000,
    },
    "BS": {
        "name": "Bahamas",
        "regulator": "CBOS",
        "offshore": True,
    },
    "KY": {
        "name": "Cayman Islands",
        "regulator": "CIMA",
        "offshore": True,
    },
    "CH": {
        "name": "Switzerland",
        "regulator": "FINMA",
        "offshore": True,
    },
}

COUNTRY_CODES = {
    "US": "United States",
    "CA": "Canada",
    "UK": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "BS": "Bahamas",
    "KY": "Cayman Islands",
    "CH": "Switzerland",
    "LU": "Luxembourg",
    "NL": "Netherlands",
    "SG": "Singapore",
    "HK": "Hong Kong",
    "BM": "Bermuda",
    "VG": "British Virgin Islands",
    "PA": "Panama",
}

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}
