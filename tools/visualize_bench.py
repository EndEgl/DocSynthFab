import json
import sys
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def visualize(json_path):
    with open(json_path) as f:
        data = json.load(f)

    results = []
    for b in data['benchmarks']:
        name = b['name'].replace("test_", "")
        mean_ms = b['stats']['mean'] * 1000  # Saniyeyi ms'ye çevir
        
        # Kategorize et
        category = "Other"
        if "e2e" in name: category = "Pipeline (E2E)"
        elif "render" in name: category = "Rendering"
        elif "augment" in name: category = "Augmentation"
        elif "validate" in name or "density" in name or "binary" in name: category = "QC / Validation"
        elif "sample" in name or "layout" in name: category = "Synthesis / Layout"

        results.append({"Task": name, "Mean_ms": mean_ms, "Category": category})

    df = pd.DataFrame(results).sort_values("Mean_ms")

    # Çizim Ayarları
    plt.style.use('dark_background') # GitHub Dark mode uyumlu
    fig, ax = plt.subplots(figsize=(12, 10))
    
    colors = plt.cm.Paired(np.linspace(0, 1, len(df['Category'].unique())))
    cat_map = {cat: colors[i] for i, cat in enumerate(df['Category'].unique())}

    bars = ax.barh(df['Task'], df['Mean_ms'], color=[cat_map[c] for c in df['Category']])
    
    # Logaritmik ölçek (Mikrosaniye ve Saniyeyi aynı grafikte görmek için şart)
    ax.set_xscale('log')
    ax.set_xlabel('Mean Latency (ms) - Log Scale')
    ax.set_title('AI-1 Gen Performance Analytics', fontsize=16, pad=20)
    
    # Değer etiketlerini ekle
    for bar in bars:
        width = bar.get_width()
        ax.text(width * 1.1, bar.get_y() + bar.get_height()/2, 
                f'{width:.2f} ms', va='center', fontsize=9, color='white')

    plt.tight_layout()
    output_name = "performance_report.png"
    plt.savefig(output_name, dpi=150)
    print(f"✅ Rapor başarıyla oluşturuldu: {output_name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python tools/visualize_bench.py bench.json")
    else:
        visualize(sys.argv[1])