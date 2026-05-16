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
    HEADERS = ["type", "title", "description", "notes", "colors", "variants", "weight", "price", "availability", "url"]

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
            data.get("availability", ""),
            data.get("url", ""),
        ]

        # URL is in column J — check if it already exists
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Materials!J:J"
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
                range=f"Materials!E{row_index}:J{row_index}",
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
                range="Materials!A:J",
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
    if "webbing" in t or "strap" in t or "ribbon" in t:
        return "Webbing"
    if "zipper" in t or "zip" in t or "slider" in t or "closure" in t:
        return "Zipper"
    if "buckle" in t or "hardware" in t or "clip" in t or "hook" in t:
        return "Hardware"
    if "lining" in t or "liner" in t or "taffeta" in t or "mesh" in t:
        return "Lining"
    if ("laminate" in t or "backpack" in t or "ecopak" in t
            or "ultra-tx" in t or "ultratx" in t or "dyneema" in t
            or "dcf" in t or "composite" in t or "ripstop" in t
            or "polyester" in t or "nylon" in t or "cordura" in t
            or "fabric" in t or "canvas" in t or "silpoly" in t
            or "silnylon" in t or "cuben" in t):
        return "Outer fabric"
    if "fleece" in t or "insul" in t or "primaloft" in t or "climashield" in t:
        return "Insulation"
    if "cord" in t or "rope" in t or "braid" in t:
        return "Cord"
    return "Fabric"


# ── EXTREMTEXTIL ──────────────────────────────────────────────────────────────

def clean_color_extremtextil(raw):
    raw = re.sub(r'\d+[,\.]\d+\s*EUR', '', raw)
    raw = re.sub(r'Deliverable.*', '', raw)
    raw = re.sub(r'Out of stock.*', '', raw)
    raw = re.sub(r'In stock.*', '', raw)
    raw = re.sub(r'Sold out.*', '', raw)
    raw = re.sub(r'Available.*', '', raw)
    return raw.strip()


def get_extremtextil_image(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        skip = ["footer", "project", "efre", "logo", "newsletter", "planer", "planner"]
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if "cstatic" in src and not any(s in src.lower() for s in skip):
                return src.split("?")[0]
    except Exception:
        pass
    return ""


def parse_extremtextil(url: str, soup: BeautifulSoup) -> dict:
    artikul = url.split("/")[-1]
    basis = artikul.split(".")[0]
    base = "https://www.extremtextil.de"

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
    availability = "Check website"

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
        if availability == "Check website":
            if "Sold out" in t and len(t) < 100:
                availability = "Sold out"
            elif "In stock" in t and len(t) < 50:
                availability = "In stock"
            elif "Out of stock" in t and len(t) < 50:
                availability = "Out of stock"

    colors_raw = []
    seen = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if basis in href and "/en/" in href:
            name = clean_color_extremtextil(a.text)
            if name and name not in seen:
                seen.append(name)
                full = base + href if href.startswith("/") else href
                colors_raw.append({"name": name, "url": full})

    colors_raw = [c for c in colors_raw if not any(w in c["name"] for w in ["sqm", "g/m", "mm", "®"])]

    colors = []
    for c in colors_raw:
        img = get_extremtextil_image(c["url"])
        colors.append({"name": c["name"], "url": c["url"], "image": img})

    return {
        "url": url,
        "source": "extremtextil.de",
        "type": guess_type(title),
        "title": title,
        "price": price,
        "weight": weight,
        "availability": availability,
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
            range="Materials!A:K"
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
