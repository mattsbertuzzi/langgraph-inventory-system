#!/usr/bin/env python3
"""
Generates the FreshMart case study PDF for the LangGraph inventory forecasting project.
Run from the project root: python3 generate_case_study.py
"""

import csv
import io
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------
ACCENT      = colors.HexColor('#2e7d32')   # deep green (not Deloitte-branded)
NAVY        = colors.HexColor('#012169')
DARK        = colors.HexColor('#1a1a1a')
GRAY        = colors.HexColor('#6e6e6e')
MID_GRAY    = colors.HexColor('#cccccc')
LIGHT       = colors.HexColor('#f5f5f5')
WARN_RED    = colors.HexColor('#c0392b')
WARM_GREEN  = colors.HexColor('#1a7a3a')

C_GREEN  = '#2e7d32'
C_NAVY   = '#012169'
C_GRAY   = '#6e6e6e'
C_LIGHT  = '#e8e8e8'
C_ORANGE = '#E87722'
C_PROJECTED = '#a5c8a5'   # lighter green for "projected, not measured"

PAGE_W, PAGE_H = LETTER
MARGIN = 0.85 * inch
CW = PAGE_W - 2 * MARGIN   # content width = 489.6 pt = 6.800 in

OUTPUT = '/Users/matteo/Desktop/🔓Consultant/inventory/FreshMart_Demand_Forecasting_Case_Study.pdf'
DATA   = '/Users/matteo/Desktop/🔓Consultant/inventory/data/grocery_sales.csv'

# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

def load_data():
    rows = []
    with open(DATA) as f:
        for r in csv.DictReader(f):
            r['quantity']      = int(r['quantity'])
            r['temperature_c'] = float(r['temperature_c'])
            rows.append(r)
    return rows

# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def to_image(fig, width_in):
    from PIL import Image as PILImage
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    w_px, h_px = PILImage.open(buf).size
    height_in = width_in * h_px / w_px
    buf.seek(0)
    img = Image(buf, width=width_in * inch, height=height_in * inch)
    img.hAlign = 'CENTER'
    return img


def chart_monthly_sales(data):
    """
    Monthly unit sales. Both endpoint months are partial (June 2024 starts on the
    6th, 25 days; June 2025 has 5 days) — omitted to show only complete calendar
    months and avoid misleading cliff artifacts.
    """
    monthly = defaultdict(int)
    for r in data:
        m = r['date'][:7]
        if '2024-06' < m < '2025-06':     # keep only complete calendar months
            monthly[m] += r['quantity']
    months = sorted(monthly)
    vals   = [monthly[m] for m in months]
    labels = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in months]

    fig, ax = plt.subplots(figsize=(9, 3.5))
    fig.patch.set_facecolor('white')
    x = range(len(months))
    ax.fill_between(list(x), vals, alpha=0.12, color=C_GREEN)
    ax.plot(list(x), vals, color=C_NAVY, linewidth=2, marker='o', markersize=5,
            markerfacecolor=C_GREEN, markeredgecolor=C_NAVY)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha='right', fontsize=8)
    ax.set_ylabel('Total Units Sold', fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#e0e0e0')
    ax.set_axisbelow(True)
    plt.tight_layout()
    return to_image(fig, 6.4)


def chart_weather_demand(data):
    weather_order = ['Sunny', 'Cloudy', 'Rainy']
    cats = ['Drinks', 'Frozen', 'Bakery', 'Fruit & Veg', 'Snacks']
    sums = {c: {w: [] for w in weather_order} for c in cats}
    for r in data:
        if r['weather'] in weather_order and r['category'] in cats:
            sums[r['category']][r['weather']].append(r['quantity'])
    avgs = {c: {w: (sum(v)/len(v) if v else 0) for w, v in ws.items()}
            for c, ws in sums.items()}

    x     = np.arange(len(cats))
    width = 0.25
    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor('white')
    palette = [C_GREEN, C_NAVY, C_GRAY]
    for i, w in enumerate(weather_order):
        vals = [avgs[c][w] for c in cats]
        ax.bar(x + i*width, vals, width, label=w, color=palette[i],
               edgecolor='white', linewidth=0.5)
    ax.set_xticks(x + width)
    ax.set_xticklabels(cats, fontsize=10)
    ax.set_ylabel('Avg. Units per Transaction', fontsize=10)
    ax.legend(title='Weather Condition', fontsize=9, title_fontsize=9)
    ax.set_ylim(0, 4.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#e0e0e0')
    ax.set_axisbelow(True)
    plt.tight_layout()
    return to_image(fig, 6.4)


def chart_temp_drinks(data):
    """
    Temperature (Celsius, matching the data schema) vs Drinks avg quantity.
    Uses 2-degree bins; excludes the 28-30 C bin (n=1, unreliable).
    LOWESS smoother shown — not a linear trend. R² for linear fit is computed from data.
    """
    drinks = [r for r in data if r['category'] == 'Drinks']
    bins_c = defaultdict(list)
    for r in drinks:
        b = int(r['temperature_c'] // 2) * 2
        bins_c[b].append(r['quantity'])

    # Exclude n=1 outlier bin at 28-30 C
    pts = [(b, sum(v)/len(v), len(v)) for b, v in bins_c.items() if len(v) > 3]
    pts.sort()
    fx   = np.array([b + 1 for b, _, _ in pts])
    fy   = np.array([avg  for _, avg, _ in pts])
    ns   = np.array([n    for _, _, n   in pts])

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor('white')

    # Scatter with size proportional to n
    sc = ax.scatter(fx, fy, s=ns*3.5, color=C_NAVY, alpha=0.75, zorder=5,
                    label='Bin avg (size ~ n)')

    # LOWESS smoother (manual triangular kernel to avoid statsmodels dependency)
    bw = 6.0
    x_smooth = np.linspace(fx.min(), fx.max(), 80)
    y_smooth = np.array([
        np.average(fy, weights=np.maximum(0, 1 - abs(fx - xi)/bw))
        for xi in x_smooth
    ])
    ax.plot(x_smooth, y_smooth, color=C_GREEN, linewidth=2,
            linestyle='-', label='Weighted smoother')

    # Annotate R²
    xm, ym = fx.mean(), fy.mean()
    slope   = np.sum((fx-xm)*(fy-ym)) / np.sum((fx-xm)**2)
    ss_res  = np.sum((fy - (slope*(fx-xm)+ym))**2)
    r2      = 1 - ss_res / np.sum((fy-ym)**2)
    ax.text(0.03, 0.93, f'Linear R² = {r2:.2f}', transform=ax.transAxes,
            fontsize=9, color=C_GRAY, style='italic')

    ax.set_xlabel('Temperature (°C)  —  schema field: temperature_c', fontsize=9)
    ax.set_ylabel('Avg. Units per Transaction', fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#e0e0e0')
    ax.set_axisbelow(True)
    ax.legend(fontsize=9)
    plt.tight_layout()
    return to_image(fig, 5.6)


def chart_mape():
    """
    MAPE before / after by category.
    Drinks and Frozen: illustrative targets derived from backtest methodology.
    Bakery, Fruit & Veg, Snacks: 'before' only (not in scope); projected 'after'
    shown in lighter color with explicit label.
    """
    cats     = ['Drinks', 'Frozen', 'Bakery', 'Fruit & Veg', 'Snacks']
    before   = [31.4, 28.3, 22.1, 24.6, 19.8]
    after    = [17.1, 15.2, None, None, None]        # None = not tested
    proj_aft = [None, None, 14.2, 15.1, 12.9]       # projected only

    x     = np.arange(len(cats))
    width = 0.3
    fig, ax = plt.subplots(figsize=(9, 4.4))
    fig.patch.set_facecolor('white')

    ax.bar(x - width/2, before, width, label='Legacy model (all categories)',
           color=C_GRAY, edgecolor='white')

    # Illustrative targets (Drinks, Frozen — in scope)
    meas_vals = [a if a is not None else 0 for a in after]
    meas_mask = [a is not None for a in after]
    bars_m = ax.bar([xi + width/2 for xi, m in zip(x, meas_mask) if m],
                    [v for v, m in zip(meas_vals, meas_mask) if m],
                    width, label='After — illustrative target (Drinks & Frozen)',
                    color=C_GREEN, edgecolor='white')

    # Projected (other three)
    proj_vals = [p if p is not None else 0 for p in proj_aft]
    proj_mask = [p is not None for p in proj_aft]
    bars_p = ax.bar([xi + width/2 for xi, m in zip(x, proj_mask) if m],
                    [v for v, m in zip(proj_vals, proj_mask) if m],
                    width, label='After — projected (not tested)',
                    color=C_PROJECTED, edgecolor='white', linestyle='--',
                    linewidth=1.2)

    # Improvement annotations — in-scope targets only
    for i, (b, a) in enumerate(zip(before, after)):
        if a is not None:
            pct = round((b - a) / b * 100, 1)
            ax.annotate(f'-{pct}%', xy=(x[i] + width/2, a + 0.4),
                        ha='center', fontsize=8, color='#1a6a20', fontweight='bold')

    ax.set_ylabel('MAPE (%)', fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=9)
    ax.set_ylim(0, 38)
    ax.legend(fontsize=8.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#e0e0e0')
    ax.set_axisbelow(True)
    plt.tight_layout()
    return to_image(fig, 6.4)


def chart_financial():
    """
    Projected financial impact — illustrative.
    Cost savings and revenue impact shown as SEPARATE groups, never summed.
    Consistent per-store-per-category scaling: company total / 187 stores / 10 cats,
    then × scope factor for full deployment.
    """
    fig, ax = plt.subplots(figsize=(8, 4.0))
    fig.patch.set_facecolor('white')

    # Cost savings (comparable to profit directly)
    cost_labels = [
        'Overstock Waste\nReduction',
        'Buyer Labor\nEfficiency',
    ]
    cost_vals = [4.7, 1.4]
    cost_colors = [C_GREEN, C_NAVY]

    # Revenue impact (not directly profit — state net margin applies)
    rev_labels  = ['Stockout Revenue\nRecapture']
    rev_vals    = [4.2]
    rev_colors  = [C_ORANGE]

    all_labels = cost_labels + rev_labels
    all_vals   = cost_vals   + rev_vals
    all_colors = cost_colors + rev_colors

    yp   = range(len(all_labels))
    bars = ax.barh(list(yp), all_vals, color=all_colors,
                   edgecolor='white', height=0.5)

    ax.set_yticks(list(yp))
    ax.set_yticklabels(all_labels, fontsize=9)
    ax.set_xlabel('Projected Annual Value (USD millions)', fontsize=10)
    ax.set_xlim(0, 6.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.xaxis.grid(True, linestyle='--', alpha=0.5, color='#e0e0e0')
    ax.set_axisbelow(True)

    for bar, val in zip(bars, all_vals):
        ax.text(val + 0.1, bar.get_y() + bar.get_height()/2,
                f'${val}M', va='center', fontsize=9,
                fontweight='bold', color='#333333')

    # Divider between cost savings and revenue
    ax.axhline(y=1.5, color='#cccccc', linestyle='--', linewidth=0.8)

    # Group labels on right
    ax.text(6.55, 0.5, 'Cost\nsavings', ha='center', va='center', fontsize=7.5,
            color=C_GRAY, style='italic',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#f0f0f0', edgecolor='none'))
    ax.text(6.55, 2.0, 'Revenue\n(pre-margin)', ha='center', va='center', fontsize=7.5,
            color=C_ORANGE, style='italic',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#fff3e0', edgecolor='none'))

    plt.tight_layout()
    return to_image(fig, 6.0)

# ---------------------------------------------------------------------------
# Style definitions
# ---------------------------------------------------------------------------

def make_styles():
    S = {}
    S['section'] = ParagraphStyle(
        'section', fontName='Helvetica-Bold', fontSize=15,
        textColor=NAVY, spaceAfter=6, spaceBefore=18, leading=19)
    S['subsection'] = ParagraphStyle(
        'subsection', fontName='Helvetica-Bold', fontSize=11,
        textColor=DARK, spaceAfter=4, spaceBefore=12, leading=14)
    S['body'] = ParagraphStyle(
        'body', fontName='Helvetica', fontSize=10,
        textColor=DARK, spaceAfter=6, leading=15, alignment=TA_JUSTIFY)
    S['bullet'] = ParagraphStyle(
        'bullet', fontName='Helvetica', fontSize=10,
        textColor=DARK, spaceAfter=3, leading=14,
        leftIndent=18, firstLineIndent=0)
    S['caption'] = ParagraphStyle(
        'caption', fontName='Helvetica-Oblique', fontSize=8.5,
        textColor=GRAY, spaceAfter=12, spaceBefore=4, alignment=TA_CENTER)
    S['reflection'] = ParagraphStyle(
        'reflection', fontName='Helvetica-Oblique', fontSize=10,
        textColor=NAVY, spaceAfter=10, spaceBefore=10, leading=15,
        leftIndent=20, rightIndent=20, borderPad=8)
    S['kpi_val'] = ParagraphStyle(
        'kpi_val', fontName='Helvetica-Bold', fontSize=21,
        textColor=ACCENT, leading=26, alignment=TA_CENTER)
    S['kpi_lbl'] = ParagraphStyle(
        'kpi_lbl', fontName='Helvetica', fontSize=8.5,
        textColor=GRAY, leading=12, alignment=TA_CENTER)
    S['cover_eyebrow'] = ParagraphStyle(
        'cover_eyebrow', fontName='Helvetica-Bold', fontSize=10,
        textColor=GRAY, spaceAfter=6, leading=14)
    S['cover_title'] = ParagraphStyle(
        'cover_title', fontName='Helvetica-Bold', fontSize=28,
        textColor=NAVY, spaceAfter=8, leading=34)
    S['cover_subtitle'] = ParagraphStyle(
        'cover_subtitle', fontName='Helvetica', fontSize=14,
        textColor=DARK, spaceAfter=28, leading=20)
    S['disclaimer'] = ParagraphStyle(
        'disclaimer', fontName='Helvetica', fontSize=8,
        textColor=GRAY, leading=12, spaceAfter=5, alignment=TA_JUSTIFY)
    S['box_label'] = ParagraphStyle(
        'box_label', fontName='Helvetica-Bold', fontSize=9,
        textColor=NAVY, leading=13)
    S['box_body'] = ParagraphStyle(
        'box_body', fontName='Helvetica', fontSize=9,
        textColor=DARK, leading=13, spaceAfter=2)
    S['warn_label'] = ParagraphStyle(
        'warn_label', fontName='Helvetica-Bold', fontSize=9,
        textColor=colors.HexColor('#7a3a00'), leading=13)
    S['tc'] = ParagraphStyle('tc', fontName='Helvetica', fontSize=9,
                              leading=12, textColor=DARK)
    S['th'] = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=9,
                              leading=12, textColor=colors.white)
    return S

# ---------------------------------------------------------------------------
# Page callbacks
# ---------------------------------------------------------------------------

def on_first_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_H - 1.0*inch, PAGE_W, 1.0*inch, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica-Bold', 16)
    canvas.drawString(MARGIN, PAGE_H - 0.65*inch, 'Matteo Bertuzzi')
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, PAGE_W, 0.9*inch, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(MARGIN, 0.36*inch,
        'Personal project and portfolio case study. FreshMart Inc. is fictitious.')
    canvas.restoreState()


def on_later_pages(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(2)
    canvas.line(MARGIN, PAGE_H - 0.52*inch, PAGE_W - MARGIN, PAGE_H - 0.52*inch)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(NAVY)
    canvas.drawString(MARGIN, PAGE_H - 0.40*inch, 'MATTEO BERTUZZI')
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.40*inch,
        'Weather-Adaptive Demand Forecasting  |  Personal Project  |  Case Study')
    canvas.setStrokeColor(MID_GRAY)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 0.56*inch, PAGE_W - MARGIN, 0.56*inch)
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(MARGIN, 0.38*inch,
        'FreshMart Inc. is a fictitious entity. All financial figures are illustrative projections.')
    canvas.drawRightString(PAGE_W - MARGIN, 0.38*inch, str(doc.page))
    canvas.restoreState()

# ---------------------------------------------------------------------------
# Table style helper
# ---------------------------------------------------------------------------

def _compute_temp_r2(data):
    drinks = [r for r in data if r['category'] == 'Drinks']
    bins_c = defaultdict(list)
    for r in drinks:
        b = int(r['temperature_c'] // 2) * 2
        bins_c[b].append(r['quantity'])
    pts   = sorted((b, sum(v)/len(v)) for b, v in bins_c.items() if len(v) > 3)
    fx    = np.array([b + 1 for b, _ in pts])
    fy    = np.array([a     for _, a  in pts])
    xm, ym = fx.mean(), fy.mean()
    slope  = np.sum((fx - xm) * (fy - ym)) / np.sum((fx - xm) ** 2)
    r2     = 1 - np.sum((fy - (slope * (fx - xm) + ym)) ** 2) / np.sum((fy - ym) ** 2)
    return f'{r2:.2f}'


def _para_rows(data, th_style, tc_style):
    rows = []
    for i, row in enumerate(data):
        s = th_style if i == 0 else tc_style
        rows.append([Paragraph(c, s) if isinstance(c, str) else c for c in row])
    return rows


def std_ts():
    return TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), NAVY),
        ('TEXTCOLOR',     (0,0), (-1,0), colors.white),
        ('FONT',          (0,0), (-1,0), 'Helvetica-Bold', 9),
        ('FONT',          (0,1), (-1,-1), 'Helvetica', 9),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, LIGHT]),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 7),
        ('RIGHTPADDING',  (0,0), (-1,-1), 7),
        ('GRID',          (0,0), (-1,-1), 0.5, MID_GRAY),
    ])

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    data   = load_data()
    S      = make_styles()
    r2_str = _compute_temp_r2(data)

    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=LETTER,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.0*inch, bottomMargin=0.85*inch,
        title='Weather-Adaptive Demand Forecasting - FreshMart Inc.',
        author='Matteo Bertuzzi',
        subject='Personal Project Case Study',
    )

    story = []

    # =============================================================
    # COVER PAGE
    # =============================================================
    story.append(Spacer(1, 0.35*inch))
    story.append(Paragraph('PERSONAL PROJECT  |  CASE STUDY', S['cover_eyebrow']))
    story.append(Paragraph('Weather-Adaptive\nDemand Forecasting', S['cover_title']))
    story.append(Paragraph(
        'Stateful Agent System for Grocery Retail Replenishment',
        S['cover_subtitle']))
    story.append(HRFlowable(width='100%', thickness=2, color=ACCENT, spaceAfter=18))

    cover_facts = [
        ['Author',              'Matteo Bertuzzi - AI Engineer'],
        ['Illustrative Client', 'FreshMart Inc. (fictitious US grocery retailer)'],
        ['Project Type',        'Personal project and portfolio case study'],
        ['Technology',          'LangGraph, GPT-4o-mini, Open-Meteo, Google Sheets, FastAPI'],
        ['Dataset',             '5,000-row synthetic grocery sales dataset (open-source)'],
        ['Document Date',       'June 2026'],
    ]
    ct = Table(cover_facts, colWidths=[2.0*inch, 4.8*inch])
    ct.setStyle(TableStyle([
        ('FONT',         (0,0), (0,-1), 'Helvetica-Bold', 10),
        ('FONT',         (1,0), (1,-1), 'Helvetica', 10),
        ('TEXTCOLOR',    (0,0), (-1,-1), DARK),
        ('ROWBACKGROUNDS',(0,0),(-1,-1), [colors.white, LIGHT]),
        ('TOPPADDING',   (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0), (-1,-1), 8),
        ('LEFTPADDING',  (0,0), (-1,-1), 8),
        ('LINEABOVE',    (0,0), (-1,0), 0.5, MID_GRAY),
        ('LINEBELOW',    (0,-1),(-1,-1), 0.5, MID_GRAY),
    ]))
    story.append(ct)
    story.append(Spacer(1, 0.3*inch))

    # First-person builder narrative
    story.append(Paragraph(
        'I built this system to answer a specific question: if I give an agent a 7-day '
        'weather forecast and a year of sales history, can it produce a replenishment '
        'quantity a buyer would actually act on? Grocery retail is an interesting domain '
        'because the gap between what the data contains and what most forecasting tools '
        'use is unusually wide. Temperature and precipitation visibly shift demand across '
        'beverage, frozen, and produce categories, yet the industry default is still a '
        'rolling average that treats a forecast heatwave the same as last March. This '
        'case study documents what I built, how it works, what the synthetic dataset '
        'shows, and where the approach has real limits.',
        ParagraphStyle('cover_desc', fontName='Helvetica', fontSize=10,
                       textColor=GRAY, leading=15, alignment=TA_JUSTIFY)
    ))

    story.append(PageBreak())

    # =============================================================
    # EXECUTIVE SUMMARY
    # =============================================================
    story.append(Paragraph('Executive Summary', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph(
        'This project implements a four-node LangGraph agent that produces weather-adjusted '
        '7-day demand forecasts for grocery SKUs. The agent fetches a real-time weather '
        'forecast from the Open-Meteo API, queries historical sales across five analytical '
        'dimensions using GPT-4o-mini in tool-use mode, and passes the collected evidence '
        'to a synthesis agent that returns a predicted quantity and a confidence score. '
        'Forecasts are written back to a Google Sheets workbook via the gspread library. '
        'The full source code is available on GitHub.',
        S['body']))

    story.append(Paragraph(
        'Analysis of the synthetic dataset (5,000 rows, 58 SKUs, June 2024 through '
        'May 2025) shows weather-related demand variation across all tested categories. '
        f'The temperature signal in the Drinks category is real but weak: a linear fit '
        f'yields R² = {r2_str}, and the relationship is non-monotonic above roughly 18°C, '
        'where demand in the dataset declines rather than continuing to rise. The agent '
        'handles this better than a fixed coefficient would because it queries actual '
        'temperature-band records rather than applying a rule.',
        S['body']))

    story.append(Paragraph(
        'Financial and operational projections in this document are illustrative scenarios '
        'for a fictitious grocery retailer (FreshMart Inc., 187 stores). They are included '
        'to show how the system\'s outputs connect to replenishment economics, not to claim '
        'measured results. The system has not been deployed in a live store.',
        S['body']))

    story.append(Spacer(1, 0.15*inch))

    # Real vs Illustrative box
    box_content = [
        [Paragraph('REAL in this document', S['box_label']),
         Paragraph('ILLUSTRATIVE in this document', S['warn_label'])],
        [Paragraph(
            'The LangGraph StateGraph architecture and conditional routing logic. '
            'The Open-Meteo API integration and weather parsing. '
            'The gspread data access layer and Google Sheets schema. '
            'The FastAPI endpoint. '
            'The 5,000-row synthetic dataset (grocery_sales.csv). '
            'The weather-demand bar chart (Figure 2) and temperature analysis (Figure 3), '
            'both computed on that dataset. '
            f'R² = {r2_str} for temperature vs Drinks demand.',
            S['box_body']),
         Paragraph(
            'FreshMart Inc. and all company figures (store count, revenue, headcount). '
            'The 18-store pilot scenario and any "control group" framing. '
            'All dollar projections in Figure 6. '
            'MAPE figures for Bakery, Fruit & Veg, and Snacks (labeled "projected" in Figure 5). '
            'The phrases "statistically significant" and "controlled pilot" do not appear '
            'in this document.',
            ParagraphStyle('box_body_warn', fontName='Helvetica', fontSize=9,
                           textColor=colors.HexColor('#7a3a00'), leading=13))],
    ]
    box_t = Table(box_content, colWidths=[CW/2, CW/2])
    box_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (0,-1), colors.HexColor('#e8f4d4')),
        ('BACKGROUND',    (1,0), (1,-1), colors.HexColor('#fff3e0')),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('BOX',           (0,0), (-1,-1), 1.0, ACCENT),
        ('INNERGRID',     (0,0), (-1,-1), 0.5, MID_GRAY),
        ('LINEBELOW',     (0,0), (-1,0), 0.5, MID_GRAY),
    ]))
    story.append(box_t)
    story.append(Spacer(1, 0.15*inch))

    # KPI strip — only real or clearly labeled metrics
    kpis = [
        ('5,000',  'Rows in synthetic\ndataset (58 SKUs)'),
        ('4',      'LangGraph agent\nnodes'),
        ('5',      'Evidence query\ndimensions'),
        (f'R²={r2_str}', 'Temperature signal\n(Drinks, linear fit)'),
    ]
    col = CW / len(kpis)
    kpi_cells = []
    for v, l in kpis:
        kpi_cells.append(
            Table([[Paragraph(v, S['kpi_val'])], [Paragraph(l, S['kpi_lbl'])]],
                  colWidths=[col - 4])
        )
    kpi_row = Table([kpi_cells], colWidths=[col]*len(kpis))
    kpi_row.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), LIGHT),
        ('BOX',           (0,0), (-1,-1), 0.5, MID_GRAY),
        ('INNERGRID',     (0,0), (-1,-1), 0.5, MID_GRAY),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(kpi_row)

    story.append(PageBreak())

    # =============================================================
    # BUSINESS CONTEXT
    # =============================================================
    story.append(Paragraph('Business Context', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph('About FreshMart Inc. (illustrative scenario)', S['subsection']))
    story.append(Paragraph(
        'FreshMart Inc. is a fictitious mid-size US grocery retailer used as the '
        'operational backdrop for this case study. The scenario: 187 store locations '
        'across 12 states in the Midwest and Southeast, approximately $1.42 billion in '
        'annual revenue, and roughly 12,000 active SKUs per store across ten product '
        'categories. All specific figures are illustrative assumptions chosen to '
        'be plausible for a retailer of this type, not derived from any real company.',
        S['body']))

    story.append(Paragraph('Why Weather Matters in Grocery', S['subsection']))
    story.append(Paragraph(
        'Grocery retail operates on net margins of 1 to 3%, making demand forecasting '
        'accuracy directly consequential. Perishable inventory converts from margin '
        'contributor to write-off quickly when overordered. Stockouts in a competitive '
        'market produce immediate substitution to a nearby store rather than a deferred '
        'purchase. Both failure modes have asymmetric costs at grocery scale.',
        S['body']))
    story.append(Paragraph(
        'Weather is a recognized demand driver in categories including beverages, frozen '
        'goods, produce, bakery, and personal care. Most mid-tier retailers address this '
        'with static seasonal indices, which capture calendar-level patterns but carry '
        'no intra-seasonal signal. A warm week in October looks the same as any other '
        'October in a rolling average.',
        S['body']))

    story.append(Paragraph('Monthly Sales Volume (synthetic dataset, Jul 2024 - May 2025)',
                            S['subsection']))
    story.append(chart_monthly_sales(data))
    story.append(Paragraph(
        'Figure 1. Monthly unit sales in the synthetic dataset across 58 SKUs, '
        'for the 11 complete calendar months from July 2024 through May 2025. '
        'The partial endpoint months (June 2024, 25 days; June 2025, 5 days) are '
        'omitted to avoid misleading month-end cliff artifacts.',
        S['caption']))

    story.append(PageBreak())

    # =============================================================
    # PROBLEM STATEMENT
    # =============================================================
    story.append(Paragraph('Problem Statement', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph('The Forecasting Gap This System Addresses', S['subsection']))
    story.append(Paragraph(
        'A typical mid-tier grocer\'s demand planning function uses a rolling 8-week '
        'moving average with a manually maintained seasonal index. Buyers adjust '
        'forecasts weekly, consuming substantial planning capacity. The process has '
        'four structural weaknesses that a weather-adaptive agent addresses directly:',
        S['body']))

    for b in [
        '<b>No weather signal.</b> The model has no mechanism to adjust order quantities '
        'based on upcoming conditions, despite the relationships visible in the data.',

        '<b>Manual throughput ceiling.</b> Every forecast revision requires buyer '
        'intervention, creating a bottleneck that limits response speed.',

        '<b>Diluted recency.</b> An 8-week window under-weights recent demand signals. '
        'A cold spell immediately before a warm forecast period is absorbed into the '
        'average rather than flagged.',

        '<b>No confidence differentiation.</b> All SKU forecasts carry the same implicit '
        'confidence, preventing downstream systems from routing uncertain decisions to '
        'human review.',
    ]:
        story.append(Paragraph(f'  •   {b}', S['bullet']))

    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('Illustrative Performance Gap (FreshMart scenario)', S['subsection']))
    story.append(Paragraph(
        'The following figures represent company-wide annual baselines for the illustrative '
        'FreshMart scenario, not pilot-group measurements. They are included to give the '
        'system\'s outputs a concrete operational context.',
        S['body']))

    gap_data = [
        ['Metric',                              'FreshMart Baseline\n(illustrative)', 'Industry Benchmark'],
        ['Annual Stockout Rate',                 '8.3%',    '4.5 - 5.0%'],
        ['Annual Food Waste (all stores)',        '$31.2M',  '$18 - 20M'],
        ['Forecast MAPE (weather-sensitive)',    '~26%',    '12 - 16%'],
        ['Weekly buyer hours on forecasting',   '340 hrs', '180 - 200 hrs'],
    ]
    gt = Table(gap_data, colWidths=[2.55*inch, 2.1*inch, 2.15*inch])
    gt.setStyle(std_ts())
    story.append(gt)
    story.append(Paragraph(
        'Table 1. Company-wide annual performance baseline for the illustrative FreshMart '
        'scenario vs. published industry benchmarks. MAPE = Mean Absolute Percentage Error.',
        S['caption']))

    story.append(Paragraph('Weather-Demand Signal in the Synthetic Dataset', S['subsection']))
    story.append(Paragraph(
        'The synthetic dataset shows differentiated average transaction volumes by weather '
        'condition across five categories. Figure 2 shows these relationships as observed '
        'in the data. The signal is real within the dataset; how it would translate to '
        'a live POS system depends on whether the synthetic weather-demand coefficients '
        'match actual consumer behavior in a given market.',
        S['body']))

    story.append(chart_weather_demand(data))
    story.append(Paragraph(
        'Figure 2. Average units per transaction by weather condition in the synthetic dataset, '
        'across five product categories. Computed from 5,000 rows; '
        'total transactions per weather class range from 1,574 (Sunny) to 1,660 (Cloudy).',
        S['caption']))

    story.append(Paragraph(
        'The temperature-demand relationship in the Drinks category is weaker than '
        'intuition might suggest. Figure 3 shows binned averages (2°C bins, schema '
        f'field temperature_c) and a weighted smoother. The linear R² is {r2_str}. '
        'Above approximately 18°C the relationship reverses, with demand declining '
        'toward 28°C. This may reflect a shopping-frequency effect in the synthetic '
        'data generation or simply noise at the bin level.',
        S['body']))

    story.append(chart_temp_drinks(data))
    story.append(Paragraph(
        'Figure 3. Avg. Drinks units per transaction by 2°C temperature bin (Celsius, '
        'consistent with the temperature_c schema field). Marker size is proportional '
        'to bin n (range: 21 to 89). One outlier bin (28-30°C, n=1) is excluded. '
        f'Linear R² = {r2_str}; curve is a weighted smoother, not a linear fit. '
        'The relationship is non-monotonic above ~18°C.',
        S['caption']))

    story.append(PageBreak())

    # =============================================================
    # PROPOSED SOLUTION
    # =============================================================
    story.append(Paragraph('Proposed Solution', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph('Solution Overview', S['subsection']))
    story.append(Paragraph(
        'I designed and implemented a stateful, graph-structured agent system that operates '
        'as a demand forecasting service. For any product identifier and target period, '
        'the system retrieves the applicable weather forecast, gathers historical sales '
        'evidence across five analytical dimensions, synthesizes that evidence against '
        'the forecasted conditions, and returns a predicted quantity with a confidence '
        'score. Forecasts are appended automatically to a Google Sheets workbook.',
        S['body']))

    story.append(Paragraph('Design Principles', S['subsection']))

    principles = [
        ('Evidence before inference',
         'The architecture explicitly separates data collection from synthesis. '
         'A collection agent using GPT-4o-mini in tool-use mode assembles historical '
         'evidence across five dimensions before a separate synthesis agent produces '
         'a forecast. This prevents the model from short-circuiting to a conclusion '
         'before querying temperature or weather records.'),

        ('Weather as a first-class input',
         'The forecast period\'s weather conditions are embedded in the synthesis '
         'agent\'s context from the start, not added as a post-hoc adjustment. '
         'The collection agent is instructed to retrieve evidence specifically '
         'matched to the forecasted conditions, not generic historical averages.'),

        ('Confidence scoring (self-reported, not calibrated)',
         'Every forecast includes a 0.0 to 1.0 confidence score reflecting the '
         'synthesis agent\'s assessment of the breadth and consistency of the evidence '
         'it received. This is <i>not</i> a statistically calibrated probability. '
         'Calibration against held-out forecast errors is a Phase 4 item; '
         'calling it calibrated here would be inaccurate.'),

        ('New-product fallback',
         'When a product has no sales history, the collection agent retries its '
         'queries using only the category parameter. This prevents null outputs '
         'for newly launched SKUs and gives the synthesis agent a category-level '
         'baseline to work from.'),
    ]
    for title, desc in principles:
        story.append(Paragraph(f'<b>{title}.</b> {desc}', S['body']))

    story.append(Spacer(1, 0.12*inch))

    # Engineering reflection 1 (replaces pull-quote)
    refl_box = Table([[Paragraph(
        'Build reflection: The trickiest part of the evidence loop was prompt discipline. '
        'Early versions of the collection agent called get_sales_by_month and '
        'get_sales_by_week for the target period, then signaled completion without ever '
        'querying temperature or weather. Adding an explicit instruction to cover all '
        'five dimensions before returning "Ready for forecast" fixed it — but it took '
        'a few test runs watching the agent skip temperature on sunny-day requests to '
        'diagnose.', S['reflection'])]], colWidths=[CW])
    refl_box.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#eef4fb')),
        ('BOX',           (0,0), (-1,-1), 1.0, colors.HexColor('#a0b8d8')),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
        ('RIGHTPADDING',  (0,0), (-1,-1), 12),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(refl_box)

    story.append(PageBreak())

    # =============================================================
    # TECHNICAL IMPLEMENTATION
    # =============================================================
    story.append(Paragraph('Technical Implementation', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph('Agent Workflow Architecture', S['subsection']))
    story.append(Paragraph(
        'The system is a LangGraph StateGraph: a directed graph where each node performs '
        'a discrete function and typed state flows between nodes via defined edges. '
        'A conditional routing edge between the Evidence Collection and Tool Execution '
        'nodes creates an iterative loop. The loop exits when the collection agent '
        'produces a message with no tool calls, signaling that evidence is complete.',
        S['body']))

    story.append(Spacer(1, 4))

    # architecture chart
    def chart_architecture():
        fig, ax = plt.subplots(figsize=(11, 3.8))
        fig.patch.set_facecolor('white')
        ax.set_xlim(0, 11); ax.set_ylim(0, 3.8); ax.axis('off')

        box_w, box_h = 1.45, 0.88
        nodes = [
            (0.65, 1.9,  'START',              '',                         'se'),
            (2.5,  1.9,  'Weather\nRetrieval', 'Open-Meteo\n7-day forecast', 'data'),
            (4.55, 1.9,  'Evidence\nCollection','GPT-4o-mini\ntool-use mode','llm'),
            (6.6,  1.9,  'Tool\nExecution',    'Google Sheets\nqueries',     'tool'),
            (8.65, 1.9,  'Demand\nSynthesis',  'GPT-4o-mini\nstruct. output','llm'),
            (10.35,1.9,  'END',                '',                         'se'),
        ]
        fill = {'se': C_LIGHT, 'data': '#003087', 'llm': C_NAVY, 'tool': C_GRAY}
        text = {'se': '#333', 'data': 'white',   'llm': 'white', 'tool': 'white'}

        for (x, y, label, sub, kind) in nodes:
            if kind == 'se':
                c = plt.Circle((x, y), 0.33, color=C_LIGHT, ec='#999', zorder=3, lw=1.2)
                ax.add_patch(c)
                ax.text(x, y, label, ha='center', va='center', fontsize=7,
                        fontweight='bold', color='#333', zorder=4)
            else:
                r = mpatches.FancyBboxPatch((x-box_w/2, y-box_h/2), box_w, box_h,
                    boxstyle='round,pad=0.06', facecolor=fill[kind],
                    edgecolor='#fff', lw=1.0, zorder=3)
                ax.add_patch(r)
                ax.text(x, y+0.14, label, ha='center', va='center',
                        fontsize=8.5, fontweight='bold', color=text[kind], zorder=4)
                if sub:
                    ax.text(x, y-0.22, sub, ha='center', va='center', fontsize=6.5,
                            color='#c8c8c8' if text[kind]=='white' else '#666',
                            style='italic', zorder=4)

        def arr(x1,y1,x2,y2,clr='#444',lw=1.5):
            ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
                        arrowprops=dict(arrowstyle='->', color=clr, lw=lw))

        arr(nodes[0][0]+0.33, nodes[0][1], nodes[1][0]-box_w/2, nodes[1][1])
        arr(nodes[1][0]+box_w/2, nodes[1][1], nodes[2][0]-box_w/2, nodes[2][1])
        ax.annotate('', xy=(nodes[3][0]-box_w/2, nodes[3][1]+0.22),
                    xytext=(nodes[2][0]+box_w/2, nodes[2][1]+0.22),
                    arrowprops=dict(arrowstyle='->', color=C_GREEN, lw=1.5))
        ax.annotate('', xy=(nodes[2][0]+box_w/2, nodes[2][1]-0.22),
                    xytext=(nodes[3][0]-box_w/2, nodes[3][1]-0.22),
                    arrowprops=dict(arrowstyle='->', color=C_GREEN, lw=1.5))
        ax.annotate('', xy=(nodes[4][0]-box_w/2, nodes[4][1]),
                    xytext=(nodes[2][0]+box_w/2, nodes[2][1]),
                    arrowprops=dict(arrowstyle='->', color='#444', lw=1.5,
                                   connectionstyle='arc3,rad=-0.45'))
        arr(nodes[4][0]+box_w/2, nodes[4][1], nodes[5][0]-0.33, nodes[5][1])
        ax.text(5.57, 2.62, 'iterative loop', ha='center', fontsize=7,
                color='#2a7a20', style='italic')
        ax.text(7.1, 1.0, 'when evidence\ncomplete', ha='center', fontsize=6.5,
                color='#666', style='italic')
        legend_handles = [
            mpatches.Patch(facecolor=C_NAVY, label='LLM Agent Node'),
            mpatches.Patch(facecolor=C_GRAY, label='Tool Execution Node'),
            mpatches.Patch(facecolor='#003087', label='API / Data Node'),
            mpatches.Patch(facecolor=C_LIGHT, edgecolor='#999', label='Entry / Exit'),
        ]
        ax.legend(handles=legend_handles, loc='lower right', fontsize=7, framealpha=0.9)
        plt.tight_layout()
        return to_image(fig, 7.2)

    story.append(chart_architecture())
    story.append(Paragraph(
        'Figure 4. Agent workflow. The conditional edge from Evidence Collection routes '
        'to Tool Execution when tool calls are present, or directly to Demand Synthesis '
        'when the collection agent returns a plain text completion. '
        'Source: server/graph.py.',
        S['caption']))

    story.append(Paragraph('Component Breakdown', S['subsection']))

    comp_data = [
        ['Component',              'Technology',              'Function'],
        ['Weather Retrieval',      'Open-Meteo REST API',
         'Fetches daily weather code, min/max temperature for a 7-day window at supplied '
         'coordinates. No authentication required. Source: nodes/weather_getter.py.'],
        ['Evidence Collection',    'GPT-4o-mini (tool-use)',
         'Iteratively selects and runs historical sales queries across five dimensions '
         '(month, week, day, weather condition, temperature band) until the agent '
         'produces no further tool calls. Source: nodes/tool_caller.py.'],
        ['Tool Execution',         'LangChain ToolNode + gspread',
         'Executes structured queries against the Google Sheets sales history. '
         'Each of the five tools filters by product_id before returning records. '
         'Source: tools/forecast_tools.py, utils/db_helpers.py.'],
        ['Demand Synthesis',       'GPT-4o-mini (structured output)',
         'Receives the full evidence context plus forecasted weather, returns '
         'a Pydantic model: predicted_quantity (int) and confidence (float 0-1). '
         'Source: nodes/stock_setter.py.'],
        ['Forecast Recorder',      'gspread write API',
         'Appends each completed forecast to a sales_forecast worksheet with '
         'product, period, quantity, confidence, and UTC timestamp. '
         'Source: nodes/forecast_recorder.py.'],
        ['REST API',               'FastAPI 0.136 / Uvicorn',
         'POST /forecast endpoint with Pydantic-validated request body. '
         'Source: main.py.'],
    ]
    compt = Table(_para_rows(comp_data, S['th'], S['tc']), colWidths=[1.3*inch, 1.65*inch, 3.85*inch])
    compt.setStyle(std_ts())
    story.append(compt)
    story.append(Paragraph(
        'Table 2. System components, technologies, and functional roles. '
        'Source file references are to the server/ directory.',
        S['caption']))

    story.append(Paragraph('Data Schema', S['subsection']))
    story.append(Paragraph(
        'The sales_history worksheet contains one row per transaction. All five evidence '
        'dimensions are derivable from the date and weather fields without transformation. '
        'Temperature is stored in Celsius (temperature_c) throughout the codebase; '
        'Figure 3 uses Celsius to match.',
        S['body']))

    schema_data = [
        ['Field',          'Type',                          'Evidence Dimension'],
        ['date',           'YYYY-MM-DD string',             'Month, week, day-of-month, day-of-week'],
        ['product_id',     'String',                        'Primary filter on all five queries'],
        ['quantity',       'Integer',                       'Demand signal (dependent variable)'],
        ['category',       'Controlled vocab (10 values)',  'Category fallback for new products'],
        ['weather',        'Sunny | Cloudy | Rainy | Snowy','Weather-condition dimension'],
        ['temperature_c',  'Float, Celsius',                'Temperature-band dimension'],
    ]
    scht = Table(schema_data, colWidths=[1.2*inch, 1.8*inch, 3.8*inch])
    scht.setStyle(std_ts())
    story.append(scht)
    story.append(Paragraph(
        'Table 3. Sales history schema. A separate sales_forecast worksheet receives '
        'one row per completed forecast output.',
        S['caption']))

    story.append(Paragraph('Technology Stack', S['subsection']))
    tech = [
        ('LangGraph 1.2 / LangChain Core 1.4',
         'StateGraph with TypedDict state schema. Conditional edge implements the '
         'evidence-collection loop. Type annotations enforce data contracts at each '
         'node boundary.'),
        ('OpenAI GPT-4o-mini',
         'Temperature 0.2 in the collection agent (allows adaptive tool selection); '
         'temperature 0 with structured output in the synthesis agent '
         '(deterministic quantity and confidence).'),
        ('Open-Meteo API',
         'Returns WMO weather codes and daily min/max temperatures for any lat/long. '
         'Zero authentication, no rate-limit concerns at this scale.'),
        ('Google Sheets / gspread 6.2',
         'Service account credentials with Sheets and Drive scopes. '
         '_get_records() fetches the full worksheet on each query; '
         'filtering is done in Python rather than via Sheets API.'),
        ('FastAPI 0.136 / Uvicorn',
         'Single POST endpoint, CORS middleware for browser clients, '
         'optional category field in request body for new-product fallback.'),
    ]
    for t, d in tech:
        story.append(Paragraph(f'<b>{t}.</b> {d}', S['body']))

    story.append(PageBreak())

    # =============================================================
    # RESULTS AND DATASET ANALYSIS
    # =============================================================
    story.append(Paragraph('Results and Dataset Analysis', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph('Dataset Overview', S['subsection']))
    story.append(Paragraph(
        'The synthetic dataset (grocery_sales.csv) contains 5,000 transactions across '
        '58 SKUs in 10 categories, covering June 6, 2024 through June 5, 2025. '
        'Weather conditions are distributed as: Cloudy 33.2%, Rainy 32.9%, '
        'Sunny 31.5%, and Snowing 2.4%. Temperatures span -2°C to 28°C. '
        'Drinks (687 rows) and Frozen (444 rows) are the two categories selected '
        'for focused analysis because they have the strongest theoretical weather linkage.',
        S['body']))

    story.append(Paragraph('Backtest Methodology', S['subsection']))
    story.append(Paragraph(
        'A train/test split at April 1, 2025 yields 4,080 training rows and 920 test '
        'rows (the final two months). In a backtest, the evidence collection agent '
        'queries only records predating the forecast date, and the synthesis agent '
        'receives the actual Open-Meteo forecast for the test period. The MAPE figures '
        'in Table 4 and Figure 5 represent <i>illustrative targets</i> derived from '
        'the direction and scale of improvement observed in the dataset analysis, '
        'not a fully automated end-to-end backtest run. The methodology for running '
        'such a backtest is documented in the repository; the figures serve to frame '
        'expected performance, not to report it as measured.',
        S['body']))

    # engineering reflection 2
    refl_box2 = Table([[Paragraph(
        f'Build reflection: I expected temperature to show a clean upward trend for '
        f'beverage demand. The dataset gives R² = {r2_str} with a non-monotonic shape '
        'above 18°C — bins at 24-28°C are lower than at 16-20°C. '
        'A linear coefficient would systematically over-predict on very hot days. '
        'The agent avoids this because get_sales_by_temperature_range queries actual '
        'records in that band rather than extrapolating from a slope.',
        S['reflection'])]], colWidths=[CW])
    refl_box2.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.HexColor('#eef4fb')),
        ('BOX',           (0,0), (-1,-1), 1.0, colors.HexColor('#a0b8d8')),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
        ('RIGHTPADDING',  (0,0), (-1,-1), 12),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(refl_box2)

    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('Illustrative Performance Targets', S['subsection']))

    res_data = [
        ['Metric',                          'Baseline', 'Target\n(illustrative)', 'Basis'],
        ['MAPE - Drinks category',           '31.4%',   '~17%',
         'Direction consistent with weather-signal strength in dataset'],
        ['MAPE - Frozen category',           '28.3%',   '~15%',
         'Direction consistent with weather-signal strength in dataset'],
        ['Time-to-forecast per SKU',         '~4 min\n(manual)',  '~8 sec\n(automated)',
         'Measured: agent API call wall time on local hardware'],
        ['Confidence score range\n(Drinks)', 'n/a',     '0.5 - 0.85',
         'Observed in test runs; not statistically calibrated'],
    ]
    rt = Table(_para_rows(res_data, S['th'], S['tc']), colWidths=[1.9*inch, 1.0*inch, 1.1*inch, 2.8*inch])
    rt.setStyle(std_ts())
    story.append(rt)
    story.append(Paragraph(
        'Table 4. Illustrative performance targets. MAPE targets are directional '
        'estimates; time-to-forecast is the one real measured figure. '
        'Backtest MAPE requires running the full agent pipeline on the held-out period.',
        S['caption']))

    story.append(Paragraph('MAPE by Category', S['subsection']))
    story.append(chart_mape())
    story.append(Paragraph(
        'Figure 5. Forecast MAPE before/after, by category. '
        'Drinks and Frozen (green bars) show illustrative post-implementation targets '
        'derived from the dataset analysis. Bakery, Fruit & Veg, and Snacks show only '
        'the baseline; projected post-implementation MAPE (light green, dashed outline) '
        'is a directional estimate, not derived from tested results in these categories.',
        S['caption']))

    story.append(PageBreak())

    # =============================================================
    # PROJECTED BUSINESS IMPACT
    # =============================================================
    story.append(Paragraph('Projected Business Impact (Illustrative)', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph(
        'The following projections apply the system\'s directional improvements to the '
        'FreshMart illustrative scenario. All figures are derived from explicit '
        'per-store-per-category assumptions, shown below. Cost savings and revenue '
        'impact are reported separately; they are not summed into a single value '
        'because they represent different types of benefit to the business.',
        S['body']))

    story.append(Paragraph('Extrapolation Logic', S['subsection']))

    econ_data = [
        ['Assumption',                                   'Value',       'Basis'],
        ['Company-wide annual overstock waste',           '$31.2M',      'Illustrative (FreshMart scenario)'],
        ['Store count',                                   '187',         'Illustrative'],
        ['Weather-sensitive categories in scope',         '10',          'Illustrative'],
        ['Per-store per-category annual waste baseline',  '$16,700',     '$31.2M ÷ 187 ÷ 10'],
        ['Pilot scope (18 stores × 2 categories)',  '$600K/yr',    '$16,700 × 36 store-cat. units'],
        ['Assumed waste reduction rate',                  '15%',         'Directional, consistent with MAPE improvement'],
        ['Pilot-scale annual savings',                    '~$90K/yr',    '$600K × 15%'],
        ['Full-deployment waste savings (scale: 51.9×)', '$4.7M/yr','$90K × (187/18 × 10/2)'],
    ]
    et = Table(econ_data, colWidths=[3.1*inch, 1.2*inch, 2.5*inch])
    et.setStyle(std_ts())
    story.append(et)
    story.append(Paragraph(
        'Table 5. Per-store-per-category extrapolation showing how pilot-scale and '
        'full-scale figures relate. Scale factor = 187/18 × 10/2 = 51.9×. '
        'The 15% waste reduction assumption drives all downstream dollar figures.',
        S['caption']))

    story.append(KeepTogether([
        Paragraph('Projected Annual Financial Impact', S['subsection']),
        chart_financial(),
        Paragraph(
            'Figure 6. Projected annual value upon full deployment — illustrative. '
            'Cost savings (green, navy): directly comparable to net income. '
            'Revenue recapture (orange): gross revenue impact; apply the 1-3% net '
            'margin to estimate profit equivalent (~$42K-$126K). '
            'Note: these are not summed because revenue and cost savings are different '
            'in kind. Pilot-scale equivalent (18 stores, 2 categories): ~$90K/year '
            'in overstock savings.',
            S['caption']),
    ]))

    story.append(PageBreak())

    # =============================================================
    # KEY BENEFITS
    # =============================================================
    story.append(Paragraph('Key Benefits for the Business', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    benefits = [
        ('Waste reduction at the margin',
         'Grocery net margins of 1-3% mean every dollar of overstock write-off '
         'requires $33-100 in revenue to offset. Reducing overstock by 15% across '
         'weather-sensitive categories has an outsized margin effect relative to its '
         'revenue size.'),

        ('Buyers focus on exceptions, not routine orders',
         'The confidence score routes high-certainty forecasts to automated order '
         'generation and surfaces only low-confidence SKUs for buyer review. '
         'In the FreshMart scenario, this shifts the buyer\'s role from generating '
         '340 forecast adjustments per week to reviewing a targeted exception list.'),

        ('New product continuity',
         'The category-level fallback means a newly launched SKU does not produce '
         'a null forecast on its first week. The synthesis agent receives category '
         'evidence instead and reduces confidence accordingly, which is more useful '
         'than no output.'),

        ('Auditability',
         'Each forecast is traceable to the historical records that informed it. '
         'The Google Sheets output includes product, period, quantity, confidence, '
         'and UTC timestamp. This makes model behavior reviewable without access '
         'to the LLM conversation history.'),
    ]

    for title, desc in benefits:
        story.append(KeepTogether([
            Paragraph(f'<b>{title}.</b> {desc}', S['body']),
            Spacer(1, 4),
        ]))

    story.append(PageBreak())

    # =============================================================
    # LIMITATIONS
    # =============================================================
    story.append(Paragraph('Limitations', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph(
        'The following limitations apply to any interpretation of the results in '
        'this document.',
        S['body']))

    limits = [
        ('Synthetic data only',
         'grocery_sales.csv was generated to have plausible category distributions '
         'and weather correlations; it was not derived from a live POS system. '
         'Performance on real retail data will differ, potentially significantly, '
         'because real consumer behavior is noisier and less cleanly correlated '
         'with weather conditions.'),

        ('LLM confidence is uncalibrated',
         'The 0.0-1.0 confidence score reflects GPT-4o-mini\'s self-assessment of '
         'the evidence quality, not a calibrated probability. A score of 0.8 does '
         'not mean the forecast will be within 20% of actual demand. '
         'Calibration is a Phase 4 item.'),

        ('No live deployment',
         'The system runs correctly against the Google Sheets store and Open-Meteo '
         'API on the synthetic dataset, but has not been operated in a real store\'s '
         'replenishment workflow. Operational edge cases — API latency, data '
         'freshness, SKU churn, concurrent writes — are untested.'),

        ('Weather-demand coefficients are illustrative',
         'The relationships in Figures 2 and 3 reflect patterns in the synthetic '
         'data. They are useful for demonstrating the architecture\'s query logic, '
         f'not for claiming measured consumer behavior. The weak R² ({r2_str}) for '
         'temperature vs Drinks demand in the dataset is itself a reminder that '
         'these signals require validation against real data before deployment.'),
    ]

    for title, desc in limits:
        story.append(Paragraph(f'<b>{title}.</b> {desc}', S['body']))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # =============================================================
    # WHAT'S NEXT
    # =============================================================
    story.append(Paragraph("What's Next", S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph(
        'The current implementation is a working foundation. These are the extensions '
        'I would pursue to move it from a portfolio project toward something a retailer '
        'could run against live data:',
        S['body']))

    road_data = [
        ['Extension',           'What it requires',                      'What it unlocks'],
        ['Live POS integration','Replace gspread with a real-time data feed or warehouse connector',
         'Actual MAPE measurement against live sales; calibration data for the confidence score'],
        ['Confidence calibration','Run agent in backtest mode; compare confidence vs actual error distribution',
         'Statistically meaningful confidence score; triggered escalation thresholds'],
        ['ERP write-back',      'Connect POST /forecast to purchase order generation',
         'Closes the loop from forecast to fulfilment without buyer touchpoint'],
        ['Promotional signals', 'Add promo calendar and event data to the evidence dimensions',
         'Removes the largest residual error source after weather is accounted for'],
    ]
    rdt = Table(_para_rows(road_data, S['th'], S['tc']), colWidths=[1.4*inch, 2.6*inch, 2.8*inch])
    rdt.setStyle(std_ts())
    story.append(rdt)
    story.append(Paragraph(
        'Table 6. Planned extensions ordered by data dependency. '
        'Live POS integration is the enabling step that unlocks calibration and '
        'meaningful A/B measurement.',
        S['caption']))

    # =============================================================
    # ABOUT THE AUTHOR
    # =============================================================
    story.append(Paragraph('About the Author', S['section']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=10))

    story.append(Paragraph(
        'I am Matteo Bertuzzi, an AI engineer working at the intersection of consumer '
        'behavior, applied intelligence, and retail operations. My work focuses on '
        'building agent systems that take a specific operational signal — weather, '
        'location, past behavior — and turn it into a decision a practitioner can '
        'actually act on. This project reflects that: a real implementation built to '
        'answer a question about whether a weather-aware agent can outperform a '
        'rolling average in a domain where the signal is present but routinely ignored.',
        S['body']))

    story.append(Paragraph(
        'The system is fully implemented and available as open-source code. '
        'The business scenario is illustrative; all technical components are real '
        'and functional. The implementation took approximately six weeks: one week '
        'of architecture design, three weeks of system build and iteration, '
        'and two weeks of analysis and documentation.',
        S['body']))

    story.append(Spacer(1, 0.2*inch))

    contact_data = [
        ['Author',   'Matteo Bertuzzi'],
        ['Role',     'AI Engineer  |  Consumer Behavior, Retail Intelligence, Agent Systems'],
        ['GitHub',   'github.com/matteobertuzzi'],
        ['LinkedIn', 'linkedin.com/in/matteo-bertuzzi'],
    ]
    ctab = Table(contact_data, colWidths=[1.2*inch, 5.6*inch])
    ctab.setStyle(TableStyle([
        ('FONT',          (0,0), (0,-1), 'Helvetica-Bold', 9),
        ('FONT',          (1,0), (1,-1), 'Helvetica', 9),
        ('TEXTCOLOR',     (0,0), (-1,-1), DARK),
        ('ROWBACKGROUNDS',(0,0), (-1,-1), [colors.white, LIGHT]),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('LINEABOVE',     (0,0), (-1,0), 0.5, MID_GRAY),
        ('LINEBELOW',     (0,-1),(-1,-1), 0.5, MID_GRAY),
    ]))
    story.append(ctab)

    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width='100%', thickness=0.5, color=MID_GRAY, spaceAfter=10))

    story.append(Paragraph(
        'This document is a personal project and portfolio case study. '
        'FreshMart Inc. is fictitious. All dollar figures and percentage improvements '
        'labeled "illustrative" are projections derived from stated assumptions, '
        'not from measured results in a live deployment. The open-source dataset and '
        'full source code are available in the GitHub repository.',
        S['disclaimer']))

    story.append(Paragraph(
        'Copyright 2026 Matteo Bertuzzi. All rights reserved.',
        ParagraphStyle('copyright', fontName='Helvetica', fontSize=8,
                       textColor=GRAY, leading=12, alignment=TA_LEFT)
    ))

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    print(f'Saved: {OUTPUT}')


if __name__ == '__main__':
    build()
