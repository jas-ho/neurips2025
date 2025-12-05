#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Build offline HTML viewer for NeurIPS papers.
Optimized for busy researchers on iPad/mobile.
"""

import argparse
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_similarity(year: int) -> dict:
    """Load pre-computed similarity data if available."""
    similarity_file = DATA_DIR / f"similarity_{year}.json"
    if similarity_file.exists():
        with open(similarity_file) as f:
            return json.load(f)
    return {}


def load_neurips(year: int):
    """Load and process NeurIPS papers for the viewer."""
    data_file = DATA_DIR / f"neurips-{year}-orals-posters.json"
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")

    with open(data_file) as f:
        raw = json.load(f)

    papers = []
    for p in raw.get("results", []):
        # Format authors: "Name (Institution), Name (Institution), ..."
        authors_list = p.get("authors", [])
        if authors_list:
            authors_str = ", ".join(
                f"{a.get('fullname', 'Unknown')}" +
                (f" ({a.get('institution')})" if a.get('institution') else "")
                for a in authors_list
            )
        else:
            authors_str = ""

        # Extract topic category (e.g., "Computer Vision" from "Computer Vision->Everything Else")
        topic = p.get("topic") or ""
        topic_category = topic.split("->")[0] if topic else ""

        # Normalize decision for filtering
        decision = p.get("decision") or ""
        if "Oral" in decision:
            decision_type = "Oral"
        elif "spotlight" in decision.lower():
            decision_type = "Spotlight"
        else:
            decision_type = "Poster"

        papers.append({
            "id": p["id"],
            "num": p.get("poster_position", ""),  # e.g., "#4902"
            "title": p.get("name", ""),
            "authors": authors_str,
            "affiliations": [a.get("institution", "") for a in authors_list if a.get("institution")],
            "decision": decision_type,  # Oral, Poster, Spotlight
            "decision_full": decision,  # Full decision text
            "session": p.get("session", ""),
            "datetime": p.get("starttime", ""),  # ISO format
            "datetime_end": p.get("endtime", ""),
            "room": p.get("room_name", ""),
            "content_type": p.get("eventtype", ""),
            "topic": topic,  # Full topic string
            "topic_category": topic_category,  # Just the main category
            "keywords": p.get("keywords") or [],
            "text": p.get("abstract") or "",
            "has_abstract": bool((p.get("abstract") or "").strip()),
            "url": p.get("paper_url", ""),
            "virtualsite_url": p.get("virtualsite_url", ""),
        })

    return papers


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <title>NeurIPS __YEAR__</title>
    <link rel="preconnect" href="https://api.fontshare.com">
    <link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,900&f[]=cabinet-grotesk@700,800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #FAFAFA;
            --bg-subtle: #F0F0F0;
            --card: #FFFFFF;
            --text: #0A0A0A;
            --text2: #3D3D3D;
            --text3: #8C8C8C;
            --accent: #00D26A;
            --accent-light: #4AE590;
            --accent-bg: #DFFFF0;
            --accent-dark: #00A854;
            --border: #E8E8E8;
            --tag-bg: #F5F5F5;
            --success: #00D26A;
            --warning: #FFB020;
            --oral: #FF6B6B;
            --spotlight: #FFD93D;
            --poster: #4ECDC4;
            --font-display: 'Cabinet Grotesk', 'Satoshi', system-ui, sans-serif;
            --font-body: 'Satoshi', system-ui, sans-serif;
            --font-ui: 'Satoshi', system-ui, sans-serif;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
            --shadow-lg: 0 8px 24px rgba(0,0,0,0.08);
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 20px;
            --radius-full: 100px;
        }
        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #0A0A0A;
                --bg-subtle: #141414;
                --card: #1A1A1A;
                --text: #FAFAFA;
                --text2: #BEBEBE;
                --text3: #6B6B6B;
                --accent: #00D26A;
                --accent-light: #4AE590;
                --accent-bg: #0A2818;
                --accent-dark: #00A854;
                --border: #2A2A2A;
                --tag-bg: #1F1F1F;
                --shadow-sm: 0 1px 2px rgba(0,0,0,0.2);
                --shadow-md: 0 4px 12px rgba(0,0,0,0.3);
                --shadow-lg: 0 8px 24px rgba(0,0,0,0.4);
            }
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body {
            font-family: var(--font-body);
            background: var(--bg);
            color: var(--text);
            line-height: 1.65;
            -webkit-text-size-adjust: 100%;
            padding-bottom: env(safe-area-inset-bottom);
            font-feature-settings: "ss01", "ss02";
        }

        /* Header - Bold & Confident */
        .header {
            position: sticky;
            top: 0;
            background: var(--bg);
            padding: 20px 16px 20px;
            z-index: 100;
            border-bottom: 1px solid var(--border);
        }
        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .header h1 {
            font-family: var(--font-display);
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -1px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header h1::before {
            content: '✳';
            color: var(--accent);
            font-size: 24px;
        }
        .header h1 span {
            color: var(--text3);
            font-weight: 700;
        }
        .header-actions {
            display: flex;
            gap: 10px;
        }
        .btn {
            font-family: var(--font-ui);
            padding: 10px 18px;
            border: 2px solid var(--border);
            border-radius: var(--radius-full);
            background: var(--card);
            color: var(--text);
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }
        .btn:hover {
            border-color: var(--text);
            transform: translateY(-1px);
            box-shadow: var(--shadow-sm);
        }
        .btn:active { transform: scale(0.98) translateY(0); }
        .btn.active {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }

        /* Search - Clean & Modern */
        .search-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .search-row {
            display: flex;
            gap: 10px;
        }
        .search-row input {
            flex: 1;
            padding: 16px 20px;
            border: 2px solid var(--border);
            border-radius: var(--radius-full);
            font-family: var(--font-body);
            font-size: 16px;
            background: var(--card);
            color: var(--text);
            min-width: 0;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-sm);
        }
        .search-row input::placeholder { color: var(--text3); }
        .search-row input:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 4px var(--accent-bg), var(--shadow-md);
        }

        /* Search Options */
        .search-options {
            display: flex;
            gap: 20px;
            padding: 0 8px;
        }
        .search-option {
            display: flex;
            align-items: center;
            gap: 8px;
            font-family: var(--font-ui);
            font-size: 13px;
            font-weight: 500;
            color: var(--text2);
            cursor: pointer;
            user-select: none;
        }
        .search-option input[type="checkbox"] {
            appearance: none;
            width: 18px;
            height: 18px;
            border: 2px solid var(--border);
            border-radius: 5px;
            background: var(--card);
            cursor: pointer;
            position: relative;
            transition: all 0.15s ease;
        }
        .search-option input[type="checkbox"]:checked {
            background: var(--accent);
            border-color: var(--accent);
        }
        .search-option input[type="checkbox"]:checked::after {
            content: '✓';
            position: absolute;
            color: white;
            font-size: 12px;
            font-weight: bold;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }

        /* Filters - Pill Style */
        .filters {
            display: flex;
            gap: 8px;
            margin-top: 16px;
            flex-wrap: wrap;
            align-items: center;
        }
        .filter-chip {
            font-family: var(--font-ui);
            padding: 8px 16px;
            border-radius: var(--radius-full);
            font-size: 14px;
            font-weight: 600;
            background: var(--card);
            color: var(--text2);
            border: 2px solid var(--border);
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .filter-chip:hover {
            border-color: var(--text3);
            transform: translateY(-1px);
        }
        .filter-chip.active {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }
        .filter-divider {
            width: 2px;
            height: 24px;
            background: var(--border);
            margin: 0 6px;
            border-radius: 1px;
        }
        .filter-toggle {
            font-family: var(--font-ui);
            padding: 8px 16px;
            border-radius: var(--radius-full);
            font-size: 13px;
            font-weight: 600;
            background: transparent;
            color: var(--text3);
            border: 2px dashed var(--border);
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .filter-toggle:hover { border-color: var(--accent); color: var(--accent); }
        .filter-toggle.has-active {
            color: var(--accent);
            border-color: var(--accent);
            border-style: solid;
            background: var(--accent-bg);
        }
        .filter-clear {
            font-family: var(--font-ui);
            padding: 8px 14px;
            border-radius: var(--radius-full);
            font-size: 12px;
            font-weight: 600;
            background: var(--accent-bg);
            color: var(--accent);
            border: none;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .filter-clear:hover { background: var(--accent); color: white; }

        /* Collapsible filter section */
        .filters-expanded {
            display: none;
            flex-direction: column;
            gap: 12px;
            margin-top: 16px;
            padding: 16px;
            background: var(--card);
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
            animation: slideDown 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }
        .filters-expanded.open { display: flex; }
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .filter-group {
            display: flex;
            gap: 8px;
            align-items: center;
            overflow-x: auto;
            padding-bottom: 4px;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: thin;
        }
        .filter-group::-webkit-scrollbar { height: 4px; }
        .filter-group::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 2px;
        }
        .filter-label {
            font-family: var(--font-ui);
            font-size: 11px;
            font-weight: 700;
            color: var(--text3);
            text-transform: uppercase;
            letter-spacing: 1px;
            min-width: 60px;
            flex-shrink: 0;
        }
        .filter-chip.small {
            padding: 6px 12px;
            font-size: 13px;
            flex-shrink: 0;
            white-space: nowrap;
        }

        /* Session & Similar filters */
        .session-filter, .similar-filter {
            display: none;
            align-items: center;
            gap: 10px;
            margin-top: 12px;
            padding: 12px 16px;
            background: var(--accent-bg);
            border-radius: var(--radius-md);
            border: 2px solid var(--accent-light);
        }
        .session-filter.active, .similar-filter.active { display: flex; }
        .session-filter-label, .similar-filter-label {
            font-family: var(--font-ui);
            font-size: 11px;
            font-weight: 700;
            color: var(--accent-dark);
            text-transform: uppercase;
            letter-spacing: 1px;
            flex-shrink: 0;
        }
        .session-filter-value, .similar-filter-value {
            font-family: var(--font-ui);
            font-size: 14px;
            font-weight: 500;
            color: var(--text);
            flex: 1;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .session-filter-clear, .similar-filter-clear {
            font-family: var(--font-ui);
            font-size: 18px;
            color: var(--text3);
            background: none;
            border: none;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: var(--radius-sm);
            line-height: 1;
            transition: all 0.15s ease;
        }
        .session-filter-clear:hover, .similar-filter-clear:hover {
            color: var(--accent-dark);
            background: white;
        }

        /* Similar filter specific */
        .similar-filter-label::before {
            content: '◈';
            margin-right: 6px;
        }

        /* Find Similar button */
        .find-similar-btn {
            font-family: var(--font-ui);
            color: var(--text2);
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            background: var(--card);
            border: 2px solid var(--border);
            padding: 8px 14px;
            border-radius: var(--radius-full);
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .find-similar-btn:hover {
            border-color: var(--accent);
            color: var(--accent);
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        .find-similar-btn:active { transform: translateY(0); }
        .find-similar-btn::before {
            content: '◈';
            font-size: 14px;
        }

        /* Search snippet */
        .card-snippet {
            font-family: var(--font-body);
            font-size: 14px;
            color: var(--text2);
            line-height: 1.6;
            margin-top: 12px;
            padding: 12px 14px;
            background: var(--bg-subtle);
            border-radius: var(--radius-sm);
            border-left: 4px solid var(--accent);
        }
        .card-snippet mark {
            background: linear-gradient(to bottom, transparent 40%, var(--warning) 40%);
            padding: 0 2px;
            font-weight: 600;
        }
        @media (prefers-color-scheme: dark) {
            .card-snippet mark { background: linear-gradient(to bottom, transparent 40%, #7a5a10 40%); }
        }
        .card.expanded .card-snippet { display: none; }

        /* Stats */
        .stats {
            font-family: var(--font-ui);
            font-size: 13px;
            font-weight: 500;
            color: var(--text3);
            margin-top: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .stats-count { font-variant-numeric: tabular-nums; }

        /* Results */
        .results {
            padding: 20px 16px;
            max-width: 900px;
            margin: 0 auto;
        }

        /* Card - Clean & Elevated */
        .card {
            background: var(--card);
            border-radius: var(--radius-lg);
            padding: 24px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
            transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            animation: cardEnter 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) backwards;
        }
        .card:nth-child(1) { animation-delay: 0.02s; }
        .card:nth-child(2) { animation-delay: 0.04s; }
        .card:nth-child(3) { animation-delay: 0.06s; }
        .card:nth-child(4) { animation-delay: 0.08s; }
        .card:nth-child(5) { animation-delay: 0.1s; }
        @keyframes cardEnter {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .card:hover {
            border-color: var(--accent);
            box-shadow: var(--shadow-md), 0 0 0 1px var(--accent-bg);
            transform: translateY(-2px);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 12px;
        }
        .card-header-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-num {
            font-family: var(--font-ui);
            font-size: 12px;
            color: var(--accent-dark);
            font-weight: 700;
            flex-shrink: 0;
            background: var(--accent-bg);
            padding: 4px 10px;
            border-radius: var(--radius-full);
            letter-spacing: 0.5px;
        }
        .card-star-btn {
            color: var(--text3);
            font-size: 18px;
            opacity: 0.4;
            cursor: pointer;
            padding: 6px;
            margin: -6px;
            border-radius: var(--radius-sm);
            transition: all 0.2s ease;
            border: none;
            background: none;
        }
        .card-star-btn:hover {
            opacity: 1;
            color: var(--warning);
            background: var(--tag-bg);
        }
        .card.is-starred .card-star-btn {
            opacity: 1;
            color: var(--warning);
        }
        .card-datetime {
            font-family: var(--font-ui);
            font-size: 12px;
            color: var(--text3);
            text-align: right;
            line-height: 1.5;
            font-weight: 500;
        }
        .card-title {
            font-family: var(--font-display);
            font-size: 20px;
            font-weight: 700;
            line-height: 1.35;
            margin-bottom: 12px;
            cursor: pointer;
            transition: color 0.2s ease;
            letter-spacing: -0.3px;
        }
        .card-title:hover { color: var(--accent); }

        .card-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }

        /* Tags - Colorful Circles for Decision */
        .tag {
            font-family: var(--font-ui);
            display: inline-flex;
            align-items: center;
            padding: 5px 12px;
            border-radius: var(--radius-full);
            font-size: 12px;
            font-weight: 600;
            background: var(--tag-bg);
            color: var(--text2);
            border: none;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .tag:hover {
            background: var(--border);
            transform: translateY(-1px);
        }
        /* Decision badges - Apart-style colored circles */
        .tag.decision {
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 11px;
        }
        .tag.decision::before {
            content: '';
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 6px;
            flex-shrink: 0;
        }
        .tag.decision.oral {
            background: rgba(255, 107, 107, 0.15);
            color: #D94444;
        }
        .tag.decision.oral::before { background: var(--oral); }
        .tag.decision.spotlight {
            background: rgba(255, 217, 61, 0.2);
            color: #9A7B00;
        }
        .tag.decision.spotlight::before { background: var(--spotlight); }
        .tag.decision.poster {
            background: rgba(78, 205, 196, 0.15);
            color: #2A9D8F;
        }
        .tag.decision.poster::before { background: var(--poster); }
        .tag.decision:hover { opacity: 0.85; transform: translateY(-1px); }
        @media (prefers-color-scheme: dark) {
            .tag.decision.oral { color: #FF8A8A; }
            .tag.decision.spotlight { color: #FFE066; }
            .tag.decision.poster { color: #6EE7DF; }
        }

        /* Keywords */
        .keywords-section { margin-bottom: 16px; }
        .keywords-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }
        .keyword-tag {
            font-family: var(--font-ui);
            display: inline-block;
            padding: 4px 10px;
            border-radius: var(--radius-full);
            font-size: 12px;
            background: var(--bg-subtle);
            color: var(--text2);
            font-weight: 500;
        }
        .tag.no-abstract {
            background: rgba(255, 176, 32, 0.15);
            color: #B07B00;
            border: 1px dashed var(--warning);
        }
        @media (prefers-color-scheme: dark) {
            .tag.no-abstract { background: rgba(255, 176, 32, 0.1); color: #FFB020; }
        }

        .card-authors {
            font-size: 14px;
            color: var(--text2);
            line-height: 1.6;
            margin-bottom: 0;
            max-height: 0;
            overflow: hidden;
            opacity: 0;
            transition: all 0.3s ease;
        }
        .card.expanded .card-authors {
            max-height: 200px;
            opacity: 1;
            margin-bottom: 16px;
        }

        /* Expanded content */
        .card-body {
            max-height: 0;
            overflow: hidden;
            opacity: 0;
            transition: all 0.35s ease;
        }
        .card.expanded .card-body {
            max-height: 5000px;
            opacity: 1;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid var(--bg-subtle);
        }

        .abstract-text {
            font-size: 15px;
            line-height: 1.75;
            color: var(--text);
        }
        .abstract-text p { margin-bottom: 14px; }
        .abstract-text p:last-child { margin-bottom: 0; }
        .section-label {
            font-family: var(--font-ui);
            font-size: 11px;
            font-weight: 700;
            color: var(--accent-dark);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            margin-top: 20px;
        }
        .section-label:first-child { margin-top: 0; }

        .card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 24px;
            padding-top: 20px;
            border-top: 2px solid var(--bg-subtle);
        }
        .card-link {
            font-family: var(--font-ui);
            color: var(--accent);
            text-decoration: none;
            font-size: 14px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }
        .card-link:hover { color: var(--accent-dark); }
        .card-link::after {
            content: '→';
            transition: transform 0.2s ease;
        }
        .card-link:hover::after { transform: translateX(3px); }
        .card-actions {
            display: flex;
            gap: 10px;
        }
        .icon-btn {
            width: 40px;
            height: 40px;
            border-radius: var(--radius-md);
            border: 2px solid var(--border);
            background: var(--card);
            color: var(--text3);
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }
        .icon-btn:hover {
            border-color: var(--warning);
            color: var(--warning);
            transform: translateY(-2px);
        }
        .icon-btn.starred {
            color: var(--warning);
            border-color: var(--warning);
            background: rgba(255, 176, 32, 0.1);
        }

        .empty {
            text-align: center;
            padding: 100px 24px;
            color: var(--text2);
        }
        .empty h3 {
            font-family: var(--font-display);
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 10px;
            color: var(--text);
        }

        /* Keyboard hints */
        .keyboard-hints { display: none; }
        .kbd {
            font-family: var(--font-ui);
            padding: 3px 8px;
            background: var(--card);
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text3);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }
        @media (min-width: 768px) {
            .keyboard-hints { display: block; }
            .header { padding: 24px 32px 24px; }
            .results { padding: 24px 32px; }
            .header h1 { font-size: 36px; }
        }

        /* Focus */
        .card.focused {
            outline: 3px solid var(--accent);
            outline-offset: 2px;
        }

        mark {
            background: linear-gradient(to bottom, transparent 50%, var(--warning) 50%);
            color: inherit;
            padding: 0 2px;
            font-weight: 600;
        }
        @media (prefers-color-scheme: dark) {
            mark { background: linear-gradient(to bottom, transparent 50%, #7a5a10 50%); }
        }

        .no-abstract-notice {
            font-family: var(--font-ui);
            font-style: italic;
            color: var(--text3);
            font-size: 14px;
            padding: 20px;
            background: var(--tag-bg);
            border-radius: var(--radius-md);
            text-align: center;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 10px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 5px;
        }
        ::-webkit-scrollbar-thumb:hover { background: var(--text3); }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-top">
            <h1>NeurIPS <span>__YEAR__</span></h1>
            <div class="header-actions">
                <button class="btn" id="starredBtn" onclick="toggleStarredOnly()">★ Saved</button>
            </div>
        </div>
        <div class="search-container">
            <div class="search-row">
                <input type="search" id="search" placeholder="Search titles, authors, abstracts..." autocomplete="off">
            </div>
            <div class="search-options">
                <label class="search-option">
                    <input type="checkbox" id="wordBoundary" checked>
                    <span>Whole words</span>
                </label>
                <label class="search-option">
                    <input type="checkbox" id="caseSensitive">
                    <span>Case sensitive</span>
                </label>
            </div>
            <div class="session-filter" id="sessionFilter">
                <span class="session-filter-label">Session:</span>
                <span class="session-filter-value" id="sessionFilterValue"></span>
                <button class="session-filter-clear" onclick="clearSessionFilter()" title="Clear session filter">×</button>
            </div>
            <div class="similar-filter" id="similarFilter">
                <span class="similar-filter-label">Similar to:</span>
                <span class="similar-filter-value" id="similarFilterValue"></span>
                <button class="similar-filter-clear" onclick="clearSimilarFilter()" title="Clear similarity filter">×</button>
            </div>
        </div>
        <div class="filters" id="dayFilters"></div>
        <div class="filters-expanded" id="filtersExpanded">
            <div class="filter-group" id="decisionFilters">
                <span class="filter-label">Type</span>
            </div>
            <div class="filter-group" id="topicFilters">
                <span class="filter-label">Topic</span>
            </div>
        </div>
        <div class="stats">
            <span id="stats" class="stats-count"></span>
            <span class="keyboard-hints"><kbd class="kbd">j/k</kbd> navigate <kbd class="kbd">/</kbd> search <kbd class="kbd">s</kbd> star</span>
        </div>
    </div>
    <div class="results" id="results"></div>

    <script>
    const DATA = __DATA_PLACEHOLDER__;
    const SIMILAR = __SIMILAR_PLACEHOLDER__;

    // State
    let starred = new Set(JSON.parse(localStorage.getItem('neurips__YEAR___starred') || '[]'));
    let showStarredOnly = false;
    let focusedIndex = -1;
    let activeDay = '';
    let activeDecision = '';
    let activeTopic = '';
    let activeSession = '';
    let activeSimilarTo = null;
    let filtersOpen = false;

    // Elements
    const searchEl = document.getElementById('search');
    const resultsEl = document.getElementById('results');
    const statsEl = document.getElementById('stats');
    const starredBtn = document.getElementById('starredBtn');
    const dayFiltersEl = document.getElementById('dayFilters');
    const wordBoundaryEl = document.getElementById('wordBoundary');
    const caseSensitiveEl = document.getElementById('caseSensitive');
    const filtersExpandedEl = document.getElementById('filtersExpanded');
    const decisionFiltersEl = document.getElementById('decisionFilters');
    const topicFiltersEl = document.getElementById('topicFilters');
    const sessionFilterEl = document.getElementById('sessionFilter');
    const sessionFilterValueEl = document.getElementById('sessionFilterValue');
    const similarFilterEl = document.getElementById('similarFilter');
    const similarFilterValueEl = document.getElementById('similarFilterValue');

    // Parse datetime to get day from ISO format
    function getDay(datetime) {
        if (!datetime) return null;
        const isoMatch = datetime.match(/^(\\d{4}-\\d{2}-\\d{2})/);
        if (isoMatch) {
            const date = new Date(isoMatch[1] + 'T12:00:00');
            const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
            return days[date.getDay()];
        }
        return null;
    }

    // Format datetime for display (conference timezone)
    function formatDatetime(datetime) {
        if (!datetime) return '';
        const isoMatch = datetime.match(/^(\\d{4})-(\\d{2})-(\\d{2})T(\\d{2}):(\\d{2})/);
        if (isoMatch) {
            const [, year, month, day, hour, min] = isoMatch;
            const date = new Date(Date.UTC(parseInt(year), parseInt(month) - 1, parseInt(day)));
            const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const h = parseInt(hour);
            const ampm = h >= 12 ? 'PM' : 'AM';
            const h12 = h % 12 || 12;
            return `${dayNames[date.getUTCDay()]}, ${monthNames[date.getUTCMonth()]} ${date.getUTCDate()}, ${h12}:${min} ${ampm}`;
        }
        return datetime;
    }

    // Day filters from datetime
    const days = [...new Set(DATA.map(d => getDay(d.datetime)).filter(Boolean))];
    const dayOrder = ['Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday'];
    days.sort((a, b) => dayOrder.indexOf(a) - dayOrder.indexOf(b));

    days.forEach(day => {
        const btn = document.createElement('button');
        btn.className = 'filter-chip';
        btn.dataset.day = day;
        btn.textContent = day.slice(0, 3);
        btn.onclick = () => {
            activeDay = activeDay === day ? '' : day;
            dayFiltersEl.querySelectorAll('[data-day]').forEach(b => b.classList.toggle('active', b.dataset.day === activeDay));
            render();
        };
        dayFiltersEl.appendChild(btn);
    });

    // Divider and toggle button
    const divider = document.createElement('span');
    divider.className = 'filter-divider';
    dayFiltersEl.appendChild(divider);

    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'filter-toggle';
    toggleBtn.innerHTML = 'Filters ▾';
    toggleBtn.onclick = () => {
        filtersOpen = !filtersOpen;
        filtersExpandedEl.classList.toggle('open', filtersOpen);
        updateToggleState();
    };
    dayFiltersEl.appendChild(toggleBtn);

    const clearBtn = document.createElement('button');
    clearBtn.className = 'filter-clear';
    clearBtn.innerHTML = 'Clear';
    clearBtn.style.display = 'none';
    clearBtn.onclick = () => {
        activeDecision = '';
        activeTopic = '';
        activeSession = '';
        decisionFiltersEl.querySelectorAll('[data-decision]').forEach(b => b.classList.remove('active'));
        topicFiltersEl.querySelectorAll('[data-topic]').forEach(b => b.classList.remove('active'));
        updateToggleState();
        render();
    };
    dayFiltersEl.appendChild(clearBtn);

    function updateToggleState() {
        const activeCount = [activeDecision, activeTopic].filter(Boolean).length;
        const hasActiveFilters = activeCount > 0;
        toggleBtn.classList.toggle('has-active', hasActiveFilters);
        if (filtersOpen) {
            toggleBtn.innerHTML = 'Filters ▴';
        } else if (hasActiveFilters) {
            toggleBtn.innerHTML = 'Filters ▾ (' + activeCount + ')';
        } else {
            toggleBtn.innerHTML = 'Filters ▾';
        }
        clearBtn.style.display = hasActiveFilters ? 'inline-block' : 'none';
        sessionFilterEl.classList.toggle('active', !!activeSession);
        sessionFilterValueEl.textContent = activeSession;
        if (activeSimilarTo) {
            const sourcePaper = DATA.find(d => d.id === activeSimilarTo);
            similarFilterEl.classList.add('active');
            similarFilterValueEl.textContent = sourcePaper
                ? (sourcePaper.num || '#' + sourcePaper.id) + ' — ' + sourcePaper.title.slice(0, 50) + '…'
                : '#' + activeSimilarTo;
        } else {
            similarFilterEl.classList.remove('active');
        }
    }

    // Decision type filters (Oral, Poster, Spotlight)
    const decisions = [...new Set(DATA.map(d => d.decision).filter(Boolean))];
    const decisionOrder = ['Oral', 'Spotlight', 'Poster'];
    decisions.sort((a, b) => decisionOrder.indexOf(a) - decisionOrder.indexOf(b));

    decisions.forEach(dec => {
        const btn = document.createElement('button');
        btn.className = 'filter-chip small';
        btn.dataset.decision = dec;
        btn.textContent = dec;
        btn.onclick = () => {
            activeDecision = activeDecision === dec ? '' : dec;
            decisionFiltersEl.querySelectorAll('[data-decision]').forEach(b => b.classList.toggle('active', b.dataset.decision === activeDecision));
            updateToggleState();
            render();
        };
        decisionFiltersEl.appendChild(btn);
    });

    // Topic filters - extract main category from "Computer Vision->Everything Else" format
    const topicMap = new Map();
    DATA.forEach(d => {
        if (d.topic_category) {
            topicMap.set(d.topic_category, d.topic_category);
        }
    });
    const topics = [...topicMap.keys()].sort();

    topics.forEach(topic => {
        const btn = document.createElement('button');
        btn.className = 'filter-chip small';
        btn.dataset.topic = topic;
        btn.textContent = topic.length > 25 ? topic.slice(0, 23) + '…' : topic;
        btn.title = topic;
        btn.onclick = () => {
            activeTopic = activeTopic === topic ? '' : topic;
            topicFiltersEl.querySelectorAll('[data-topic]').forEach(b => b.classList.toggle('active', b.dataset.topic === activeTopic));
            updateToggleState();
            render();
        };
        topicFiltersEl.appendChild(btn);
    });

    function escapeHtml(s) {
        if (!s) return '';
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function highlight(text, words, useWordBoundary, caseSensitive) {
        if (!words.length || !text) return escapeHtml(text);
        let result = escapeHtml(text);
        const flags = caseSensitive ? 'g' : 'gi';
        words.forEach(w => {
            const escaped = w.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
            const pattern = useWordBoundary ? '\\\\b(' + escaped + ')\\\\b' : '(' + escaped + ')';
            const re = new RegExp(pattern, flags);
            result = result.replace(re, '<mark>$1</mark>');
        });
        return result;
    }

    function getSnippet(text, words, useWordBoundary, caseSensitive) {
        if (!words.length || !text) return '';
        const contextChars = 45;
        for (const word of words) {
            const escaped = word.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
            const pattern = useWordBoundary ? '\\\\b' + escaped + '\\\\b' : escaped;
            const re = new RegExp(pattern, caseSensitive ? '' : 'i');
            const match = text.match(re);
            if (match) {
                const idx = match.index;
                const matchText = match[0];
                let start = Math.max(0, idx - contextChars);
                let end = Math.min(text.length, idx + matchText.length + contextChars);
                while (start > 0 && text[start - 1] !== ' ') start--;
                while (end < text.length && text[end] !== ' ') end++;
                let snippet = text.slice(start, end).trim();
                const prefix = start > 0 ? '…' : '';
                const suffix = end < text.length ? '…' : '';
                const highlightedSnippet = highlight(snippet, [word], useWordBoundary, caseSensitive);
                return prefix + highlightedSnippet + suffix;
            }
        }
        return '';
    }

    function formatAbstract(text, words, useWordBoundary, caseSensitive) {
        if (!text) return '<div class="no-abstract-notice">No abstract available</div>';
        return '<div class="abstract-text"><p>' + highlight(text, words, useWordBoundary, caseSensitive) + '</p></div>';
    }

    function toggleStar(id, event) {
        event.stopPropagation();
        if (starred.has(id)) {
            starred.delete(id);
        } else {
            starred.add(id);
        }
        localStorage.setItem('neurips__YEAR___starred', JSON.stringify([...starred]));
        render();
    }

    function toggleStarredOnly() {
        showStarredOnly = !showStarredOnly;
        starredBtn.classList.toggle('active', showStarredOnly);
        render();
    }

    function filterByDecision(decision) {
        activeDecision = activeDecision === decision ? '' : decision;
        decisionFiltersEl.querySelectorAll('[data-decision]').forEach(b => b.classList.toggle('active', b.dataset.decision === activeDecision));
        if (!filtersOpen && activeDecision) {
            filtersOpen = true;
            filtersExpandedEl.classList.add('open');
        }
        updateToggleState();
        render();
    }

    function filterBySession(session) {
        activeSession = activeSession === session ? '' : session;
        updateToggleState();
        render();
    }

    function clearSessionFilter() {
        activeSession = '';
        updateToggleState();
        render();
    }

    function showSimilar(paperId) {
        activeSession = '';
        activeSimilarTo = paperId;
        updateToggleState();
        render();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function clearSimilarFilter() {
        activeSimilarTo = null;
        updateToggleState();
        render();
    }

    function render() {
        const useWordBoundary = wordBoundaryEl.checked;
        const caseSensitive = caseSensitiveEl.checked;
        const query = caseSensitive ? searchEl.value.trim() : searchEl.value.toLowerCase().trim();
        const words = query.split(/\\s+/).filter(w => w.length > 1);

        let filtered = DATA;

        if (showStarredOnly) {
            filtered = filtered.filter(d => starred.has(d.id));
        }
        if (activeDecision) {
            filtered = filtered.filter(d => d.decision === activeDecision);
        }
        if (activeDay) {
            filtered = filtered.filter(d => getDay(d.datetime) === activeDay);
        }
        if (activeTopic) {
            filtered = filtered.filter(d => d.topic_category === activeTopic);
        }
        if (activeSession) {
            filtered = filtered.filter(d => d.session === activeSession);
        }
        if (activeSimilarTo && SIMILAR[activeSimilarTo]) {
            const similarIds = new Set(SIMILAR[activeSimilarTo]);
            filtered = filtered.filter(d => similarIds.has(d.id));
        }
        if (words.length) {
            filtered = filtered.filter(d => {
                const searchable = caseSensitive
                    ? (d.title + ' ' + d.text + ' ' + d.session + ' ' + d.authors)
                    : (d.title + ' ' + d.text + ' ' + d.session + ' ' + d.authors).toLowerCase();
                return words.every(w => {
                    const escaped = w.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
                    const pattern = useWordBoundary ? '\\\\b' + escaped + '\\\\b' : escaped;
                    const re = new RegExp(pattern, caseSensitive ? '' : 'i');
                    return re.test(searchable);
                });
            });
        }

        // Sort: by similarity order if showing similar, otherwise by datetime
        if (activeSimilarTo && SIMILAR[activeSimilarTo]) {
            const order = SIMILAR[activeSimilarTo];
            filtered.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
        } else {
            filtered.sort((a, b) => (a.datetime || '').localeCompare(b.datetime || ''));
        }

        const withAbstract = filtered.filter(d => d.has_abstract).length;
        statsEl.textContent = `${filtered.length} papers (${withAbstract} with abstracts)`;
        starredBtn.textContent = '★ ' + starred.size;

        if (filtered.length === 0) {
            resultsEl.innerHTML = '<div class="empty"><h3>No results</h3><p>' +
                (showStarredOnly ? 'No saved papers yet. Tap ★ to save.' : 'Try different search terms') + '</p></div>';
            return;
        }

        const display = filtered.slice(0, 100);
        resultsEl.innerHTML = display.map((d, i) => `
            <div class="card${starred.has(d.id) ? ' is-starred' : ''}" data-id="${d.id}" data-index="${i}">
                <div class="card-header">
                    <div class="card-header-left">
                        <span class="card-num">${escapeHtml(d.num) || '#' + d.id}</span>
                        <button class="card-star-btn" onclick="toggleStar(${d.id}, event)" title="Star">★</button>
                    </div>
                    <span class="card-datetime">${escapeHtml(formatDatetime(d.datetime))}${d.room ? '<br>' + escapeHtml(d.room) : ''}</span>
                </div>
                <div class="card-title" onclick="toggleCard(this.parentElement)">${highlight(d.title, words, useWordBoundary, caseSensitive)}</div>
                <div class="card-meta">
                    <button class="tag decision ${d.decision.toLowerCase()}" onclick="filterByDecision('${escapeHtml(d.decision)}')">${escapeHtml(d.decision)}</button>
                    ${d.topic_category ? '<button class="tag" onclick="activeTopic=activeTopic===\\'' + escapeHtml(d.topic_category) + '\\'?\\'\\':' + '\\'' + escapeHtml(d.topic_category) + '\\';topicFiltersEl.querySelectorAll(\\'[data-topic]\\').forEach(b=>b.classList.toggle(\\'active\\',b.dataset.topic===activeTopic));updateToggleState();render();">' + escapeHtml(d.topic_category) + '</button>' : ''}
                    ${d.session ? '<button class="tag" onclick="filterBySession(\\'' + escapeHtml(d.session.replace(/'/g, "\\\\'")) + '\\')">' + escapeHtml(d.session.slice(0, 35)) + (d.session.length > 35 ? '…' : '') + '</button>' : ''}
                    ${!d.has_abstract ? '<span class="tag no-abstract">No Abstract</span>' : ''}
                </div>
                ${words.length && d.text ? (() => { const s = getSnippet(d.text, words, useWordBoundary, caseSensitive); return s ? '<div class="card-snippet">' + s + '</div>' : ''; })() : ''}
                <div class="card-authors">${highlight(d.authors, words, useWordBoundary, caseSensitive) || 'Authors not available'}</div>
                <div class="card-body">
                    ${d.keywords && d.keywords.length ? '<div class="keywords-section"><span class="section-label">Keywords</span><div class="keywords-list">' + d.keywords.map(k => '<span class="keyword-tag">' + escapeHtml(k) + '</span>').join('') + '</div></div>' : ''}
                    ${formatAbstract(d.text, words, useWordBoundary, caseSensitive)}
                    <div class="card-footer">
                        <div style="display: flex; gap: 12px; align-items: center;">
                            ${d.url ? '<a class="card-link" href="' + d.url + '" target="_blank" rel="noopener">View on OpenReview ↗</a>' : ''}
                            ${SIMILAR[d.id] ? '<button class="find-similar-btn" onclick="showSimilar(' + d.id + ')">Find Similar</button>' : ''}
                        </div>
                        <div class="card-actions">
                            <button class="icon-btn ${starred.has(d.id) ? 'starred' : ''}" onclick="toggleStar(${d.id}, event)" title="Save">★</button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('') + (filtered.length > 100 ? '<div class="empty"><p>Showing first 100 of ' + filtered.length + ' results. Narrow your search to see more.</p></div>' : '');

        focusedIndex = -1;
    }

    function toggleCard(card) {
        const wasExpanded = card.classList.contains('expanded');
        document.querySelectorAll('.card.expanded').forEach(c => c.classList.remove('expanded'));
        if (!wasExpanded) {
            card.classList.add('expanded');
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
            if (e.key === 'Escape') {
                e.target.blur();
            }
            return;
        }

        const cards = [...document.querySelectorAll('.card')];

        if (e.key === '/') {
            e.preventDefault();
            searchEl.focus();
        } else if (e.key === 'j' || e.key === 'ArrowDown') {
            e.preventDefault();
            focusedIndex = Math.min(focusedIndex + 1, cards.length - 1);
            updateFocus(cards);
        } else if (e.key === 'k' || e.key === 'ArrowUp') {
            e.preventDefault();
            focusedIndex = Math.max(focusedIndex - 1, 0);
            updateFocus(cards);
        } else if (e.key === 'Enter' || e.key === 'o') {
            if (focusedIndex >= 0 && cards[focusedIndex]) {
                toggleCard(cards[focusedIndex]);
            }
        } else if (e.key === 's') {
            if (focusedIndex >= 0 && cards[focusedIndex]) {
                const id = parseInt(cards[focusedIndex].dataset.id);
                toggleStar(id, e);
            }
        }
    });

    function updateFocus(cards) {
        cards.forEach((c, i) => c.classList.toggle('focused', i === focusedIndex));
        if (cards[focusedIndex]) {
            cards[focusedIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    // Event listeners
    let debounce;
    searchEl.addEventListener('input', () => {
        clearTimeout(debounce);
        debounce = setTimeout(render, 100);
    });
    wordBoundaryEl.addEventListener('change', render);
    caseSensitiveEl.addEventListener('change', render);

    // Initial render
    render();
    </script>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description="Build offline HTML viewer for NeurIPS papers")
    parser.add_argument("--year", type=int, default=2025,
                        help="NeurIPS year to build viewer for (default: 2025)")
    args = parser.parse_args()

    year = args.year
    output_file = DATA_DIR / "index.html"

    print(f"Loading NeurIPS {year} papers...")
    papers = load_neurips(year)
    print(f"Loaded {len(papers)} papers")

    with_abstract = sum(1 for p in papers if p['has_abstract'])
    print(f"  {with_abstract} with abstract content")
    print(f"  {len(papers) - with_abstract} without abstracts")

    # Count by decision type
    decision_counts = {}
    for p in papers:
        dec = p.get('decision', 'Unknown')
        decision_counts[dec] = decision_counts.get(dec, 0) + 1
    for dec, count in sorted(decision_counts.items()):
        print(f"  {count} {dec}")

    # Load similarity data if available
    similarity = load_similarity(year)
    if similarity:
        print(f"  {len(similarity)} papers with similarity data")
    else:
        print("  No similarity data found (run enrich_embeddings.py to generate)")

    data_json = json.dumps(papers, separators=(',', ':'))
    similarity_json = json.dumps(similarity, separators=(',', ':'))
    html = HTML_TEMPLATE.replace('__DATA_PLACEHOLDER__', data_json)
    html = html.replace('__SIMILAR_PLACEHOLDER__', similarity_json)
    html = html.replace('__YEAR__', str(year))

    output_file.write_text(html)
    size_mb = output_file.stat().st_size / 1024 / 1024
    print(f"Created {output_file} ({size_mb:.1f} MB)")


if __name__ == '__main__':
    main()
