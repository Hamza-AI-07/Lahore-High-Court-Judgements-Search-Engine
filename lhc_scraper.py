import os
import re
import time
import csv
import argparse
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://data.lhc.gov.pk"
LIST_URL = f"{BASE}/reported_judgments/judgments_approved_for_reporting"
FORMER_URL = f"{BASE}/reported_judgments/judgments_approved_for_reporting_by_former_judges"

def build_session(proxy):
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LHC-Scraper/1.0"})
    retry = Retry(total=6, connect=6, read=6, backoff_factor=0.7, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    if proxy:
        s.proxies.update({"http": proxy, "https": proxy})
    return s

def get_soup(session, url, timeout):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def safe_text(node):
    return (node.get_text(strip=True) if node else "").strip()

def slugify(s, max_len=80):
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:max_len] or "untitled"

def is_pdf_href(href):
    return href and href.lower().endswith(".pdf")

def absolute(href):
    return urljoin(BASE, href)

def normalize_pdf_url(url):
    parsed = urlparse(url)
    if parsed.netloc.lower() == "sys.lhc.gov.pk" and parsed.scheme.lower() == "https":
        return parsed._replace(scheme="http").geturl()
    return url

def verify_url_exists(session, url, timeout):
    u1 = normalize_pdf_url(url)
    try:
        r = session.head(u1, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and ("application/pdf" in r.headers.get("Content-Type", "").lower() or u1.lower().endswith(".pdf")):
            return True
    except Exception:
        pass
    try:
        r = session.get(u1, timeout=timeout, stream=True)
        ct = r.headers.get("Content-Type", "").lower()
        if r.status_code == 200 and ("application/pdf" in ct or u1.lower().endswith(".pdf")):
            return True
    except Exception:
        pass
    p = urlparse(u1)
    alt = p._replace(scheme=("http" if p.scheme == "https" else "https")).geturl()
    if alt != u1:
        try:
            r = session.head(alt, timeout=timeout, allow_redirects=True)
            if r.status_code == 200 and ("application/pdf" in r.headers.get("Content-Type", "").lower() or alt.lower().endswith(".pdf")):
                return True
        except Exception:
            pass
        try:
            r = session.get(alt, timeout=timeout, stream=True)
            ct = r.headers.get("Content-Type", "").lower()
            if r.status_code == 200 and ("application/pdf" in ct or alt.lower().endswith(".pdf")):
                return True
        except Exception:
            pass
    return False

def extract_items_from_list(soup):
    items = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        text = safe_text(a)
        full = absolute(href)
        if is_pdf_href(href) and ("appjudgments" in href or urlparse(full).netloc.endswith("sys.lhc.gov.pk")):
            items.append({"detail_url": None, "pdf_url": full, "title": text})
        elif "/reported_judgments/" in href and "judgments_approved_for_reporting" not in href:
            items.append({"detail_url": full, "pdf_url": None, "title": text})
    return items

def extract_items_from_listing_table(soup):
    items = []
    rows = soup.select("table tbody tr")
    for tr in rows:
        tds = tr.find_all("td")
        if not tds:
            continue
        title = safe_text(tds[2]) if len(tds) >= 3 else ""
        pdf_link = None
        detail_link = None
        for a in tr.select("a[href]"):
            href = a.get("href")
            if not href:
                continue
            if is_pdf_href(href):
                pdf_link = absolute(href)
            elif "/reported_judgments/" in href and "judgments_approved_for_reporting" not in href:
                detail_link = absolute(href)
        items.append({"title": title, "pdf_url": pdf_link, "detail_url": detail_link})
    return items

def find_next_page(soup, current_url):
    a = soup.select_one('a[rel="next"]')
    if a and a.get('href'):
        return absolute(a.get('href'))
    for link in soup.select('a[href]'):
        text = safe_text(link).lower()
        href = link.get('href')
        if not href:
            continue
        if 'next' in text or '›' in text or '»' in text:
            return absolute(href)
    return None

def find_next_page(soup, current_url):
    for a in soup.select("a[href]"):
        t = safe_text(a).lower()
        href = a.get("href")
        if not href:
            continue
        if a.get("rel") == ["next"] or t == "next" or t == "›" or "page=" in href:
            candidate = absolute(href)
            if urlparse(candidate).path.startswith(urlparse(current_url).path):
                return candidate
    return None

def extract_metadata_from_detail(soup, page_url):
    title = ""
    judge = ""
    case_no = ""
    decision_date = ""
    uploaded_date = ""
    text = soup.get_text(" ", strip=True)
    m = re.search(r"by\s+(Mr\.|Justice|Hon'?ble)[^,]+", text, flags=re.I)
    if m:
        judge = m.group(0)
    m = re.search(r"(Case\s*#|Case No\.?)\s*[:\-]?\s*([^\s,;]+)", text, flags=re.I)
    if m:
        case_no = m.group(2)
    m = re.search(r"Decision Date\s*[:\-]?\s*([0-9]{2}\-[0-9]{2}\-[0-9]{4})", text, flags=re.I)
    if m:
        decision_date = m.group(1)
    m = re.search(r"uploaded on:\s*([0-9]{2}\-[0-9]{2}\-[0-9]{4})", text, flags=re.I)
    if m:
        uploaded_date = m.group(1)
    h1 = soup.select_one("h1, h2, .page-title, .title")
    if h1:
        title = safe_text(h1)
    if not title:
        title = slugify(urlparse(page_url).path.split("/")[-1])
    return {"Title": title, "Judge": judge, "CaseNo": case_no, "DecisionDate": decision_date, "UploadedDate": uploaded_date, "DetailURL": page_url}

def find_pdf_in_detail(soup):
    for a in soup.select("a[href]"):
        href = a.get("href")
        if is_pdf_href(href):
            return absolute(href)
    for a in soup.select("a[href*='/files/'], a[href*='sites/default/files']"):
        href = a.get("href")
        if href and ".pdf" in href.lower():
            return absolute(href)
    return None

def download_pdf(session, url, name_hint, index, pdf_dir, timeout):
    fname = f"{index:04d}_{slugify(name_hint)}.pdf"
    path = os.path.join(pdf_dir, fname)
    if os.path.exists(path):
        return path
    url1 = normalize_pdf_url(url)
    try:
        r = session.get(url1, timeout=timeout)
        r.raise_for_status()
    except requests.exceptions.SSLError:
        p = urlparse(url1)
        alt = p._replace(scheme=("http" if p.scheme == "https" else "https")).geturl()
        r = session.get(alt, timeout=timeout)
        r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    return path

def load_existing(csv_path):
    if not os.path.exists(csv_path):
        return []
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows

def save_rows(csv_path, rows):
    fieldnames = ["Title", "Date", "Judge", "PDF Link", "DetailURL"]
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            w.writeheader()
        for r in rows:
            w.writerow(r)

def scrape(target, out_csv, pdf_dir, sleep_sec, proxy, connect_timeout, read_timeout, skip_download=False, verify_links=False):
    os.makedirs(pdf_dir, exist_ok=True)
    session = build_session(proxy)
    timeout = (connect_timeout, read_timeout)
    existing = load_existing(out_csv)
    seen_pdf = set(r.get("PDF Link", "") for r in existing if r.get("PDF Link"))
    seen_detail = set(r.get("DetailURL", "") for r in existing if r.get("DetailURL"))
    count = len(existing)
    batch = []
    sources = [LIST_URL, FORMER_URL]
    for src in sources:
        page_idx = 0
        while count < target:
            page_url = f"{src}?page={page_idx}"
            soup = get_soup(session, page_url, timeout)
            items = extract_items_from_list(soup)
            if not items:
                break
            for item in items:
                if count >= target:
                    break
                pdf_url = item["pdf_url"]
                meta = {"Title": item.get("title") or "", "Date": "", "Judge": "", "PDF Link": "", "DetailURL": item.get("detail_url") or ""}
                if pdf_url and pdf_url not in seen_pdf:
                    if skip_download:
                        if not verify_links or verify_url_exists(session, pdf_url, timeout):
                            meta["PDF Link"] = pdf_url
                            batch.append(meta)
                            seen_pdf.add(pdf_url)
                            count += 1
                        time.sleep(sleep_sec)
                        continue
                    else:
                        pdf_path = download_pdf(session, pdf_url, meta["Title"] or f"doc_{count+1}", count+1, pdf_dir, timeout)
                        meta["PDF Link"] = pdf_url
                    batch.append(meta)
                    seen_pdf.add(pdf_url)
                    count += 1
                    time.sleep(sleep_sec)
                    continue
                detail_url = item["detail_url"]
                if detail_url and detail_url not in seen_detail:
                    dsoup = get_soup(session, detail_url, timeout)
                    dmeta = extract_metadata_from_detail(dsoup, detail_url)
                    meta["Title"] = dmeta.get("Title", meta["Title"])
                    meta["Judge"] = dmeta.get("Judge", "")
                    meta["Date"] = dmeta.get("DecisionDate", dmeta.get("UploadedDate", ""))
                    meta["DetailURL"] = detail_url
                    pdf_in_detail = find_pdf_in_detail(dsoup)
                    if pdf_in_detail and pdf_in_detail not in seen_pdf:
                        if skip_download:
                            if not verify_links or verify_url_exists(session, pdf_in_detail, timeout):
                                meta["PDF Link"] = pdf_in_detail
                                batch.append(meta)
                                seen_pdf.add(pdf_in_detail)
                                count += 1
                        else:
                            pdf_path = download_pdf(session, pdf_in_detail, meta["Title"] or f"doc_{count+1}", count+1, pdf_dir, timeout)
                            meta["PDF Link"] = pdf_in_detail
                            batch.append(meta)
                            seen_pdf.add(pdf_in_detail)
                            count += 1
                    seen_detail.add(detail_url)
                    time.sleep(sleep_sec)
            if batch:
                save_rows(out_csv, batch)
                batch = []
            page_idx += 1

    return count

def id_scan(target, out_csv, pdf_dir, sleep_sec, proxy, connect_timeout, read_timeout, skip_download, years, ranges, verify_links=False):
    os.makedirs(pdf_dir, exist_ok=True)
    session = build_session(proxy)
    timeout = (connect_timeout, read_timeout)
    existing = load_existing(out_csv)
    seen_pdf = set(r.get("PDF Link", "") for r in existing if r.get("PDF Link"))
    count = len(existing)
    batch = []
    for year in years:
        for start, end in ranges:
            step = -1 if start > end else 1
            for num in range(start, end + step, step):
                if count >= target:
                    break
                code = f"{year}LHC{num}"
                pdf_url = f"http://sys.lhc.gov.pk/appjudgments/{code}.pdf"
                if pdf_url in seen_pdf:
                    continue
                meta = {"Title": code, "Date": "", "Judge": "", "PDF Link": pdf_url, "DetailURL": ""}
                if skip_download:
                    if not verify_links or verify_url_exists(session, pdf_url, timeout):
                        batch.append(meta)
                        seen_pdf.add(pdf_url)
                        count += 1
                else:
                    try:
                        if not verify_links or verify_url_exists(session, pdf_url, timeout):
                            download_pdf(session, pdf_url, code, count + 1, pdf_dir, timeout)
                            batch.append(meta)
                            seen_pdf.add(pdf_url)
                            count += 1
                    except Exception:
                        pass
                if len(batch) >= 50:
                    save_rows(out_csv, batch)
                    batch = []
                time.sleep(sleep_sec)
            if count >= target:
                break
        if count >= target:
            break
    if batch:
        save_rows(out_csv, batch)
    return count

def page_scrape(target, out_csv, pdf_dir, sleep_sec, proxy, connect_timeout, read_timeout, start_url, skip_download=False, verify_links=False, overrides=None):
    os.makedirs(pdf_dir, exist_ok=True)
    session = build_session(proxy)
    timeout = (connect_timeout, read_timeout)
    existing = load_existing(out_csv)
    seen_pdf = set(r.get("PDF Link", "") for r in existing if r.get("PDF Link"))
    seen_detail = set(r.get("DetailURL", "") for r in existing if r.get("DetailURL"))
    count = len(existing)
    batch = []
    base = start_url.split("?")[0]
    soup = apply_filters(session, base, timeout, overrides or {})
    page_idx = 0
    while count < target:
        items = extract_items_from_listing_table(soup)
        if not items:
            break
        for item in items:
            if count >= target:
                break
            title = item.get("title") or ""
            pdf_url = item.get("pdf_url")
            detail_url = item.get("detail_url")
            meta = {"Title": title, "Date": "", "Judge": "", "PDF Link": "", "DetailURL": detail_url or ""}
            if pdf_url and pdf_url not in seen_pdf:
                if skip_download:
                    if not verify_links or verify_url_exists(session, pdf_url, timeout):
                        meta["PDF Link"] = pdf_url
                        batch.append(meta)
                        seen_pdf.add(pdf_url)
                        count += 1
                else:
                    if not verify_links or verify_url_exists(session, pdf_url, timeout):
                        download_pdf(session, pdf_url, title or f"doc_{count+1}", count+1, pdf_dir, timeout)
                        meta["PDF Link"] = pdf_url
                        batch.append(meta)
                        seen_pdf.add(pdf_url)
                        count += 1
                time.sleep(sleep_sec)
                continue
            if detail_url and detail_url not in seen_detail:
                dsoup = get_soup(session, detail_url, timeout)
                dmeta = extract_metadata_from_detail(dsoup, detail_url)
                meta["Title"] = dmeta.get("Title", meta["Title"]) or meta["Title"]
                meta["Judge"] = dmeta.get("Judge", "")
                meta["Date"] = dmeta.get("DecisionDate", dmeta.get("UploadedDate", ""))
                meta["DetailURL"] = detail_url
                pdf_in_detail = find_pdf_in_detail(dsoup)
                if pdf_in_detail and pdf_in_detail not in seen_pdf:
                    if skip_download:
                        if not verify_links or verify_url_exists(session, pdf_in_detail, timeout):
                            meta["PDF Link"] = pdf_in_detail
                            batch.append(meta)
                            seen_pdf.add(pdf_in_detail)
                            count += 1
                    else:
                        if not verify_links or verify_url_exists(session, pdf_in_detail, timeout):
                            download_pdf(session, pdf_in_detail, meta["Title"] or f"doc_{count+1}", count+1, pdf_dir, timeout)
                            meta["PDF Link"] = pdf_in_detail
                            batch.append(meta)
                            seen_pdf.add(pdf_in_detail)
                            count += 1
                seen_detail.add(detail_url)
                time.sleep(sleep_sec)
        if batch:
            save_rows(out_csv, batch)
            batch = []
        page_idx += 1
        next_url = f"{base}?page={page_idx}"
        nsoup = get_soup(session, next_url, timeout)
        nitems = extract_items_from_listing_table(nsoup)
        if not nitems:
            break
        soup = nsoup
    return count

def find_form_fields(soup):
    fields = {}
    for inp in soup.select("form input[name], form select[name], form textarea[name]"):
        name = inp.get("name")
        if name:
            fields[name] = inp
    return fields

def build_filter_payload(soup, overrides):
    payload = {}
    fields = find_form_fields(soup)
    for name in fields.keys():
        payload[name] = fields[name].get("value", "")
    for k, v in overrides.items():
        candidates = []
        if k == "year":
            candidates = ["year", "Select Year", "select_year"]
        elif k == "judge":
            candidates = ["courtName", "judge", "Hon'ble Judge", "hon_judge"]
        elif k == "citation":
            candidates = ["citation", "Citation/Tag Line", "tag_line"]
        elif k == "caseno":
            candidates = ["caseNo", "case_no", "Case #"]
        elif k == "title":
            candidates = ["title", "Title"]
        elif k == "decision_from":
            candidates = ["decisionDate[from]", "decision_from", "Decision Date From"]
        elif k == "decision_to":
            candidates = ["decisionDate[to]", "decision_to", "Decision Date To"]
        elif k == "uploaded_from":
            candidates = ["uploadedDate[from]", "uploaded_from", "Uploaded Date From"]
        elif k == "uploaded_to":
            candidates = ["uploadedDate[to]", "uploaded_to", "Uploaded Date To"]
        else:
            candidates = [k]
        applied = False
        for cand in candidates:
            if cand in fields:
                payload[cand] = v
                applied = True
                break
        if not applied:
            for name in fields.keys():
                if k.lower() in name.lower():
                    payload[name] = v
                    break
    return payload

def apply_filters(session, url, timeout, overrides):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    payload = build_filter_payload(soup, overrides or {})
    if not payload:
        return soup
    fb = soup.select_one("input[name=form_build_id]")
    fid = soup.select_one("input[name=form_id]")
    if fb and fb.get("value"):
        payload["form_build_id"] = fb.get("value")
    if fid and fid.get("value"):
        payload["form_id"] = fid.get("value")
    payload.setdefault("op", "Submit")
    pr = session.post(url, data=payload, timeout=timeout)
    pr.raise_for_status()
    return BeautifulSoup(pr.text, "html.parser")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", type=int, default=1000)
    p.add_argument("--out", type=str, default="lhc_1000_documents.csv")
    p.add_argument("--pdf-dir", type=str, default="lhc_documents")
    p.add_argument("--sleep", type=float, default=1.0)
    p.add_argument("--proxy", type=str, default="")
    p.add_argument("--connect-timeout", type=float, default=10.0)
    p.add_argument("--read-timeout", type=float, default=60.0)
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--verify-links", action="store_true")
    p.add_argument("--mode", type=str, choices=["list", "idscan", "page"], default="list")
    p.add_argument("--scan-years", type=str, default="2025,2024")
    p.add_argument("--scan-range", type=str, default="7500-5000")
    p.add_argument("--start-url", type=str, default=LIST_URL)
    p.add_argument("--filters-year", type=str, default="")
    p.add_argument("--filters-judge", type=str, default="")
    p.add_argument("--filters-decision-from", type=str, default="")
    p.add_argument("--filters-decision-to", type=str, default="")
    p.add_argument("--filters-uploaded-from", type=str, default="")
    p.add_argument("--filters-uploaded-to", type=str, default="")
    args = p.parse_args()
    if args.mode == "list":
        scrape(args.target, args.out, args.pdf_dir, args.sleep, args.proxy, args.connect_timeout, args.read_timeout, skip_download=args.skip_download, verify_links=args.verify_links)
    else:
        if args.mode == "idscan":
            years = [y.strip() for y in args.scan_years.split(",") if y.strip()]
            ranges = []
            for part in args.scan_range.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part:
                    a, b = part.split("-", 1)
                    try:
                        ranges.append((int(a), int(b)))
                    except Exception:
                        pass
            if not ranges:
                ranges = [(7500, 5000)]
            id_scan(args.target, args.out, args.pdf_dir, args.sleep, args.proxy, args.connect_timeout, args.read_timeout, args.skip_download, years, ranges, verify_links=args.verify_links)
        else:
            overrides = {}
            if args.filters_year:
                overrides["year"] = args.filters_year
            if args.filters_judge:
                overrides["judge"] = args.filters_judge
            if args.filters_decision_from:
                overrides["decision_from"] = args.filters_decision_from
            if args.filters_decision_to:
                overrides["decision_to"] = args.filters_decision_to
            if args.filters_uploaded_from:
                overrides["uploaded_from"] = args.filters_uploaded_from
            if args.filters_uploaded_to:
                overrides["uploaded_to"] = args.filters_uploaded_to
            overrides = {}
            if args.filters_year:
                overrides["year"] = args.filters_year
            if args.filters_judge:
                overrides["judge"] = args.filters_judge
            if args.filters_decision_from:
                overrides["decision_from"] = args.filters_decision_from
            if args.filters_decision_to:
                overrides["decision_to"] = args.filters_decision_to
            if args.filters_uploaded_from:
                overrides["uploaded_from"] = args.filters_uploaded_from
            if args.filters_uploaded_to:
                overrides["uploaded_to"] = args.filters_uploaded_to
            page_scrape(args.target, args.out, args.pdf_dir, args.sleep, args.proxy, args.connect_timeout, args.read_timeout, args.start_url, skip_download=args.skip_download, verify_links=args.verify_links, overrides=overrides)

if __name__ == "__main__":
    main()
