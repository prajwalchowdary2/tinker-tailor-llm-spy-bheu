"""Generate additional figures for the expanded paper."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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
}


def fig_prompt_length_distribution():
    """Prompt length distribution histogram."""
    fig, ax = plt.subplots(figsize=(7, 3))

    labels = ['<50', '50-200', '200-500', '500-1K', '1K-2K', '>2K']
    counts = [205, 145, 10, 2, 30, 114]
    colors = [COLORS['primary'], COLORS['secondary'], COLORS['teal'],
              COLORS['purple'], COLORS['accent'], COLORS['danger']]

    bars = ax.bar(labels, counts, color=colors, edgecolor='white', width=0.65)

    for bar, val in zip(bars, counts):
        pct = val / 506 * 100
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
                f'{val}\n({pct:.0f}%)', ha='center', va='bottom',
                fontsize=8, fontweight='bold')

    ax.set_xlabel('Prompt Length (characters)')
    ax.set_ylabel('Count')
    ax.set_title('Distribution of Recovered Text Artifact Lengths (n=506)', fontweight='bold')
    ax.set_ylim(0, 250)

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_prompt_lengths.pdf'))
    plt.close()
    print('[OK] fig_prompt_lengths.pdf')


def fig_data_source():
    """WAL vs SSTable data source breakdown."""
    fig, axes = plt.subplots(1, 2, figsize=(7, 3))

    # ChatGPT
    ax = axes[0]
    sizes = [138, 0]
    labels_legend = ['WAL Logs', 'SSTables']
    colors = [COLORS['primary'], COLORS['gray']]
    wedges, texts, autotexts = ax.pie(
        [138, 0.1], labels=None, colors=colors,
        autopct=lambda p: f'{p:.0f}%' if p > 1 else '',
        startangle=90, pctdistance=0.5
    )
    ax.set_title('ChatGPT\n(138 artifacts)', fontweight='bold', fontsize=10)
    ax.text(0, -1.3, 'WAL: 430KB\nSST: 2KB', ha='center', fontsize=8, color=COLORS['gray'])

    # Claude
    ax = axes[1]
    wedges, texts, autotexts = ax.pie(
        [8, 94], labels=None, colors=colors,
        autopct=lambda p: f'{p:.0f}%',
        startangle=90, pctdistance=0.6
    )
    for autotext in autotexts:
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)
    ax.set_title('Claude\n(102 drafts)', fontweight='bold', fontsize=10)
    ax.text(0, -1.3, 'WAL: 148KB\nSST: 149KB', ha='center', fontsize=8, color=COLORS['gray'])

    fig.legend(labels_legend, loc='lower center', ncol=2, fontsize=9,
               bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_data_source.pdf'))
    plt.close()
    print('[OK] fig_data_source.pdf')


def fig_leveldb_storage():
    """LevelDB storage analysis across profiles."""
    fig, ax = plt.subplots(figsize=(7, 3.2))

    profiles = ['P2 GPT', 'P3 Claude', 'P37 Claude', 'P2 Claude',
                'P5 GPT', 'P20 Claude', 'P29 Claude', 'P31 Claude',
                'P21 Claude', 'P3 GPT', 'P1 Claude', 'P24 Claude']
    log_kb = [2473, 505, 576, 447, 430, 326, 148, 257, 248, 0, 127, 3]
    ldb_kb = [0, 141, 0, 1, 2, 13, 149, 0, 0, 143, 10, 109]

    x = np.arange(len(profiles))
    width = 0.35

    b1 = ax.bar(x - width/2, log_kb, width, label='WAL Logs (.log)',
                color=COLORS['primary'], edgecolor='white')
    b2 = ax.bar(x + width/2, ldb_kb, width, label='SSTables (.ldb)',
                color=COLORS['accent'], edgecolor='white')

    ax.set_ylabel('Size (KB)')
    ax.set_xticks(x)
    ax.set_xticklabels(profiles, rotation=45, ha='right', fontsize=7)
    ax.set_title('LevelDB Storage by Profile (Top 12)', fontweight='bold')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_leveldb_storage.pdf'))
    plt.close()
    print('[OK] fig_leveldb_storage.pdf')


def fig_realworld_speed():
    """Real-world end-to-end speed benchmark."""
    fig, ax = plt.subplots(figsize=(6, 3))

    trials = [1, 2, 3, 4, 5]
    times = [163.0, 151.1, 147.4, 147.2, 146.7]

    ax.bar(trials, times, color=COLORS['primary'], edgecolor='white', width=0.5)

    for i, t in enumerate(times):
        ax.text(i + 1, t + 2, f'{t:.0f}ms', ha='center', va='bottom',
                fontsize=9, fontweight='bold')

    ax.axhline(y=250, color=COLORS['danger'], linestyle='--', linewidth=1.5,
               label='CrowdStrike Falcon (250ms)')
    ax.axhline(y=500, color=COLORS['purple'], linestyle='--', linewidth=1.5,
               label='Microsoft Defender (500ms)')

    ax.set_xlabel('Trial')
    ax.set_ylabel('Time (ms)')
    ax.set_title('End-to-End Scan: 23 Profiles, 506 Text Artifacts', fontweight='bold')
    ax.set_ylim(0, 550)
    ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, 'fig_realworld_speed.pdf'))
    plt.close()
    print('[OK] fig_realworld_speed.pdf')


if __name__ == '__main__':
    print('[*] Generating extra figures\n')
    fig_prompt_length_distribution()
    fig_data_source()
    fig_leveldb_storage()
    fig_realworld_speed()
    print(f'\n[+] Done. Extra figures in {FIGURE_DIR}/')
