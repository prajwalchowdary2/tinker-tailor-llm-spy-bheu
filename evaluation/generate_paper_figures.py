"""
Generate all publication-quality figures for the USENIX paper.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import numpy as np
import os

FIGURE_DIR = "paper/figures"
os.makedirs(FIGURE_DIR, exist_ok=True)

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 8,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'pdf.fonttype': 42,   # TrueType — prevents Type 3 bitmap fonts
    'ps.fonttype': 42,    # TrueType — prevents Type 3 bitmap fonts
})

COLORS = {
    'primary': '#1565C0',
    'secondary': '#2E7D32',
    'accent': '#E65100',
    'danger': '#C62828',
    'purple': '#6A1B9A',
    'teal': '#00838F',
    'gray': '#546E7A',
    'light_blue': '#42A5F5',
    'light_green': '#66BB6A',
    'light_orange': '#FFA726',
}


def fig1_architecture():
    """Pipeline architecture diagram."""
    fig, ax = plt.subplots(figsize=(7, 5.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8.2)
    ax.axis('off')

    boxes = [
        (5, 7.4, 'Profile Discovery', '23 Chrome profiles + Desktop apps', '#E3F2FD', COLORS['primary']),
        (5, 6.1, 'LevelDB Parser', 'SSTable footer → index → data blocks\nWAL logs → raw byte blobs', '#E8F5E9', COLORS['secondary']),
        (5, 4.8, 'Snappy Decompressor', 'Pure-Python, 97 lines\n4 element types (literal + 3 copy)', '#FFF3E0', COLORS['accent']),
        (5, 3.5, 'V8 Deserializer', 'Tags · Varints · Smi-shift · Depth tracking', '#F3E5F5', COLORS['purple']),
        (5, 0.5, 'Evidence Envelope', 'HMAC-SHA256 chain of custody', '#ECEFF1', COLORS['gray']),
    ]

    for x, y, title, subtitle, facecolor, edgecolor in boxes:
        width = 7.5
        height = 0.8
        rect = mpatches.FancyBboxPatch(
            (x - width/2, y - height/2), width, height,
            boxstyle="round,pad=0.12",
            facecolor=facecolor, edgecolor=edgecolor, linewidth=1.8
        )
        ax.add_patch(rect)
        ax.text(x, y + 0.12, title,
                ha='center', va='center', fontsize=10, fontweight='bold',
                color=edgecolor)
        ax.text(x, y - 0.18, subtitle,
                ha='center', va='center', fontsize=7.5, color='#333333')

    # Platform Carvers container: title on top, sub-boxes nested below
    container = mpatches.FancyBboxPatch(
        (1.25, 1.35), 7.5, 1.5,
        boxstyle="round,pad=0.12",
        facecolor='#E0F7FA', edgecolor=COLORS['teal'], linewidth=1.8
    )
    ax.add_patch(container)
    ax.text(5, 2.6, 'Platform Carvers', ha='center', va='center',
            fontsize=10, fontweight='bold', color=COLORS['teal'])

    carver_labels = ['ChatGPT\nV8 Structured', 'Claude\nTipTap', 'Generic\nRegex']
    carver_colors = [COLORS['primary'], COLORS['danger'], COLORS['accent']]
    for i, (label, color) in enumerate(zip(carver_labels, carver_colors)):
        cx = 2.5 + i * 2.5
        rect = mpatches.FancyBboxPatch(
            (cx - 1.05, 1.55), 2.1, 0.75,
            boxstyle="round,pad=0.06",
            facecolor='white', edgecolor=color, linewidth=1.2, linestyle='--'
        )
        ax.add_patch(rect)
        ax.text(cx, 1.93, label, ha='center', va='center', fontsize=7.5,
                color=color, fontweight='bold', linespacing=1.3)

    # Arrows
    arrow_ys = [(7.0, 6.5), (5.7, 5.2), (4.4, 3.9), (3.1, 2.95), (1.3, 0.9)]
    for y_start, y_end in arrow_ys:
        ax.annotate('', xy=(5, y_end), xytext=(5, y_start),
                    arrowprops=dict(arrowstyle='->', color='#666666', lw=1.5))

    plt.savefig(os.path.join(FIGURE_DIR, 'fig_architecture.pdf'))
    plt.close()
    print('[OK] fig_architecture.pdf')


def fig2_tool_comparison():
    """Tool comparison bar chart — the killer figure."""
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.2))

    # ChatGPT comparison
    ax = axes[0]
    tools = ['Tinker Tailor', 'Grep', 'JSON Scan']
    values = [328, 0, 0]
    colors = [COLORS['primary'], COLORS['accent'], COLORS['gray']]
    bars = ax.bar(tools, values, color=colors, edgecolor='white', linewidth=0.5, width=0.6)
    ax.set_ylabel('Text Artifacts Recovered')
    ax.set_title('ChatGPT (Profile 5)', fontweight='bold')
    ax.set_ylim(0, 380)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
                str(val), ha='center', va='bottom', fontweight='bold', fontsize=10)
    # Add "0%" labels
    ax.text(1, 8, '0%', ha='center', va='bottom', fontsize=12, color=COLORS['danger'], fontweight='bold')
    ax.text(2, 8, '0%', ha='center', va='bottom', fontsize=12, color=COLORS['danger'], fontweight='bold')

    # Claude comparison
    ax = axes[1]
    values = [102, 21, 0]
    bars = ax.bar(tools, values, color=colors, edgecolor='white', linewidth=0.5, width=0.6)
    ax.set_ylabel('Drafts Recovered')
    ax.set_title('Claude (Profile 29)', fontweight='bold')
    ax.set_ylim(0, 125)
    for bar, val in zip(bars, values):
        label = f'{val} ({val*100//102}%)' if val > 0 else '0'
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                str(val), ha='center', va='bottom', fontweight='bold', fontsize=10)
    ax.text(1, 23, '21%', ha='center', va='bottom', fontsize=9, color=COLORS['accent'], fontweight='bold')
    ax.text(2, 3, '0%', ha='center', va='bottom', fontsize=12, color=COLORS['danger'], fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_tool_comparison.pdf'))
    plt.close()
    print('[OK] fig_tool_comparison.pdf')


def fig3_speed_benchmark():
    """Speed vs EDR detection windows — log scale."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    # Carver speeds (p99)
    platforms = ['ChatGPT', 'Claude', 'Generic']
    p99_times = [0.03, 0.03, 0.03]

    bars = ax.barh(platforms, p99_times, color=COLORS['primary'], height=0.5,
                   label='Tinker Tailor p99', edgecolor='white')

    # EDR detection windows
    edr_systems = [
        ('CrowdStrike Falcon', 250, COLORS['danger']),
        ('SentinelOne', 300, COLORS['accent']),
        ('Microsoft Defender', 500, COLORS['purple']),
        ('Elastic Security', 750, COLORS['teal']),
        ('Carbon Black', 1000, COLORS['gray']),
    ]

    edr_handles = []
    for name, window, color in edr_systems:
        line = ax.axvline(x=window, color=color, linestyle='--',
                          linewidth=1.2, alpha=0.8,
                          label=f'{name} ({window}ms)')
        edr_handles.append(line)

    ax.set_xscale('log')
    ax.set_xlabel('Time (ms) — log scale')
    ax.set_xlim(0.005, 30000)
    ax.set_ylim(-0.6, 2.6)
    ax.set_title('Extraction Speed vs Estimated EDR Event-Processing Latency',
                 fontweight='bold', pad=10)

    # Add multiplier annotations
    for i, (platform, time) in enumerate(zip(platforms, p99_times)):
        mult = int(250 / time)
        ax.text(time * 3, i, f'{mult:,}× below est.\nCrowdStrike latency',
                va='center', fontsize=7, color=COLORS['danger'], fontweight='bold')

    ax.legend(handles=[bars] + edr_handles, loc='center right',
              fontsize=6.5, framealpha=0.95, borderpad=0.6,
              handlelength=1.8, labelspacing=0.5)

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_speed_edr.pdf'))
    plt.close()
    print('[OK] fig_speed_edr.pdf')


def fig4_recovery_rates():
    """Recovery rate bar chart — precision/recall/F1 per platform."""
    fig, ax = plt.subplots(figsize=(6, 3))

    platforms = ['ChatGPT', 'Claude', 'DeepSeek', 'Perplexity']
    precision = [1.0, 1.0, 1.0, 1.0]
    recall = [1.0, 1.0, 1.0, 1.0]
    f1 = [1.0, 1.0, 1.0, 1.0]

    x = np.arange(len(platforms))
    width = 0.22

    b1 = ax.bar(x - width, precision, width, label='Precision',
                color=COLORS['primary'], edgecolor='white')
    b2 = ax.bar(x, recall, width, label='Recall',
                color=COLORS['secondary'], edgecolor='white')
    b3 = ax.bar(x + width, f1, width, label='F1 Score',
                color=COLORS['accent'], edgecolor='white')

    ax.set_ylabel('Score')
    ax.set_xticks(x)
    ax.set_xticklabels(platforms)
    ax.set_ylim(0, 1.15)
    ax.set_title('Recovery Rates on Synthetic Ground Truth', fontweight='bold')
    ax.legend(loc='upper right')

    # Add value labels
    for bars in [b1, b2, b3]:
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    '1.0', ha='center', va='bottom', fontsize=7, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_recovery_rates.pdf'))
    plt.close()
    print('[OK] fig_recovery_rates.pdf')


def fig5_profile_breakdown():
    """Per-profile prompt recovery breakdown."""
    fig, ax = plt.subplots(figsize=(7, 3.5))

    # Real data from the scan
    profiles = [
        ('ChatGPT User Prompts', 174, 'chatgpt'),
        ('ChatGPT Assistant Replies', 154, 'chatgpt'),
        ('Claude Keystroke Fragments', 148, 'claude'),
        ('Claude Submitted Prompts', 30, 'claude'),
    ]

    labels = [p[0] for p in profiles]
    values = [p[1] for p in profiles]
    colors = [COLORS['primary'] if p[2] == 'chatgpt' else COLORS['danger'] for p in profiles]

    bars = ax.barh(range(len(labels)), values, color=colors, edgecolor='white', height=0.7)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('Artifacts Recovered')
    ax.set_title('Artifact Characterization (Total: 506)', fontweight='bold')
    ax.invert_yaxis()

    # Value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height()/2,
                str(val), va='center', fontsize=8, fontweight='bold')

    # Legend
    chatgpt_patch = mpatches.Patch(color=COLORS['primary'], label='ChatGPT')
    claude_patch = mpatches.Patch(color=COLORS['danger'], label='Claude TipTap')
    ax.legend(handles=[chatgpt_patch, claude_patch], loc='lower right')

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_profile_breakdown.pdf'))
    plt.close()
    print('[OK] fig_profile_breakdown.pdf')


def fig6_data_flow():
    """Data flow diagram showing the deletion persistence problem."""
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.2, 4.2)
    ax.axis('off')

    # Timeline
    ax.annotate('', xy=(9.5, 2), xytext=(0.5, 2),
                arrowprops=dict(arrowstyle='->', color='#999', lw=2))
    ax.text(5, 1.5, 'Time →', ha='center', fontsize=9, color='#999')

    # Events
    events = [
        (1.5, 'User sends\nmessage', COLORS['secondary'], '●'),
        (3.5, 'Data written\nto IndexedDB', COLORS['primary'], '●'),
        (5.5, 'User clicks\n"Delete"', COLORS['danger'], '✕'),
        (7.5, 'Compaction\n(days later)', COLORS['gray'], '●'),
    ]

    for x, label, color, marker in events:
        ax.plot(x, 2, marker='o' if marker == '●' else 'x',
                markersize=16, color=color, markeredgewidth=3, zorder=5)
        ax.text(x, 2.7, label, ha='center', va='bottom', fontsize=9.5,
                color=color, fontweight='bold', linespacing=1.2)

    # Persistence bar
    rect = mpatches.FancyBboxPatch(
        (3.3, 0.15), 4.4, 0.75,
        boxstyle="round,pad=0.1",
        facecolor='#FFCDD2', edgecolor=COLORS['danger'], linewidth=1.5
    )
    ax.add_patch(rect)
    ax.text(5.5, 0.7, 'DATA PERSISTS UNTIL COMPACTION',
            ha='center', va='center', fontsize=9, fontweight='bold',
            color=COLORS['danger'])
    ax.text(5.5, 0.3, 'Observed: days (active) to ≥83 days (low-activity)',
            ha='center', va='center', fontsize=7.5, fontstyle='italic',
            color=COLORS['danger'])

    # Labels
    ax.text(5.5, 3.8, 'The Deletion Persistence Gap',
            ha='center', va='center', fontsize=13, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_data_flow.pdf'))
    plt.close()
    print('[OK] fig_data_flow.pdf')


def fig7_v8_format():
    """V8 serialization format visual breakdown."""
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.2, 4.8)
    ax.axis('off')

    ax.text(5, 4.4, 'V8 Structured Clone Binary Layout', ha='center',
            fontsize=12, fontweight='bold')

    segments = [
        (0.3, 1.2, '0x22', 'Tag\nOneByteString', COLORS['primary']),
        (1.5, 0.7, '0x08', 'Length\n(varint)', COLORS['secondary']),
        (2.2, 2.2, 'messages', 'Key bytes\n(UTF-8)', COLORS['purple']),
        (4.4, 0.7, '0x61', 'Tag\nBeginArray', COLORS['accent']),
        (5.1, 0.7, '0x03', 'Array\nlength', COLORS['secondary']),
        (5.8, 0.5, '0x49', 'Smi\ntag', COLORS['teal']),
        (6.3, 0.5, '0x02', 'idx\n×2', COLORS['teal']),
        (6.8, 0.5, '0x6f', 'Begin\nObj', COLORS['danger']),
        (7.3, 1.5, '...fields...', 'Key-value\npairs', COLORS['gray']),
        (8.8, 0.5, '0x7b', 'End\nObj', COLORS['danger']),
    ]

    y_top = 3.4
    box_h = 0.85

    for x, w, label, desc, color in segments:
        rect = mpatches.FancyBboxPatch(
            (x, y_top - box_h), w, box_h,
            boxstyle="square,pad=0",
            facecolor=color + '22', edgecolor=color, linewidth=1.5
        )
        ax.add_patch(rect)
        ax.text(x + w/2, y_top - box_h/2, label,
                ha='center', va='center', fontsize=8, fontweight='bold',
                fontfamily='monospace', color=color)
        ax.text(x + w/2, y_top - box_h - 0.15, desc,
                ha='center', va='top', fontsize=7, color='#444',
                linespacing=1.3)

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_v8_format.pdf'))
    plt.close()
    print('[OK] fig_v8_format.pdf')


if __name__ == '__main__':
    print('[*] Generating paper figures\n')
    fig1_architecture()
    fig2_tool_comparison()
    fig3_speed_benchmark()
    fig4_recovery_rates()
    fig5_profile_breakdown()
    fig6_data_flow()
    fig7_v8_format()
    print(f'\n[+] All figures saved to {FIGURE_DIR}/')
