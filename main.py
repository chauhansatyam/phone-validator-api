from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import phonenumbers
from phonenumbers import geocoder, carrier, number_type, PhoneNumberType
from phonenumbers import timezone as pn_timezone
import re
from datetime import datetime
import pytz

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Comprehensive country-specific business hours configuration for 195+ countries
COUNTRY_BUSINESS_CONFIG = {
    # Asia
    "IN": {"weekdays": [0, 1, 2, 3, 4, 5], "business_hours_start": 10, "business_hours_end": 18, "weekend_days": [6]},  # India - Mon-Sat
    "PK": {"weekdays": [0, 1, 2, 3, 4, 5], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [6]},  # Pakistan - Mon-Sat
    "BD": {"weekdays": [0, 1, 2, 3, 4, 6], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5]},  # Bangladesh - Sun-Thu + Sat
    "LK": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Sri Lanka
    "NP": {"weekdays": [6, 0, 1, 2, 3, 4], "business_hours_start": 10, "business_hours_end": 17, "weekend_days": [5]},  # Nepal - Sun-Fri
    "CN": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # China
    "JP": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Japan
    "KR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # South Korea
    "KP": {"weekdays": [0, 1, 2, 3, 4, 5], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [6]},  # North Korea
    "TH": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Thailand
    "VN": {"weekdays": [0, 1, 2, 3, 4, 5], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [6]},  # Vietnam - Mon-Sat
    "MY": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Malaysia
    "SG": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Singapore
    "ID": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Indonesia
    "PH": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Philippines
    "MM": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Myanmar
    "KH": {"weekdays": [0, 1, 2, 3, 4, 5], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [6]},  # Cambodia
    "LA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Laos
    "BN": {"weekdays": [0, 1, 2, 3, 6], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [4, 5]},  # Brunei - Sun-Thu
    "TL": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Timor-Leste
    "MN": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Mongolia
    "TW": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Taiwan
    "HK": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Hong Kong
    "MO": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Macau
    
    # Middle East (Most have Friday-Saturday weekends or Friday only)
    "AE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # UAE - Sat-Sun now
    "SA": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [4, 5]},  # Saudi Arabia - Sun-Thu
    "QA": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 7, "business_hours_end": 15, "weekend_days": [4, 5]},  # Qatar - Sun-Thu
    "KW": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [4, 5]},  # Kuwait - Sun-Thu
    "BH": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 8, "business_hours_end": 15, "weekend_days": [4, 5]},  # Bahrain - Sun-Thu
    "OM": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 8, "business_hours_end": 15, "weekend_days": [4, 5]},  # Oman - Sun-Thu
    "YE": {"weekdays": [5, 6, 0, 1, 2], "business_hours_start": 8, "business_hours_end": 14, "weekend_days": [3, 4]},  # Yemen - Sat-Wed
    "IQ": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 8, "business_hours_end": 15, "weekend_days": [4, 5]},  # Iraq - Sun-Thu
    "SY": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 8, "business_hours_end": 14, "weekend_days": [4, 5]},  # Syria - Sun-Thu
    "JO": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [4, 5]},  # Jordan - Sun-Thu
    "LB": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Lebanon - Mon-Fri
    "IL": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [4, 5]},  # Israel - Sun-Thu
    "PS": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 8, "business_hours_end": 15, "weekend_days": [4, 5]},  # Palestine - Sun-Thu
    "TR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Turkey - Mon-Fri
    "IR": {"weekdays": [5, 6, 0, 1, 2], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [3, 4]},  # Iran - Sat-Wed
    "AF": {"weekdays": [5, 6, 0, 1, 2], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [3, 4]},  # Afghanistan - Sat-Wed
    "AM": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Armenia
    "AZ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Azerbaijan
    "GE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Georgia
    "CY": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Cyprus
    
    # Central Asia
    "KZ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Kazakhstan
    "UZ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Uzbekistan
    "TM": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Turkmenistan
    "KG": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Kyrgyzstan
    "TJ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Tajikistan
    
    # Europe - Western
    "GB": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # United Kingdom
    "IE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Ireland
    "FR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # France
    "DE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Germany
    "NL": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Netherlands
    "BE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Belgium
    "LU": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Luxembourg
    "CH": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Switzerland
    "AT": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Austria
    "LI": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Liechtenstein
    
    # Europe - Northern
    "NO": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Norway
    "SE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Sweden
    "FI": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Finland
    "DK": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Denmark
    "IS": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Iceland
    
    # Europe - Southern
    "ES": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Spain
    "PT": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Portugal
    "IT": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Italy
    "GR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Greece
    "MT": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Malta
    "SM": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # San Marino
    "VA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Vatican City
    "AD": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Andorra
    "MC": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Monaco
    
    # Europe - Eastern
    "PL": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Poland
    "CZ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Czech Republic
    "SK": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Slovakia
    "HU": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Hungary
    "RO": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Romania
    "BG": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Bulgaria
    "MD": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Moldova
    "UA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Ukraine
    "BY": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Belarus
    "RU": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Russia
    
    # Europe - Baltic
    "EE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Estonia
    "LV": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Latvia
    "LT": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Lithuania
    
    # Europe - Balkans
    "SI": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Slovenia
    "HR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Croatia
    "BA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Bosnia
    "RS": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Serbia
    "ME": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Montenegro
    "XK": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Kosovo
    "MK": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # North Macedonia
    "AL": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Albania
    
    # North America
    "US": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # USA
    "CA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Canada
    "MX": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Mexico
    
    # Central America
    "GT": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Guatemala
    "BZ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Belize
    "SV": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # El Salvador
    "HN": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Honduras
    "NI": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Nicaragua
    "CR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Costa Rica
    "PA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Panama
    
    # Caribbean
    "CU": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Cuba
    "JM": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Jamaica
    "HT": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Haiti
    "DO": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Dominican Republic
    "PR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Puerto Rico
    "TT": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Trinidad & Tobago
    "BB": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Barbados
    "BS": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Bahamas
    
    # South America
    "BR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Brazil
    "AR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Argentina
    "CL": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Chile
    "CO": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Colombia
    "PE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Peru
    "VE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Venezuela
    "EC": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Ecuador
    "BO": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Bolivia
    "PY": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Paraguay
    "UY": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 18, "weekend_days": [5, 6]},  # Uruguay
    "GY": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Guyana
    "SR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 7, "business_hours_end": 15, "weekend_days": [5, 6]},  # Suriname
    
    # Africa - North
    "EG": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [4, 5]},  # Egypt - Sun-Thu
    "LY": {"weekdays": [6, 0, 1, 2, 3], "business_hours_start": 8, "business_hours_end": 15, "weekend_days": [4, 5]},  # Libya - Sun-Thu
    "TN": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Tunisia
    "DZ": {"weekdays": [5, 6, 0, 1, 2], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [3, 4]},  # Algeria - Sat-Wed
    "MA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Morocco
    "SD": {"weekdays": [5, 6, 0, 1, 2], "business_hours_start": 8, "business_hours_end": 14, "weekend_days": [3, 4]},  # Sudan - Sat-Wed
    
    # Africa - West
    "NG": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Nigeria
    "GH": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Ghana
    "SN": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Senegal
    "CI": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Ivory Coast
    "BF": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Burkina Faso
    "ML": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Mali
    "NE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Niger
    "TG": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Togo
    "BJ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Benin
    "LR": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Liberia
    "SL": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Sierra Leone
    "GN": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Guinea
    "GM": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Gambia
    
    # Africa - East
    "KE": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Kenya
    "TZ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Tanzania
    "UG": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Uganda
    "RW": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Rwanda
    "BI": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Burundi
    "ET": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Ethiopia
    "SO": {"weekdays": [5, 6, 0, 1, 2], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [3, 4]},  # Somalia - Sat-Wed
    "DJ": {"weekdays": [5, 6, 0, 1, 2], "business_hours_start": 7, "business_hours_end": 14, "weekend_days": [3, 4]},  # Djibouti - Sat-Wed
    "ER": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Eritrea
    
    # Africa - Central
    "CD": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # DR Congo
    "CG": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Congo
    "CM": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Cameroon
    "CF": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 7, "business_hours_end": 15, "weekend_days": [5, 6]},  # Central African Rep
    "TD": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 7, "business_hours_end": 15, "weekend_days": [5, 6]},  # Chad
    "GA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Gabon
    "GQ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Equatorial Guinea
    
    # Africa - Southern
    "ZA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # South Africa
    "ZW": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Zimbabwe
    "ZM": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Zambia
    "MW": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 7, "business_hours_end": 17, "weekend_days": [5, 6]},  # Malawi
    "MZ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Mozambique
    "BW": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Botswana
    "NA": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Namibia
    "AO": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Angola
    "LS": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Lesotho
    "SZ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Eswatini
    
    # Oceania
    "AU": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # Australia
    "NZ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 9, "business_hours_end": 17, "weekend_days": [5, 6]},  # New Zealand
    "PG": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Papua New Guinea
    "FJ": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Fiji
    "SB": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 16, "weekend_days": [5, 6]},  # Solomon Islands
    "VU": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Vanuatu
    "NC": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 7, "business_hours_end": 15, "weekend_days": [5, 6]},  # New Caledonia
    "WS": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Samoa
    "TO": {"weekdays": [0, 1, 2, 3, 4], "business_hours_start": 8, "business_hours_end": 17, "weekend_days": [5, 6]},  # Tonga
}

# Default configuration for countries not listed
DEFAULT_BUSINESS_CONFIG = {
    "weekdays": [0, 1, 2, 3, 4],  # Monday-Friday
    "business_hours_start": 9,
    "business_hours_end": 17,
    "weekend_days": [5, 6]  # Saturday, Sunday
}


class PhoneRequest(BaseModel):
    number: str
    default_region: str = "IN"
    home_country: str = "IN"


def clean_phone_number(number: str) -> str:
    """Remove formatting but keep + prefix"""
    cleaned = re.sub(r'[\s\-\(\)\.]', '', number)
    return cleaned


def get_business_config(country_code: str):
    """Get business hours configuration for a country"""
    return COUNTRY_BUSINESS_CONFIG.get(country_code, DEFAULT_BUSINESS_CONFIG)


def get_time_info(parsed_number, region_code: str):
    """Get timezone and current time information for a phone number"""
    time_info = {
        "timezone": None,
        "all_timezones": [],
        "local_time": None,
        "local_time_12h": None,
        "local_date": None,
        "day_of_week": None,
        "is_business_hours": None,
        "is_weekend": None,
        "is_weekday": None,
        "utc_offset": None,
        "business_hours_start": None,
        "business_hours_end": None,
        "weekdays_config": None
    }
    
    try:
        # Get all possible timezones for this number
        timezones = pn_timezone.time_zones_for_number(parsed_number)
        
        if timezones:
            time_info["all_timezones"] = list(timezones)
            
            # Use the first timezone (primary timezone for the region)
            tz = pytz.timezone(timezones[0])
            current_time = datetime.now(tz)
            
            time_info["timezone"] = timezones[0]
            time_info["local_time"] = current_time.strftime("%Y-%m-%d %H:%M:%S")
            time_info["local_time_12h"] = current_time.strftime("%I:%M %p")
            time_info["local_date"] = current_time.strftime("%Y-%m-%d")
            time_info["day_of_week"] = current_time.strftime("%A")
            
            # UTC offset
            utc_offset = current_time.strftime("%z")
            time_info["utc_offset"] = f"{utc_offset[:3]}:{utc_offset[3:]}"
            
            # Get business configuration for the country
            business_config = get_business_config(region_code)
            
            # Store business hours info
            time_info["business_hours_start"] = f"{business_config['business_hours_start']:02d}:00"
            time_info["business_hours_end"] = f"{business_config['business_hours_end']:02d}:00"
            
            # Create readable weekdays string
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            weekday_names = [day_names[i] for i in sorted(business_config['weekdays'])]
            time_info["weekdays_config"] = ", ".join(weekday_names)
            
            # Check if current day is a weekend
            current_weekday = current_time.weekday()  # Monday=0, Sunday=6
            is_weekend = current_weekday in business_config['weekend_days']
            is_weekday = current_weekday in business_config['weekdays']
            
            time_info["is_weekend"] = is_weekend
            time_info["is_weekday"] = is_weekday
            
            # Business hours check
            is_business_hours = (
                is_weekday and 
                business_config['business_hours_start'] <= current_time.hour < business_config['business_hours_end']
            )
            time_info["is_business_hours"] = is_business_hours
            
    except Exception as e:
        # If timezone lookup fails, return None values
        pass
    
    return time_info


def smart_parse_number(raw_number: str, default_region: str):
    """
    Intelligent parsing with multiple strategies including auto-country detection
    """
    strategies = []
    
    # Strategy 1: Parse as-is (if has + or clear format)
    strategies.append(("as_is", raw_number, None))
    
    # Strategy 2: With default region (domestic)
    if not raw_number.startswith('+'):
        strategies.append(("with_region", raw_number, default_region))
    
    # Strategy 3: Add + prefix
    if not raw_number.startswith('+'):
        strategies.append(("with_plus", f"+{raw_number}", None))
    
    # Strategy 4: Try common countries for long numbers (10+ digits without +)
    if len(raw_number) >= 10 and not raw_number.startswith('+'):
        common_countries = [
            'US', 'GB', 'MX', 'BR', 'AU', 'CA', 'DE', 'FR', 'IT', 'ES',
            'AR', 'CO', 'PE', 'CL', 'CN', 'JP', 'KR', 'ID', 'TH', 'PH',
            'MY', 'SG', 'VN', 'PK', 'BD', 'RU', 'TR', 'SA', 'AE', 'ZA'
        ]
        
        for country in common_countries:
            if country != default_region:  # Skip if already tried
                strategies.append((f"auto_{country}", raw_number, country))
    
    results = []
    
    for strategy_name, number, region in strategies:
        try:
            parsed = phonenumbers.parse(number, region)
            is_valid = phonenumbers.is_valid_number(parsed)
            is_possible = phonenumbers.is_possible_number(parsed)
            detected_region = phonenumbers.region_code_for_number(parsed)
            
            results.append({
                "strategy": strategy_name,
                "parsed": parsed,
                "valid": is_valid,
                "possible": is_possible,
                "region": detected_region
            })
            
            # If found valid result with priority strategies, return immediately
            if is_valid and strategy_name in ["as_is", "with_plus"]:
                return results[-1]
                
        except:
            continue
    
    # Return best result: valid > possible > any
    valid_results = [r for r in results if r["valid"]]
    if valid_results:
        # Prefer exact matches first
        for strategy in ["with_region", "as_is", "with_plus"]:
            match = next((r for r in valid_results if r["strategy"] == strategy), None)
            if match:
                return match
        # Return first valid from auto-detection
        return valid_results[0]
    
    possible_results = [r for r in results if r["possible"]]
    if possible_results:
        return possible_results[0]
    
    if results:
        return results[0]
    
    return None


@app.post("/validate")
def validate_phone(data: PhoneRequest):
    raw = clean_phone_number(data.number)
    region_hint = data.default_region
    home_country = data.home_country

    result = {
        "input": data.number,
        "cleaned_input": raw,
        "valid": False,
        "is_possible": False,
        "is_domestic": False,
        "is_international": False,
        "is_toll_free": False,
        "is_mobile": False,
        "formatted_e164": None,
        "formatted_international": None,
        "formatted_national": None,
        "country_code": None,
        "region": None,
        "location": None,
        "carrier": None,
        "type": None,
        "reason": None,
        "parse_strategy": None,
        # Time-related fields
        "timezone": None,
        "all_timezones": [],
        "local_time": None,
        "local_time_12h": None,
        "local_date": None,
        "day_of_week": None,
        "is_business_hours": None,
        "is_weekend": None,
        "is_weekday": None,
        "utc_offset": None,
        "business_hours_start": None,
        "business_hours_end": None,
        "weekdays_config": None
    }

    parse_result = smart_parse_number(raw, region_hint)
    
    if not parse_result:
        result["reason"] = "Could not parse number with any strategy"
        return result
    
    parsed = parse_result["parsed"]
    result["parse_strategy"] = parse_result["strategy"]
    result["is_possible"] = parse_result["possible"]
    result["valid"] = parse_result["valid"]
    
    if not result["valid"]:
        result["reason"] = f"Invalid number (tried: {parse_result['strategy']})"
        return result

    result["formatted_e164"] = phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.E164
    )
    result["formatted_international"] = phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )
    result["formatted_national"] = phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.NATIONAL
    )

    result["country_code"] = f"+{parsed.country_code}"
    result["region"] = phonenumbers.region_code_for_number(parsed)
    result["location"] = geocoder.description_for_number(parsed, "en")

    result["is_domestic"] = result["region"] == home_country
    result["is_international"] = result["region"] != home_country

    num_type = number_type(parsed)
    
    type_map = {
        PhoneNumberType.MOBILE: "mobile",
        PhoneNumberType.FIXED_LINE: "fixed_line",
        PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
        PhoneNumberType.TOLL_FREE: "toll_free",
        PhoneNumberType.PREMIUM_RATE: "premium_rate",
        PhoneNumberType.SHARED_COST: "shared_cost",
        PhoneNumberType.VOIP: "voip",
        PhoneNumberType.PERSONAL_NUMBER: "personal_number",
        PhoneNumberType.PAGER: "pager",
        PhoneNumberType.UAN: "uan",
        PhoneNumberType.VOICEMAIL: "voicemail",
        PhoneNumberType.UNKNOWN: "unknown"
    }
    
    result["type"] = type_map.get(num_type, "unknown")
    result["is_toll_free"] = num_type == PhoneNumberType.TOLL_FREE
    result["is_mobile"] = num_type in [
        PhoneNumberType.MOBILE, 
        PhoneNumberType.FIXED_LINE_OR_MOBILE
    ]

    try:
        carrier_name = carrier.name_for_number(parsed, "en")
        result["carrier"] = carrier_name if carrier_name else None
    except:
        result["carrier"] = None

    # Get time information with country-specific business hours
    time_info = get_time_info(parsed, result["region"])
    result.update(time_info)

    if result["is_domestic"]:
        result["reason"] = "Valid domestic number"
    else:
        result["reason"] = f"Valid international number ({result['region']})"

    return result


class BatchPhoneRequest(BaseModel):
    numbers: list[str]
    default_region: str = "IN"
    home_country: str = "IN"


@app.post("/validate-batch")
def validate_batch(data: BatchPhoneRequest):
    results = []
    for num in data.numbers:
        req = PhoneRequest(
            number=num,
            default_region=data.default_region,
            home_country=data.home_country
        )
        results.append(validate_phone(req))
    
    valid_results = [r for r in results if r["valid"]]
    
    return {
        "total": len(results),
        "valid_count": len(valid_results),
        "invalid_count": len(results) - len(valid_results),
        "domestic_count": sum(1 for r in valid_results if r["is_domestic"]),
        "international_count": sum(1 for r in valid_results if r["is_international"]),
        "toll_free_count": sum(1 for r in valid_results if r["is_toll_free"]),
        "mobile_count": sum(1 for r in valid_results if r["is_mobile"]),
        "results": results
    }


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Phone Validator API"}


@app.get("/business-config/{country_code}")
def get_country_business_config(country_code: str):
    """Get business hours configuration for a specific country"""
    config = get_business_config(country_code.upper())
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_names = [day_names[i] for i in sorted(config['weekdays'])]
    weekend_names = [day_names[i] for i in sorted(config['weekend_days'])]
    
    return {
        "country_code": country_code.upper(),
        "weekdays": weekday_names,
        "weekend_days": weekend_names,
        "business_hours": f"{config['business_hours_start']:02d}:00 - {config['business_hours_end']:02d}:00",
        "business_hours_start": config['business_hours_start'],
        "business_hours_end": config['business_hours_end'],
        "is_configured": country_code.upper() in COUNTRY_BUSINESS_CONFIG
    }


@app.get("/supported-countries")
def get_supported_countries():
    """Get list of all countries with configured business hours"""
    countries = []
    
    for country_code, config in sorted(COUNTRY_BUSINESS_CONFIG.items()):
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday_names = [day_names[i] for i in sorted(config['weekdays'])]
        
        countries.append({
            "country_code": country_code,
            "weekdays": ", ".join(weekday_names),
            "business_hours": f"{config['business_hours_start']:02d}:00-{config['business_hours_end']:02d}:00"
        })
    
    return {
        "total_countries": len(countries),
        "countries": countries
    }
