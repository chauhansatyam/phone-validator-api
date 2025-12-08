from fastapi import FastAPI
from pydantic import BaseModel
import phonenumbers
from phonenumbers import geocoder, carrier, number_type, PhoneNumberType
import re

app = FastAPI()

class PhoneRequest(BaseModel):
    number: str
    default_region: str = "IN"
    home_country: str = "IN"


def clean_phone_number(number: str) -> str:
    """Remove formatting but keep + prefix"""
    # Remove spaces, dashes, parentheses, dots, but keep +
    cleaned = re.sub(r'[\s\-\(\)\.]', '', number)
    return cleaned


def smart_parse_number(raw_number: str, default_region: str):
    """
    Try multiple parsing strategies:
    1. Parse as-is (works if + prefix exists)
    2. Parse with default region (treats as domestic)
    3. Try adding + prefix (detects international without +)
    """
    strategies = [
        ("as_is", raw_number, None),
        ("with_region", raw_number, default_region),
        ("with_plus", f"+{raw_number}", None),
    ]
    
    results = []
    
    for strategy_name, number, region in strategies:
        try:
            parsed = phonenumbers.parse(number, region)
            is_valid = phonenumbers.is_valid_number(parsed)
            is_possible = phonenumbers.is_possible_number(parsed)
            
            results.append({
                "strategy": strategy_name,
                "parsed": parsed,
                "valid": is_valid,
                "possible": is_possible,
                "region": phonenumbers.region_code_for_number(parsed)
            })
        except:
            continue
    
    # Priority: valid > possible > any parse
    valid_results = [r for r in results if r["valid"]]
    if valid_results:
        # If multiple valid, prefer domestic first, then original format
        for strategy in ["with_region", "as_is", "with_plus"]:
            match = next((r for r in valid_results if r["strategy"] == strategy), None)
            if match:
                return match
    
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

    # Smart parsing
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

    # ===== FORMATTING =====
    result["formatted_e164"] = phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.E164
    )
    result["formatted_international"] = phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )
    result["formatted_national"] = phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.NATIONAL
    )

    # ===== COUNTRY INFO =====
    result["country_code"] = f"+{parsed.country_code}"
    result["region"] = phonenumbers.region_code_for_number(parsed)
    result["location"] = geocoder.description_for_number(parsed, "en")

    # ===== DOMESTIC vs INTERNATIONAL =====
    result["is_domestic"] = result["region"] == home_country
    result["is_international"] = result["region"] != home_country

    # ===== NUMBER TYPE =====
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

    # ===== CARRIER INFO =====
    try:
        carrier_name = carrier.name_for_number(parsed, "en")
        result["carrier"] = carrier_name if carrier_name else None
    except:
        result["carrier"] = None

    # Reason message
    if result["is_domestic"]:
        result["reason"] = "Valid domestic number"
    else:
        result["reason"] = f"Valid international number ({result['region']})"

    return result


# ===== BATCH VALIDATION =====
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


# ===== HEALTH CHECK =====
@app.get("/")
def health_check():
    return {"status": "ok", "service": "Phone Validator API"}

# from fastapi import FastAPI
# from pydantic import BaseModel
# import phonenumbers
# from phonenumbers import geocoder, carrier, number_type, PhoneNumberType
# import re

# app = FastAPI()

# class PhoneRequest(BaseModel):
#     number: str
#     default_region: str = "IN"  # Your home country
#     home_country: str = "IN"


# def clean_phone_number(number: str) -> str:
#     """Remove common formatting characters"""
#     # Remove spaces, dashes, parentheses, dots
#     cleaned = re.sub(r'[\s\-\(\)\.]', '', number)
#     return cleaned


# @app.post("/validate")
# def validate_phone(data: PhoneRequest):
#     raw = clean_phone_number(data.number)
#     region_hint = data.default_region
#     home_country = data.home_country

#     result = {
#         "input": data.number,
#         "cleaned_input": raw,
#         "valid": False,
#         "is_possible": False,
#         "is_domestic": False,
#         "is_international": False,
#         "is_toll_free": False,
#         "is_mobile": False,
#         "formatted_e164": None,
#         "formatted_international": None,
#         "formatted_national": None,
#         "country_code": None,
#         "region": None,
#         "location": None,
#         "carrier": None,
#         "type": None,
#         "reason": None,
#         "has_country_code": None
#     }

#     # Detect if country code was provided
#     result["has_country_code"] = raw.startswith('+')
    
#     # If no country code, explicitly note it's being treated as domestic
#     if not result["has_country_code"]:
#         result["reason"] = f"No country code detected - treating as {region_hint} number"

#     try:
#         # Parse number (without country code = domestic)
#         parsed = phonenumbers.parse(raw, region_hint)
        
#         # Check if possible
#         result["is_possible"] = phonenumbers.is_possible_number(parsed)
        
#         if not result["is_possible"]:
#             result["reason"] = "Number format not possible"
#             return result

#         # Check validity
#         result["valid"] = phonenumbers.is_valid_number(parsed)
        
#         if not result["valid"]:
#             result["reason"] = "Invalid number for the region"
#             return result

#         # ===== FORMATTING =====
#         result["formatted_e164"] = phonenumbers.format_number(
#             parsed, phonenumbers.PhoneNumberFormat.E164
#         )
#         result["formatted_international"] = phonenumbers.format_number(
#             parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
#         )
#         result["formatted_national"] = phonenumbers.format_number(
#             parsed, phonenumbers.PhoneNumberFormat.NATIONAL
#         )

#         # ===== COUNTRY INFO =====
#         result["country_code"] = f"+{parsed.country_code}"
#         result["region"] = phonenumbers.region_code_for_number(parsed)
#         result["location"] = geocoder.description_for_number(parsed, "en")

#         # ===== DOMESTIC vs INTERNATIONAL =====
#         result["is_domestic"] = result["region"] == home_country
#         result["is_international"] = result["region"] != home_country

#         # ===== NUMBER TYPE =====
#         num_type = number_type(parsed)
        
#         type_map = {
#             PhoneNumberType.MOBILE: "mobile",
#             PhoneNumberType.FIXED_LINE: "fixed_line",
#             PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
#             PhoneNumberType.TOLL_FREE: "toll_free",
#             PhoneNumberType.PREMIUM_RATE: "premium_rate",
#             PhoneNumberType.SHARED_COST: "shared_cost",
#             PhoneNumberType.VOIP: "voip",
#             PhoneNumberType.PERSONAL_NUMBER: "personal_number",
#             PhoneNumberType.PAGER: "pager",
#             PhoneNumberType.UAN: "uan",
#             PhoneNumberType.VOICEMAIL: "voicemail",
#             PhoneNumberType.UNKNOWN: "unknown"
#         }
        
#         result["type"] = type_map.get(num_type, "unknown")
#         result["is_toll_free"] = num_type == PhoneNumberType.TOLL_FREE
#         result["is_mobile"] = num_type in [
#             PhoneNumberType.MOBILE, 
#             PhoneNumberType.FIXED_LINE_OR_MOBILE
#         ]

#         # ===== CARRIER INFO =====
#         try:
#             carrier_name = carrier.name_for_number(parsed, "en")
#             result["carrier"] = carrier_name if carrier_name else None
#         except:
#             result["carrier"] = None

#         # Update reason for valid numbers
#         if result["has_country_code"]:
#             result["reason"] = "Valid"
#         else:
#             result["reason"] = f"Valid (treated as {region_hint} domestic number)"

#         return result

#     except phonenumbers.NumberParseException as e:
#         result["reason"] = f"Parse error: {str(e)}"
#         return result
#     except Exception as e:
#         result["reason"] = f"Unexpected error: {str(e)}"
#         return result


# # ===== BATCH VALIDATION =====
# class BatchPhoneRequest(BaseModel):
#     numbers: list[str]
#     default_region: str = "IN"
#     home_country: str = "IN"


# @app.post("/validate-batch")
# def validate_batch(data: BatchPhoneRequest):
#     results = []
#     for num in data.numbers:
#         req = PhoneRequest(
#             number=num,
#             default_region=data.default_region,
#             home_country=data.home_country
#         )
#         results.append(validate_phone(req))
    
#     # Summary stats
#     valid_results = [r for r in results if r["valid"]]
    
#     return {
#         "total": len(results),
#         "valid_count": len(valid_results),
#         "invalid_count": len(results) - len(valid_results),
#         "domestic_count": sum(1 for r in valid_results if r["is_domestic"]),
#         "international_count": sum(1 for r in valid_results if r["is_international"]),
#         "toll_free_count": sum(1 for r in valid_results if r["is_toll_free"]),
#         "mobile_count": sum(1 for r in valid_results if r["is_mobile"]),
#         "results": results
#     }


# from fastapi import FastAPI
# from pydantic import BaseModel
# import phonenumbers
# from phonenumbers import geocoder, carrier, number_type, PhoneNumberType

# app = FastAPI()

# class PhoneRequest(BaseModel):
#     number: str
#     default_region: str | None = None


# @app.post("/validate")
# def validate_phone(data: PhoneRequest):

#     raw = data.number.strip()
#     region_hint = data.default_region

#     try:
#         # Parse number (with or without country code)
#         parsed = phonenumbers.parse(raw, region_hint)

#     except Exception as e:
#         return {
#             "input": raw,
#             "valid": False,
#             "reason": "Parsing failed",
#             "details": str(e)
#         }

#     # Check validity
#     valid = phonenumbers.is_valid_number(parsed)

#     if not valid:
#         return {
#             "input": raw,
#             "valid": False,
#             "reason": "Invalid number for that country",
#             "formatted_e164": None,
#             "region": None,
#             "type": None
#         }

#     # Format to E.164
#     e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

#     # Region (country)
#     region = geocoder.region_code_for_number(parsed)

#     # Carrier & Type
#     num_type = number_type(parsed)

#     type_map = {
#         PhoneNumberType.MOBILE: "mobile",
#         PhoneNumberType.FIXED_LINE: "fixed_line",
#         PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
#         PhoneNumberType.TOLL_FREE: "toll_free",
#         PhoneNumberType.PREMIUM_RATE: "premium_rate",
#         PhoneNumberType.SHARED_COST: "shared_cost",
#         PhoneNumberType.VOIP: "voip",
#         PhoneNumberType.PERSONAL_NUMBER: "personal_number",
#         PhoneNumberType.PAGER: "pager",
#         PhoneNumberType.UAN: "uan",
#         PhoneNumberType.VOICEMAIL: "voicemail",
#         PhoneNumberType.UNKNOWN: "unknown"
#     }

#     return {
#         "input": raw,
#         "valid": True,
#         "formatted_e164": e164,
#         "region": region,
#         "type": type_map.get(num_type, "unknown")
#     }



# main.py



# from fastapi import FastAPI
# from pydantic import BaseModel
# import re
# import phonenumbers
# from phonenumbers import NumberParseException, PhoneNumberFormat, geocoder, carrier, number_type, PhoneNumberType

# app = FastAPI(title="Phone Validation API")

# class PhoneRequest(BaseModel):
#     number: str
#     default_region: str | None = None  # optional 2-letter ISO region code like "IN", "US", "GB"

# def clean_input(s: str) -> str:
#     """Remove extension markers and keep only leading + and digits."""
#     if not s:
#         return ''
#     # remove common extension patterns
#     s = re.sub(r'(?i)\s*(ext|x|extension)\.?[:\s]*\d+$', '', s).strip()
#     # keep only leading + and digits
#     # if there are other + signs/characters, collapse to a single leading + if present
#     s = s.strip()
#     leading_plus = s.startswith('+')
#     digits = ''.join(ch for ch in s if ch.isdigit())
#     return ('+' + digits) if leading_plus else digits

# def map_number_type(nt):
#     m = {
#         PhoneNumberType.MOBILE: "mobile",
#         PhoneNumberType.FIXED_LINE: "fixed_line",
#         PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
#         PhoneNumberType.TOLL_FREE: "toll_free",
#         PhoneNumberType.PREMIUM_RATE: "premium_rate",
#         PhoneNumberType.SHARED_COST: "shared_cost",
#         PhoneNumberType.VOIP: "voip",
#         PhoneNumberType.PERSONAL_NUMBER: "personal",
#         PhoneNumberType.PAGER: "pager",
#         PhoneNumberType.UAN: "uan",
#         PhoneNumberType.VOICEMAIL: "voicemail",
#         PhoneNumberType.UNKNOWN: "unknown"
#     }
#     return m.get(nt, "unknown")

# @app.post("/validate")
# def validate_phone(req: PhoneRequest):
#     raw = req.number
#     default_region = (req.default_region or '').upper() if req.default_region else None

#     cleaned = clean_input(raw)
#     digits_only = re.sub(r'\D', '', cleaned)
#     digit_count = len(digits_only)

#     response = {
#         "input": raw,
#         "cleaned": cleaned,
#         "digits": digit_count,
#         "valid": False,
#         "formatted_e164": None,
#         "region": None,
#         "type": None,
#         "possible": False,
#         "error": None,
#         "reason": None
#     }

#     # Quick length checks (E.164 allows up to 15 digits total)
#     if digit_count == 0:
#         response["error"] = "no digits found"
#         response["reason"] = "empty input after cleaning"
#         return response

#     if digit_count > 15:
#         response["error"] = "too_many_digits"
#         response["reason"] = f"digit count {digit_count} > 15 (E.164 max)"
#         return response

#     if digit_count < 6:
#         response["error"] = "too_few_digits"
#         response["reason"] = f"digit count {digit_count} < 6 (very unlikely valid phone)"
#         return response

#     # Try parsing with phonenumbers
#     parsed = None
#     last_exception = None
#     try:
#         if cleaned.startswith('+'):
#             # international parse
#             parsed = phonenumbers.parse(cleaned, None)
#         else:
#             # if user provided a default region, use it
#             if default_region and default_region != 'ZZ':
#                 parsed = phonenumbers.parse(cleaned, default_region)
#             else:
#                 # try adding + and parse internationally
#                 try:
#                     parsed = phonenumbers.parse('+' + digits_only, None)
#                 except NumberParseException:
#                     # fallback: try parse without region (may fail)
#                     parsed = phonenumbers.parse(cleaned, None)
#     except NumberParseException as e:
#         last_exception = e

#     if parsed is None:
#         response["error"] = "parse_failure"
#         response["reason"] = str(last_exception) if last_exception else "unknown parse failure"
#         return response

#     # is_possible_number (rough) and is_valid_number (more strict)
#     try:
#         response["possible"] = phonenumbers.is_possible_number(parsed)
#     except Exception:
#         response["possible"] = False

#     try:
#         is_valid = phonenumbers.is_valid_number(parsed)
#     except Exception as e:
#         response["error"] = "validation_error"
#         response["reason"] = str(e)
#         return response

#     if not is_valid:
#         response["valid"] = False
#         response["reason"] = "parsed but not valid for region"
#         # still return what we parsed (optional)
#         try:
#             response["formatted_e164"] = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
#             response["region"] = geocoder.region_code_for_number(parsed)
#         except Exception:
#             pass
#         return response

#     # Valid number
#     response["valid"] = True
#     response["formatted_e164"] = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
#     response["region"] = geocoder.region_code_for_number(parsed)
#     try:
#         t = number_type(parsed)
#         response["type"] = map_number_type(t)
#     except Exception:
#         response["type"] = None

#     response["reason"] = "valid per phonenumbers"
#     return response

