from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import re
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

ALLOWED_DOMAINS = ["extremtextil.de", "adventurexpert.com"]
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SW_ACCESS_KEY = "SWSCRXNCU2Y4AHB0DZZGRVNFMG"
SW_API_URL = "https://shop.extremtextil.de/store-api/product"
SW_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Sw-Access-Key": SW_ACCESS_KEY,
    "Origin": "https://www.extremtextil.de",
    "Referer": "https://www.extremtextil.de/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}

_en_language_id = None


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────

def get_sheets_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
    if not creds_json:
        raise HTTPException(status_code=500, detail="Google credentials not configured")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(creds_json), scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def save_to_sheets(data: dict):
    COL_HEADERS = ["type", "title", "description", "notes", "colors", "variants", "weight", "price", "url"]
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()

        row_data = [
            data.get("type", ""),
            data.get("title", ""),
            data.get("description", ""),
            "",  # notes — col D, user fills manually
            json.dumps(data.get("colors", []), ensure_ascii=False),
            json.dumps(data.get("variants", []), ensure_ascii=False),
            data.get("weight", ""),
            data.get("price", ""),
            data.get("url", ""),
        ]

        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Materials!I:I"
        ).execute()
        existing_urls = result.get("values", [])

        row_index = None
        for i, row in enumerate(existing_urls):
            if row and row[0] == data["url"]:
                row_index = i + 1
                break

        if row_index:
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"Materials!A{row_index}:C{row_index}",
                valueInputOption="RAW",
                body={"values": [row_data[:3]]}
            ).execute()
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"Materials!E{row_index}:I{row_index}",
                valueInputOption="RAW",
                body={"values": [row_data[4:]]}
            ).execute()
        else:
            if not existing_urls:
                sheet.values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range="Materials!A1",
                    valueInputOption="RAW",
                    body={"values": [COL_HEADERS]}
                ).execute()
            sheet.values().append(
                spreadsheetId=SPREADSHEET_ID,
                range="Materials!A:I",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row_data]}
            ).execute()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sheets error: {e}")


# ── HELPERS ───────────────────────────────────────────────────────────────────

def guess_type(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["zipper", "zip", "slider", "closure", "vislon", "aquaguard", "coil"]):
        return "Zipper"
    if any(w in t for w in ["webbing", "strap", "ribbon", "binding", "edge", "tape"]):
        return "Webbing"
    if any(w in t for w in ["buckle", "hardware", "clip", "hook", "snap", "toggle", "loop", "ring", "cord lock", "stopper", "puller"]):
        return "Furniture"
    if any(w in t for w in ["foam", "evazote", "eva ", "padding"]):
        return "Foam"
    return "Fabric"


# ── EXTREMTEXTIL ──────────────────────────────────────────────────────────────

def get_english_language_id() -> str:
    global _en_language_id
    if _en_language_id:
        return _en_language_id
    try:
        resp = requests.post(
            "https://shop.extremtextil.de/store-api/language",
            json={"limit": 50},
            headers=SW_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        for lang in resp.json().get("elements", []):
            name = (lang.get("name") or "").lower()
            if "english" in name or name.startswith("en"):
                _en_language_id = lang["id"]
                return _en_language_id
    except Exception:
        pass
    return ""


def fetch_all_colors_via_api(basis: str) -> list:
    lang_id = get_english_language_id()
    headers = dict(SW_HEADERS)
    if lang_id:
        headers["sw-language-id"] = lang_id

    payload = {
        "filter": [{"type": "contains", "field": "productNumber", "value": f"{basis}."}],
        "associations": {
            "seoUrls": {},
            "options": {"associations": {"group": {}}},
            "cover": {"associations": {"media": {}}},
        },
        "limit": 100,
    }
    try:
        resp = requests.post(SW_API_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
    except Exception:
        return []

    colors = []
    for el in elements:
        product_number = el.get("productNumber", "")
        if "." not in product_number:
            continue  # skip base product

        # Color name
        options = el.get("options") or []
        color_name = ""
        if options:
            opt = options[0]
            color_name = (opt.get("translated") or {}).get("name") or opt.get("name", "")

        # Fallback: metaTitle "... in COLOR | extremtextil"
        if not color_name:
            meta_title = ((el.get("translated") or {}).get("metaTitle")
                          or el.get("metaTitle") or "")
            if " in " in meta_title:
                color_name = meta_title.split(" in ")[-1].replace(" | extremtextil", "").strip()

        # URL
        seo_urls = el.get("seoUrls") or []
        if seo_urls:
            color_url = f"https://www.extremtextil.de/en/{seo_urls[0].get('seoPathInfo', '')}"
        else:
            color_url = f"https://www.extremtextil.de/en/{basis}/{product_number}"

        # Image
        image_url = (((el.get("cover") or {}).get("media") or {}).get("url") or "").split("?")[0]

        # Availability
        availability = "In stock" if (el.get("availableStock") or 0) > 0 else "Out of stock"

        # Price
        unit_price = (el.get("calculatedPrice") or {}).get("unitPrice") or 0

        colors.append({
            "name": color_name,
            "url": color_url,
            "image": image_url,
            "availability": availability,
            "price_per_unit": unit_price,
        })

    return colors


def parse_extremtextil(url: str, soup: BeautifulSoup) -> dict:
    basis = url.split("/")[-1].split(".")[0]

    title = (soup.title.text.strip().replace(" | extremtextil", "") if soup.title else url)

    skip_words = [
        "Further links", "VAT", "prices", "cancellation", "Technical",
        "Informations", "unable", "orders", "enquiries",
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    desc = ""
    for p in soup.find_all("p"):
        t = p.text.strip()
        if (30 < len(t) < 400
                and not any(w in t for w in skip_words)
                and "shipping" not in t.lower()
                and basis not in t
                and not re.search(r'\d+g/(m|sqm|qm)', t)):
            desc = t
            break

    weight = ""
    for tag in soup.find_all("div"):
        t = tag.text.strip()
        if not weight and "Weight" in t and len(t) < 60:
            m = re.search(r'\d+[,\.]?\d*\s*g/\S+', t)
            if m:
                we
