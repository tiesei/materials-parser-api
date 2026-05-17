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


class ParseRequest(BaseModel):
    url: str


class ProductsUpdateRequest(BaseModel):
    products: list
    headers: list = []


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
            meta_title = (
                (el.get("translated") or {}).get("metaTitle")
                or el.get("metaTitle") or ""
            )
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

        # Price per variant
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

    title = soup.title.text.strip().replace(" | extremtextil", "") if soup.title else url

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
                weight = m.group()
                break

    price = ""
    for tag in soup.find_all(["span", "div", "p"]):
        t = tag.text.strip()
        if not price and len(t) < 30:
            m = re.search(r'\d+[,\.]\d+\s*EUR', t)
            if m:
                price = m.group()
                break

    colors = fetch_all_colors_via_api(basis)

    if colors and not price and colors[0].get("price_per_unit"):
        price = f"{colors[0]['price_per_unit']:.2f} EUR".replace(".", ",")

    return {
        "url": url,
        "source": "extremtextil.de",
        "type": guess_type(title),
        "title": title,
        "price": price,
        "weight": weight,
        "description": desc,
        "colors": colors,
        "variants": [],
    }


# ── ADVENTUREXPERT ────────────────────────────────────────────────────────────

def parse_adventurexpert(url: str, soup: BeautifulSoup) -> dict:
    title = (soup.title.text.strip()
             .replace(" - Adventurexpert", "")
             .replace(" – Adventurexpert", "")
             if soup.title else url)

    price = ""
    price_tag = soup.find("p", class_="price") or soup.find("span", class_="woocommerce-Price-amount")
    if price_tag:
        m = re.search(r'[\d,\.]+\s*€', price_tag.get_text(strip=True))
        if m:
            price = m.group().replace("\xa0", "").strip()

    desc = ""
    desc_div = (soup.find("div", class_="woocommerce-product-details__short-description")
                or soup.find("div", id="tab-description"))
    if desc_div:
        for p in desc_div.find_all("p"):
            t = p.get_text(strip=True)
            if 10 < len(t) < 400:
                desc = t
                break

    weight = ""
    m = re.search(r'Weight[:\s]+(\d+[\d,\.]*\s*g(?:/\S+)?)', soup.get_text())
    if m:
        weight = m.group(1).strip()

    availability = "Check website"
    stock_tag = soup.find("p", class_="stock")
    if stock_tag:
        t = stock_tag.get_text(strip=True).lower()
        availability = "Out of stock" if "out of stock" in t else "In stock"
    elif soup.find("button", class_="single_add_to_cart_button"):
        availability = "In stock"

    variants = []
    for select in soup.find_all("select", attrs={"name": re.compile(r"attribute_")}):
        label_tag = select.find_previous("label")
        attr_name = (
            label_tag.get_text(strip=True) if label_tag
            else select.get("name", "")
                .replace("attribute_pa_", "")
                .replace("attribute_", "")
                .capitalize()
        )
        options = [
            opt.get_text(strip=True) for opt in select.find_all("option")
            if opt.get_text(strip=True).lower() not in ["choose an option", "select"]
        ]
        if options:
            variants.append({"attribute": attr_name, "options": options})

    images = []
    gallery = soup.find("div", class_="woocommerce-product-gallery")
    if gallery:
        for a in gallery.find_all("a", href=True):
            if re.search(r'\.(jpg|jpeg|png|webp)', a["href"], re.I) and a["href"] not in images:
                images.append(a["href"])
    if not images:
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            images.append(og["content"])

    if variants:
        colors = [
            {
                "name": opt,
                "url": url,
                "image": images[i] if i < len(images) else (images[0] if images else ""),
                "attribute": variants[0]["attribute"],
            }
            for i, opt in enumerate(variants[0]["options"])
        ]
    else:
        colors = [{"name": "Default", "url": url, "image": images[0] if images else ""}]

    return {
        "url": url,
        "source": "adventurexpert.com",
        "type": guess_type(title),
        "title": title,
        "price": price,
        "weight": weight,
        "availability": availability,
        "description": desc,
        "colors": colors,
        "variants": variants,
    }


# ── ROUTER ────────────────────────────────────────────────────────────────────

def parse_page(url: str) -> dict:
    if not any(domain in url for domain in ALLOWED_DOMAINS):
        raise HTTPException(status_code=400, detail=f"Supported sites: {', '.join(ALLOWED_DOMAINS)}")
    try:
        resp = requests.get(url, headers=FETCH_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e}")

    soup = BeautifulSoup(resp.text, "html.parser")

    if "extremtextil.de" in url:
        return parse_extremtextil(url, soup)
    elif "adventurexpert.com" in url:
        return parse_adventurexpert(url, soup)


# ── ENDPOINTS ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "Materials parser API", "supported": ALLOWED_DOMAINS}


@app.post("/parse")
def parse(req: ParseRequest):
    data = parse_page(req.url)
    save_to_sheets(data)
    return data


@app.get("/materials")
def get_materials():
    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Materials!A:I"
        ).execute()
        rows = result.get("values", [])
        if len(rows) < 2:
            return []
        headers = rows[0]
        materials = []
        for row in rows[1:]:
            while len(row) < len(headers):
                row.append("")
            item = dict(zip(headers, row))
            for field in ["colors", "variants"]:
                try:
                    item[field] = json.loads(item.get(field, "[]"))
                except Exception:
                    item[field] = []
            materials.append(item)
        return materials
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sheets error: {e}")


@app.get("/products")
def get_products():
    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Products!A:Z"
        ).execute()
        rows = result.get("values", [])
        if len(rows) < 2:
            return {"headers": [], "products": []}
        headers = rows[0]
        products = []
        for row in rows[1:]:
            while len(row) < len(headers):
                row.append("")
            products.append(dict(zip(headers, row)))
        return {"headers": headers, "products": products}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sheets error: {e}")


@app.post("/products")
def save_products(req: ProductsUpdateRequest):
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()

        if req.headers:
            header_row = req.headers
        else:
            result = sheet.values().get(
                spreadsheetId=SPREADSHEET_ID,
                range="Products!A1:Z1"
            ).execute()
            header_row = result.get("values", [[]])[0]
            if not header_row:
                raise HTTPException(status_code=400, detail="No headers in Products sheet")

        rows = [header_row] + [
            [str(product.get(h, "")) for h in header_row]
            for product in req.products
        ]

        sheet.values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range="Products!A:Z"
        ).execute()
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range="Products!A1",
            valueInputOption="RAW",
            body={"values": rows}
        ).execute()

        return {"status": "ok", "saved": len(req.products)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sheets error: {e}")
