import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import textwrap
import os


def _truncate_with_ellipsis(text: str, max_chars: int) -> str:
    """Trim long labels so they stay in their column without overlapping values."""
    if not isinstance(text, str):
        text = str(text)
    if max_chars <= 1:
        return text[:max_chars]
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "..."

def create_caption_image(text: str, output_path: str, width=1080, height=1920):
    """Fallback utility generating transparent PNG titles matching the video style natively."""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    raw_text = str(text or "").upper().strip()

    # Wrap captions and shrink font until text fits inside safe lower-third bounds.
    safe_margin_x = int(width * 0.08)
    box_width = width - (2 * safe_margin_x)
    y = int(height * 0.84)
    wrapped_text = textwrap.fill(raw_text, width=28)

    fnt = None
    text_bbox = None
    for font_size in range(60, 31, -2):
        try:
            trial_font = ImageFont.truetype("arialbd.ttf", font_size)
        except Exception:
            trial_font = ImageFont.load_default()

        trial_bbox = d.multiline_textbbox((0, 0), wrapped_text, font=trial_font, spacing=8, align='center')
        tw = trial_bbox[2] - trial_bbox[0]
        if tw <= box_width:
            fnt = trial_font
            text_bbox = trial_bbox
            break

        # Slightly increase wrapping for very long phrases before reducing size further.
        wrapped_text = textwrap.fill(raw_text, width=max(18, 28 - ((60 - font_size) // 3)))

    if fnt is None:
        fnt = ImageFont.load_default()
        text_bbox = d.multiline_textbbox((0, 0), wrapped_text, font=fnt, spacing=8, align='center')

    tw = text_bbox[2] - text_bbox[0]
    th = text_bbox[3] - text_bbox[1]
    x = (width - tw) / 2

    # Clamp y so the full multi-line caption always remains within frame.
    y = max(0, min(y, height - th - 4))

    # 4px outline for aggressive legibility over varied charts.
    for x_off in [-4, -2, 0, 2, 4]:
        for y_off in [-4, -2, 0, 2, 4]:
            d.multiline_text((x + x_off, y + y_off), wrapped_text, font=fnt, fill='black', spacing=8, align='center')

    # Core text fill.
    d.multiline_text((x, y), wrapped_text, font=fnt, fill='white', spacing=8, align='center')
    
    img.save(output_path)

def render_unified_background(ax, image_path, title):
    """Renders the EXACT SAME background image across all scenes for 100% style consistency."""
    try:
        img = Image.open(image_path)
        ax.imshow(img, aspect='auto', extent=[0, 1, 0, 1])
        # Darken the background slightly so text pops perfectly
        ax.fill_between([0, 1], 0, 1, color='black', alpha=0.7)
    except:
        ax.set_facecolor('#0a0e17') # Consistent dark blue/black fallback
        
    safe_title = str(title or "").strip()
    if len(safe_title) > 24:
        safe_title = textwrap.fill(safe_title, width=24)
    title_font = 42 if len(str(title or "")) <= 20 else 36
    ax.text(
        0.5,
        0.90,
        safe_title,
        fontsize=title_font,
        fontweight='bold',
        color='#ffffff',
        ha='center',
        va='center',
        transform=ax.transAxes,
        bbox=dict(facecolor='#111822', alpha=0.9, edgecolor='#30363d', boxstyle='round,pad=0.5')
    )
    ax.axis('off')

def generate_scene_1_intro(scene_data: dict, bg_path: str, output_path: str):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    title = scene_data.get("scene_title", "MARKET BRIEFING").upper()
    render_unified_background(ax, bg_path, title)
    
    ax.text(0.5, 0.5, "DAILY\nMARKET\nUPDATE", fontsize=65, fontweight='black', color='#00ff00', ha='center', va='center', transform=ax.transAxes)
    ax.text(0.5, 0.25, "Top Indices • Sector Flow • Volatility", fontsize=30, color='lightgray', ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path

def generate_scene_2_indices(scene_data: dict, indices_data: list, bg_path: str, output_path: str):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    title = scene_data.get("scene_title", "MAJOR INDICES").upper()
    render_unified_background(ax, bg_path, title)
    
    count = len(indices_data)
    # Dynamically center rows and keep enough spacing for readability.
    row_gap = 0.078 if count <= 7 else 0.068
    if count > 0:
        y_pos = 0.5 + ((count - 1) * row_gap / 2)
    else:
        y_pos = 0.5
        
    for idx in indices_data:
        name = _truncate_with_ellipsis(idx.get('Name', '-'), max_chars=16)
        close = f"{idx['Close']:,.2f}" if isinstance(idx['Close'], float) else str(idx['Close'])
        change = idx['Change']
        
        try:
            val = float(change)
            color = '#00ff00' if val >= 0 else '#ff4444'
            sign = "▲ +" if val > 0 else "▼ "
        except:
            color = 'lightgray'
            sign = ""
            
        # Fixed columns prevent long labels from colliding with numeric values.
        ax.text(0.05, y_pos, name, fontsize=18, fontweight='bold', color='lightgray', ha='left', va='center', transform=ax.transAxes)
        ax.text(0.70, y_pos, close, fontsize=20, color='white', ha='right', va='center', transform=ax.transAxes)
        ax.text(0.95, y_pos, f"{sign}{change}%", fontsize=20, fontweight='bold', color=color, ha='right', va='center', transform=ax.transAxes)
        ax.plot([0.05, 0.95], [y_pos - 0.035, y_pos - 0.035], color='#30363d', lw=2, transform=ax.transAxes)
        y_pos -= row_gap

    plt.tight_layout()
    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path

def generate_scene_3_trend(scene_data: dict, indices_data: list, bg_path: str, output_path: str):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    title = scene_data.get("scene_title", "MARKET TREND").upper()
    render_unified_background(ax, bg_path, title)
    
    vix_data = next((item for item in indices_data if item["Name"] == "India VIX"), {})
    
    try:
        val = float(vix_data.get('Change', 0))
        color = '#ff4444' if val > 0 else '#00ff00'
        state = "HIGH VOLATILITY DETECTED ⚠️" if val > 0 else "CALM MARKET CONDITIONS 📉"
    except:
        val = 0
        color = 'white'
        state = "NEUTRAL"
    
    ax.text(0.5, 0.6, "INDIA VIX", fontsize=45, color='lightgray', ha='center', va='center', transform=ax.transAxes)
    ax.text(0.5, 0.5, f"{vix_data.get('Close', 'N/A')}  ({vix_data.get('Change', 'N/A')}%)", fontsize=65, fontweight='bold', color=color, ha='center', va='center', transform=ax.transAxes)
    ax.text(0.5, 0.4, state, fontsize=35, color=color, ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path

def _render_sector_list(sectors, title, main_color, empty_msg, bg_path, output_path):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    render_unified_background(ax, bg_path, title)
    
    if not sectors:
        ax.text(0.5, 0.5, textwrap.fill(empty_msg, width=25), fontsize=40, color='lightgray', ha='center', va='center', transform=ax.transAxes)
    else:
        y_pos = 0.7
        for s in sectors:
            ax.text(0.5, y_pos, s['Name'], fontsize=42, color='white', ha='center', va='center', transform=ax.transAxes)
            sign = "+" if float(s['Change']) > 0 else ""
            ax.text(0.5, y_pos - 0.06, f"{sign}{s['Change']}%", fontsize=48, fontweight='bold', color=main_color, ha='center', va='center', transform=ax.transAxes)
            y_pos -= 0.18
        
    plt.tight_layout()
    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path

def generate_scene_4_winners(scene_data: dict, sectors_data: dict, bg_path: str, output_path: str):
    gainers = [s for s in sectors_data.get("Top_Gainers", []) if float(s['Change']) > 0]
    title = scene_data.get("scene_title", "SECTOR WINNERS").upper()
    return _render_sector_list(gainers, "🔥 " + title, '#00ff00', "No major sectoral gainers were observed today.", bg_path, output_path)

def generate_scene_5_losers(scene_data: dict, sectors_data: dict, bg_path: str, output_path: str):
    losers = [s for s in sectors_data.get("Top_Losers", []) if float(s['Change']) < 0]
    title = scene_data.get("scene_title", "SECTOR LOSERS").upper()
    return _render_sector_list(losers, "🔻 " + title, '#ff4444', "Sector performance remained broadly balanced today.", bg_path, output_path)

def generate_scene_6_insight(scene_data: dict, bg_path: str, output_path: str):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    title = scene_data.get("scene_title", "KEY INSIGHT").upper()
    render_unified_background(ax, bg_path, title)
    
    ax.text(0.5, 0.5, "Stay tuned as we track\nthe exact sectors driving\ntomorrow's momentum.", fontsize=40, color='white', ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path

def generate_scene_7_outro(scene_data: dict, bg_path: str, output_path: str):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    title = scene_data.get("scene_title", "WRAP UP").upper()
    render_unified_background(ax, bg_path, title)
    
    ax.text(0.5, 0.5, "Markets are dynamic.\n\nSubscribe for your concise\nDaily Financial News!", fontsize=42, fontweight='bold', color='#00ff00', ha='center', va='center', transform=ax.transAxes)
    
    plt.tight_layout()
    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path


def generate_scene_market_summary(scene_data: dict, insights: dict, bg_path: str, output_path: str):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    title = scene_data.get("scene_title") or scene_data.get("title", "MARKET SUMMARY")
    render_unified_background(ax, bg_path, title.upper())

    trend = insights.get("market_trend", "Mixed")
    breadth = insights.get("breadth", {})
    up = breadth.get("up", 0)
    down = breadth.get("down", 0)
    vol = insights.get("volatility", "Unknown")

    color = '#00ff00' if trend == "Bullish" else '#ff4444' if trend == "Bearish" else 'lightgray'
    ax.text(0.5, 0.62, trend.upper(), fontsize=58, fontweight='bold', color=color, ha='center', va='center', transform=ax.transAxes)
    ax.text(0.5, 0.50, f"Advancers: {up}   Decliners: {down}", fontsize=32, color='white', ha='center', va='center', transform=ax.transAxes)
    ax.text(0.5, 0.40, f"Volatility: {vol}", fontsize=30, color='lightgray', ha='center', va='center', transform=ax.transAxes)

    plt.tight_layout()
    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path


def generate_scene_institutional_flows(scene_data: dict, flows: dict, bg_path: str, output_path: str):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    title = scene_data.get("scene_title") or scene_data.get("title", "INSTITUTIONAL FLOWS")
    render_unified_background(ax, bg_path, title.upper())

    fii = flows.get("FII_Net")
    dii = flows.get("DII_Net")
    labels = ["FII", "DII"]
    values = [float(fii) if isinstance(fii, (int, float)) else 0.0, float(dii) if isinstance(dii, (int, float)) else 0.0]
    colors = ['#00ff00' if v >= 0 else '#ff4444' for v in values]

    y_min = min(values + [-1.0])
    y_max = max(values + [1.0])
    pad = max(1.0, (y_max - y_min) * 0.35)

    chart_ax = fig.add_axes([0.14, 0.30, 0.72, 0.36])
    chart_ax.bar(labels, values, color=colors, alpha=0.9)
    chart_ax.axhline(0, color='white', linewidth=1.5, alpha=0.6)
    chart_ax.set_ylim(y_min - pad, y_max + pad)
    chart_ax.set_facecolor((0, 0, 0, 0))
    chart_ax.tick_params(colors='white', labelsize=16)
    for spine in chart_ax.spines.values():
        spine.set_color('#8b949e')

    ax.text(0.5, 0.2, "Net Institutional Position", fontsize=28, color='lightgray', ha='center', va='center', transform=ax.transAxes)

    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path


def generate_scene_race_chart(scene_data: dict, sectors_data: dict, bg_path: str, output_path: str):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    title = scene_data.get("scene_title") or scene_data.get("title", "RACE CHART")
    render_unified_background(ax, bg_path, title.upper())

    all_sectors = sectors_data.get("All", [])[:5]
    if not all_sectors:
        ax.text(0.5, 0.5, "No sector race data available", fontsize=36, color='lightgray', ha='center', va='center', transform=ax.transAxes)
    else:
        labels = [x.get("Name", "-") for x in all_sectors]
        values = [float(x.get("Change", 0)) for x in all_sectors]
        colors = ['#00ff00' if v >= 0 else '#ff4444' for v in values]

        chart_ax = fig.add_axes([0.12, 0.24, 0.76, 0.48])
        ypos = list(range(len(labels)))
        chart_ax.barh(ypos, values, color=colors, alpha=0.9)
        chart_ax.set_yticks(ypos)
        chart_ax.set_yticklabels(labels, color='white', fontsize=14)
        chart_ax.tick_params(axis='x', colors='white')
        chart_ax.axvline(0, color='white', linewidth=1.2, alpha=0.5)
        chart_ax.set_facecolor((0, 0, 0, 0))
        for spine in chart_ax.spines.values():
            spine.set_color('#8b949e')

    ax.text(0.5, 0.16, "Leaders vs laggards snapshot", fontsize=26, color='lightgray', ha='center', va='center', transform=ax.transAxes)

    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path


def generate_scene_ipo_tracker(scene_data: dict, ipo_data: list, bg_path: str, output_path: str):
    import matplotlib
    matplotlib.use('Agg')
    fig, ax = plt.subplots(figsize=(9, 16), dpi=120)
    title = scene_data.get("scene_title") or scene_data.get("title", "IPO TRACKER")
    render_unified_background(ax, bg_path, title.upper())

    if not ipo_data:
        ax.text(0.5, 0.5, "No active IPO updates today", fontsize=36, color='lightgray', ha='center', va='center', transform=ax.transAxes)
    else:
        y = 0.68
        for row in ipo_data[:3]:
            name = str(row.get("name", "IPO")).upper()
            sub = str(row.get("subscription", "N/A"))
            perf = str(row.get("listing_perf", "N/A"))
            ax.text(0.5, y, name, fontsize=30, color='white', fontweight='bold', ha='center', va='center', transform=ax.transAxes)
            ax.text(0.5, y - 0.06, f"Sub: {sub} | Listing: {perf}", fontsize=22, color='lightgray', ha='center', va='center', transform=ax.transAxes)
            y -= 0.2

    plt.savefig(output_path, facecolor='black', edgecolor='none')
    plt.close()
    return output_path
