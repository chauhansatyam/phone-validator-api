from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import phonenumbers
from phonenumbers import geocoder, carrier, number_type, PhoneNumberType
import re

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PhoneRequest(BaseModel):
    number: str
    default_region: str = "IN"
    home_country: str = "IN"


def clean_phone_number(number: str) -> str:
    """Remove formatting but keep + prefix"""
    cleaned = re.sub(r'[\s\-\(\)\.]', '', number)
    return cleaned


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
        "parse_strategy": None
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
