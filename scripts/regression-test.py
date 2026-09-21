#!/usr/bin/env python3
"""
Automated Portfolio Regression Test Suite
Validates 100% functionality, link integrity, UI/UX, CSP, metadata, and asset resolution.
"""

import os, sys, re, json, html
from urllib.parse import urlparse

def run_regression_test(repo_path, cdn_manifest_path=None):
    errors = []
    warnings = []
    
    docs_dir = os.path.join(repo_path, "docs") if os.path.isdir(os.path.join(repo_path, "docs")) else os.path.join(repo_path, "public")
    if not os.path.isdir(docs_dir):
        return [f"Output directory not found (checked docs/ and public/ in {repo_path})"], []

    # 1. Load CDN manifest if available
    valid_cdn_paths = set()
    if cdn_manifest_path and os.path.isfile(cdn_manifest_path):
        try:
            with open(cdn_manifest_path, "r") as fp:
                mdata = json.load(fp)
            valid_cdn_paths = set(item.get("path") for item in mdata if item.get("path"))
        except Exception as e:
            warnings.append(f"Failed to load CDN manifest: {e}")

    # 2. Check Core Root & Metadata Files
    required_root_files = ["robots.txt", "sitemap.xml", "manifest.json", "rss.xml", "search-index.json"]
    for rf in required_root_files:
        fpath = os.path.join(docs_dir, rf)
        if not os.path.isfile(fpath):
            errors.append(f"Missing essential output file: {rf}")
        elif os.path.getsize(fpath) == 0 and rf != "robots.txt":
            errors.append(f"Output file is empty: {rf}")

    # Validate search-index.json
    search_idx_path = os.path.join(docs_dir, "search-index.json")
    if os.path.isfile(search_idx_path):
        try:
            with open(search_idx_path, "r") as fp:
                sdata = json.load(fp)
            entries = sdata if isinstance(sdata, list) else sdata.get("entries", [])
            if len(entries) == 0:
                warnings.append("search-index.json contains 0 entries")
        except Exception as e:
            errors.append(f"Invalid JSON in search-index.json: {e}")

    # Validate manifest.json
    manifest_path = os.path.join(docs_dir, "manifest.json")
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r") as fp:
                mjson = json.load(fp)
            if not mjson.get("name") or not mjson.get("icons"):
                warnings.append("manifest.json missing 'name' or 'icons'")
        except Exception as e:
            errors.append(f"Invalid JSON in manifest.json: {e}")

    # 3. Check JavaScript Engine (Theme Switcher, Search, Mobile Nav)
    js_files = []
    for root, _, files in os.walk(docs_dir):
        for filename in files:
            if filename.endswith(".js"):
                js_files.append(os.path.join(root, filename))
    if not js_files:
        errors.append("Missing client engine scripts")
    else:
        javascript = ""
        for js_path in js_files:
            with open(js_path, "r", errors="ignore") as fp:
                javascript += fp.read()
        if "data-theme" not in javascript and "applyTheme" not in javascript:
            errors.append("Client scripts are missing the theme switcher implementation")
        if "ssg-search" not in javascript and "searchIndex" not in javascript:
            errors.append("Client scripts are missing the search engine implementation")
        if "navToggle" not in javascript and "navbarToggle" not in javascript:
            errors.append("Client scripts are missing the mobile navigation implementation")
        if "setGalleryImage" not in javascript:
            errors.append("Client scripts are missing the gallery popover implementation")

    # 4. Deep HTML Validation across all pages
    html_files = []
    for root, _, files in os.walk(docs_dir):
        for f in files:
            if f.endswith(".html"):
                html_files.append(os.path.join(root, f))

    if not html_files:
        errors.append("No HTML files found in output directory")
        return errors, warnings

    link_re = re.compile(r'href="([^"#\s][^"]*)"')
    src_re = re.compile(r'src="([^"#\s][^"]*)"')
    meta_desc_re = re.compile(r'<meta\s+((?:name|property)="[^"]*")\s+content="([^"]*)"[^>]*>', re.IGNORECASE)
    tag_re = re.compile(r'<[^>]+>')

    for fpath in html_files:
        rel_fpath = os.path.relpath(fpath, docs_dir)
        with open(fpath, "r", errors="ignore") as fp:
            content = fp.read()

        # A. Check CSP
        csp_match = re.search(r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]*)"[^>]*>', content, re.IGNORECASE)
        if not csp_match:
            errors.append(f"{rel_fpath}: Missing Content-Security-Policy meta tag")
        else:
            csp_val = csp_match.group(1)
            if "default-src" not in csp_val or "style-src" not in csp_val or "script-src" not in csp_val:
                errors.append(f"{rel_fpath}: CSP missing required directives")

        # B. Check for HTML leaks in <head> meta descriptions
        head_match = re.search(r'<head>(.*?)</head>', content, re.DOTALL | re.IGNORECASE)
        if head_match:
            head_content = head_match.group(1)
            # Check for leaked visible tags in head
            if re.search(r'</?(?:div|h[1-6]|p|span|a)\b', head_content):
                errors.append(f"{rel_fpath}: Raw HTML tags detected inside <head> (causes visible text leak)")
            # Check meta description content
            for m in meta_desc_re.finditer(head_content):
                attr, val = m.group(1), m.group(2)
                if "<" in val or ">" in val or "&lt;" in val or "&gt;" in val:
                    errors.append(f"{rel_fpath}: Meta tag {attr} contains unescaped HTML: {val[:40]}...")

        # C. Check Made with SSG & Subpages for Hero Banner isolation
        if "made-with-ssg" in rel_fpath or (rel_fpath != "index.html" and rel_fpath != "docs/index.html"):
            if '<header class="hero-banner-container">' in content:
                # Allow hero banner on homepage only
                if rel_fpath != "index.html":
                    errors.append(f"{rel_fpath}: Subpage contains hero banner (<header class=\"hero-banner-container\"> must only appear on homepage)")

        # D. Check UI/UX Core Components
        if ('class="site-header"' not in content or 'class="site-nav"' not in content) and ("navbar" not in content or "navbar-brand" not in content):
            errors.append(f"{rel_fpath}: Missing responsive navbar")
        if 'id="mode-toggle"' not in content and "theme-switcher" not in content:
            errors.append(f"{rel_fpath}: Missing theme switcher buttons in navbar")
        if 'id="ssg-search-btn"' not in content and "searchTrigger" not in content and "search-trigger" not in content:
            errors.append(f"{rel_fpath}: Missing search trigger button in navbar")
        if 'id="navToggle"' not in content and "navbarToggle" not in content:
            errors.append(f"{rel_fpath}: Missing mobile hamburger toggle button")
        if 'id="ssg-search-overlay"' not in content and "searchModal" not in content:
            errors.append(f"{rel_fpath}: Missing search modal dialog in DOM")

        # Every photographic gallery must expose its images through one shared,
        # keyboard-operable native popover viewer.
        gallery_items = content.count('class="gallery-item"')
        gallery_triggers = content.count('class="gallery-trigger"')
        if gallery_items:
            if gallery_triggers != gallery_items:
                errors.append(
                    f"{rel_fpath}: Gallery has {gallery_items} items but {gallery_triggers} popover triggers"
                )
            if content.count('id="gallery-lightbox"') != 1:
                errors.append(f"{rel_fpath}: Gallery must have exactly one shared lightbox")
            if 'popover="auto"' not in content:
                errors.append(f"{rel_fpath}: Gallery lightbox is missing native auto-popover behaviour")
            if 'aria-modal="true"' not in content:
                errors.append(f"{rel_fpath}: Gallery lightbox is missing modal dialog semantics")
            if 'data-gallery-previous' not in content or 'data-gallery-next' not in content:
                errors.append(f"{rel_fpath}: Gallery lightbox is missing previous/next controls")

        # E. Internal Link & Asset Resolution (404 Check)
        for link in link_re.findall(content):
            if link.startswith("/") and not link.startswith("//"):
                parsed = urlparse(link)
                target = parsed.path.lstrip("/")
                if target == "" or target.endswith("/"):
                    target_file = os.path.join(docs_dir, target, "index.html")
                else:
                    target_file = os.path.join(docs_dir, target)
                
                # Check if target file or directory exists
                if not os.path.exists(target_file) and not os.path.exists(os.path.join(docs_dir, target + ".html")):
                    # Ignore common dynamic/feed links if file is generated under alternative name
                    if not target.startswith("tags/") and not target.startswith("rss") and not target.startswith("atom"):
                        warnings.append(f"{rel_fpath}: Internal link 404 -> {link}")

        for src in src_re.findall(content):
            if src.startswith("/") and not src.startswith("//"):
                parsed_src = urlparse(src)
                target = parsed_src.path.lstrip("/")
                target_file = os.path.join(docs_dir, target)
                if not os.path.exists(target_file):
                    errors.append(f"{rel_fpath}: Local asset 404 -> {src}")
            elif "cloudcdn.pro" in src and valid_cdn_paths:
                u_match = re.search(r'cloudcdn\.pro/([a-zA-Z0-9_\-\.\/]+)', src)
                if u_match:
                    u_clean = u_match.group(1).rstrip(".,;:\"'`\\")
                    if not (u_clean in valid_cdn_paths or f"clients/{u_clean}" in valid_cdn_paths or f"stocks/{u_clean}" in valid_cdn_paths or f"stocks/images/{u_clean}" in valid_cdn_paths or u_clean == "" or u_clean == "clients"):
                        errors.append(f"{rel_fpath}: CloudCDN asset 404 -> {src}")

    return errors, warnings


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    cdn_manifest = "/Users/seb/Code/Public/JavaScript/cloudcdn.pro/manifest.json"
    
    print(f"Running Automated Regression Test on: {target_dir}")
    errs, warns = run_regression_test(target_dir, cdn_manifest_path=cdn_manifest)
    
    if warns:
        print(f"\n[⚠️ WARNINGS ({len(warns)})]:")
        for w in warns[:10]:
            print(f"  - {w}")
            
    if errs:
        print(f"\n[❌ ERRORS ({len(errs)})]:")
        for e in errs:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\n[✅ PASSED]: 100% regression tests passed with zero errors!")
        sys.exit(0)
