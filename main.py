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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

ALLOWED_DOMAINS = ["extremtextil.de", "adventurexpert.com"]
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheets_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
    if not creds_json:
        raise HTTPException(status_code=500, detail="Google credentials not configured")
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def save_to_sheets(data: dict):
    # Column order: type, title, description, notes(D), colors, variants, weight, price, availability, url(J)
    HEADERS = ["type", "title", "description", "notes", "colors", "variants", "weight", "price", "url"]

    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()

        colors_json = json.dumps(data.get("colors", []), ensure_ascii=False)
        variants_json = json.dumps(data.get("variants", []), ensure_ascii=False)

        row_data = [
            data.get("type", ""),
            data.get("title", ""),
            data.get("description", ""),
            "",  # notes — col D, user fills manually
            colors_json,
            variants_json,
            data.get("weight", ""),
            data.get("price", ""),
            data.get("url", ""),
        ]

        # URL is in column I — check if it already exists
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
            # Update cols A-C (skip notes in D), then E-J
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
            # Add header if sheet is empty
            if not existing_urls:
                sheet.values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range="Materials!A1",
                    valueInputOption="RAW",
                    body={"values": [HEADERS]}
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


class ParseRequest(BaseModel):
    url: str


def guess_type(title):
    t = title.lower()
    if ("zipper" in t or "zip" in t or "slider" in t or "closure" in t
            or "vislon" in t or "aquaguard" in t or "coil" in t):
        return "Zipper"
    if ("webbing" in t or "strap" in t or "ribbon" in t
            or "binding" in t or "edge" in t or "tape" in t):
        return "Webbing"
    if ("buckle" in t or "hardware" in t or "clip" in t or "hook" in t
            or "snap" in t or "toggle" in t or "loop" in t or "ring" in t
            or "cord lock" in t or "stopper" in t or "puller" in t):
        return "Furniture"
    if "foam" in t or "evazote" in t or "eva " in t or "padding" in t:
        return "Foam"
    return "Fabric"


# ── EXTREMTEXTIL ──────────────────────────────────────────────────────────────

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


def fetch_all_colors_via_api(basis: str) -> list:
    """Fetch all color variants via Shopware Store API — one request, all colors."""
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
        resp = requests.post(SW_API_URL, json=payload, headers=SW_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        elements = data.get("elements", [])
    except Exception as e:
        return []

    colors = []
    base_url = "https://www.extremtextil.de/en/"

    for el in elements:
        # Color name — extract from metaTitle "... in COLOR | extremtextil"
        options = el.get("options") or []
        color_name = ""
        # Try metaTitle first: "Product name in bottle green | extremtextil"
        meta_title = (el.get("translated") or {}).get("metaTitle") or el.get("metaTitle") or ""
        print(f"DEBUG metaTitle: {meta_title!r}")
        if meta_title and " in " in meta_title:
            part = meta_title.split(" in ")[-1]
            color_name = part.replace(" | extremtextil", "").strip()
        # Fallback to options translated name
        if not color_name and options:
            opt = options[0]
            translated_opt = opt.get("translated") or {}
            color_name = translated_opt.get("name") or opt.get("name", "")
            print(f"DEBUG fallback color_name: {color_name!r}")

        # Product URL via seoUrls
        seo_urls = el.get("seoUrls") or []
        if seo_urls:
            seo_path = seo_urls[0].get("seoPathInfo", "")
            color_url = f"https://www.extremtextil.de/en/{seo_path}"
        else:
            product_number = el.get("productNumber", "")
            color_url = f"https://www.extremtextil.de/en/{basis}/{product_number}"

        # Image from cover
        cover = el.get("cover") or {}
        media = cover.get("media") or {}
        image_url = media.get("url", "")
        if image_url and "?" in image_url:
            image_url = image_url.split("?")[0]

        # Availability
        stock = el.get("availableStock", 0) or 0
        available = el.get("available", False)
        restock_time = el.get("restockTime")
        delivery_time = (el.get("deliveryTime") or {}).get("translated", {}).get("name", "")

        if stock > 0:
            availability = "In stock"
        else:
            availability = "Out of stock"

        # Price
        calc_price = el.get("calculatedPrice") or {}
        unit_price = calc_price.get("unitPrice", 0)

        colors.append({
            "name": color_name,
            "url": color_url,
            "image": image_url,
            "availability": availability,
            "price_per_unit": unit_price,
        })

    return colors


def parse_extremtextil(url: str, soup: BeautifulSoup) -> dict:
    artikul = url.split("/")[-1]
    basis = artikul.split(".")[0]

    title_tag = soup.title
    title = title_tag.text.strip().replace(" | extremtextil", "") if title_tag else url

    skip_words = [
        "Further links", "VAT", "prices", "cancellation",
        "Technical", "Informations", "unable", "orders",
        "enquiries", "May", "January", "February", "March",
        "April", "June", "July", "August", "September",
        "October", "November", "December"
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
    price = ""
    for tag in soup.find_all("div"):
        t = tag.text.strip()
        if not weight and re.search(r'Weight', t) and re.search(r'\d+[,\.]?\d*\s*g/', t) and len(t) < 60:
            match = re.search(r'\d+[,\.]?\d*\s*g/\S+', t)
            if match:
                weight = match.group()

    for tag in soup.find_all(["span", "div", "p"]):
        t = tag.text.strip()
        if not price and re.search(r'\d+[,\.]\d+\s*EUR', t) and len(t) < 30:
            price = re.search(r'\d+[,\.]\d+\s*EUR', t).group()

    # Fetch ALL colors via Shopware API — one request, no limit
    colors = fetch_all_colors_via_api(basis)

    # Fallback: if API returned nothing, price from first color
    if colors and not price and colors[0].get("price_per_unit"):
        p = colors[0]["price_per_unit"]
        price = f"{p:.2f} EUR".replace(".", ",")

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
    title_tag = soup.title
    title = title_tag.text.strip().replace(" - Adventurexpert", "").replace(" – Adventurexpert", "") if title_tag else url

    price = ""
    price_tag = soup.find("p", class_="price")
    if not price_tag:
        price_tag = soup.find("span", class_="woocommerce-Price-amount")
    if price_tag:
        price_text = price_tag.get_text(strip=True)
        match = re.search(r'[\d,\.]+\s*€', price_text)
        if match:
            price = match.group().replace("\xa0", "").strip()

    desc = ""
    desc_div = soup.find("div", class_="woocommerce-product-details__short-description")
    if not desc_div:
        desc_div = soup.find("div", id="tab-description")
    if desc_div:
        for p in desc_div.find_all("p"):
            t = p.get_text(strip=True)
            if 10 < len(t) < 400:
                desc = t
                break

    weight = ""
    full_text = soup.get_text()
    weight_match = re.search(r'Weight[:\s]+(\d+[\d,\.]*\s*g(?:/\S+)?)', full_text)
    if weight_match:
        weight = weight_match.group(1).strip()

    availability = "Check website"
    stock_tag = soup.find("p", class_="stock")
    if stock_tag:
        t = stock_tag.get_text(strip=True).lower()
        if "out of stock" in t:
            availability = "Out of stock"
        elif "in stock" in t:
            availability = "In stock"
    else:
        if soup.find("button", class_="single_add_to_cart_button"):
            availability = "In stock"

    variants = []
    for select in soup.find_all("select", attrs={"name": re.compile(r"attribute_")}):
        label_tag = select.find_previous("label")
        attr_name = (
            label_tag.get_text(strip=True) if label_tag
            else select.get("name", "").replace("attribute_pa_", "").replace("attribute_", "").capitalize()
        )
        options = []
        for opt in select.find_all("option"):
            val = opt.get_text(strip=True)
            if val and val.lower() not in ["choose an option", "select"]:
                options.append(val)
        if options:
            variants.append({"attribute": attr_name, "options": options})

    images = []
    gallery = soup.find("div", class_="woocommerce-product-gallery")
    if gallery:
        for a in gallery.find_all("a", href=True):
            href = a["href"]
            if re.search(r'\.(jpg|jpeg|png|webp)', href, re.I):
                if href not in images:
                    images.append(href)
    if not images:
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            images.append(og["content"])

    colors = []
    if variants:
        first_attr = variants[0]
        for i, opt in enumerate(first_attr["options"]):
            img = images[i] if i < len(images) else (images[0] if images else "")
            colors.append({
                "name": opt,
                "url": url,
                "image": img,
                "attribute": first_attr["attribute"]
            })
    else:
        colors.append({
            "name": "Default",
            "url": url,
            "image": images[0] if images else ""
        })

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
        raise HTTPException(
            status_code=400,
            detail=f"Supported sites: {', '.join(ALLOWED_DOMAINS)}"
        )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
    """Parse and save to Google Sheets. Works for add and reparse."""
    data = parse_page(req.url)
    save_to_sheets(data)
    return data


@app.get("/materials")
def get_materials():
    """Read all materials from Google Sheets."""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Materials!A:I"
        ).execute()
        rows = result.get("values", [])
        if len(rows) < 2:
            return []
        headers = rows[0]
        materials = []
        for row in rows[1:]:
            # Pad row to header length
            while len(row) < len(headers):
                row.append("")
            item = dict(zip(headers, row))
            # Parse JSON fields
            try:
                item["colors"] = json.loads(item.get("colors", "[]"))
            except Exception:
                item["colors"] = []
            try:
                item["variants"] = json.loads(item.get("variants", "[]"))
            except Exception:
                item["variants"] = []
            materials.append(item)
        return materials
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sheets error: {e}")


@app.get("/products")
def get_products():
    """Read all products from Google Sheets. Headers are dynamic — any columns work."""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(
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


class ProductsUpdateRequest(BaseModel):
    products: list
    headers: list = []


@app.post("/products")
def save_products(req: ProductsUpdateRequest):
    """Save all products + headers back to Google Sheets."""
    try:
        service = get_sheets_service()
        sheet = service.spreadsheets()

        # Use headers from request if provided, else read from sheet
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

        # Build rows
        rows = [header_row]
        for product in req.products:
            row = [str(product.get(h, "")) for h in header_row]
            rows.append(row)

        # Clear and rewrite
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
