import datetime
import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.feature import NaturalEarthFeature
import numpy as np
from herbie import Herbie
from matplotlib.colors import ListedColormap, BoundaryNorm

plt.switch_backend('Agg')  # headless

def get_refl_cmap():
    # Professional reflectivity colors (very close to Pivotal Weather style)
    colors = [
        '#73c0ff', '#4da6ff', '#0080ff', '#00b300', '#00e600', '#00ff00',
        '#b3ff00', '#ffff00', '#ffcc00', '#ff9900', '#ff6600', '#ff3300',
        '#ff0000', '#cc0000', '#990000', '#660000', '#cc00cc', '#9900cc'
    ]
    levels = np.arange(-10, 76, 5)
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(levels, cmap.N)
    return cmap, norm

def main():
    # Use latest HRRR run (data is usually available ~1-2h after init)
    now = datetime.datetime.now(datetime.timezone.utc)
    run_time = (now - datetime.timedelta(hours=3)).replace(minute=0, second=0, microsecond=0)
    print(f"🔄 Using HRRR run: {run_time.strftime('%Y-%m-%d %H:%M UTC')}")

    os.makedirs("images", exist_ok=True)

    cmap, norm = get_refl_cmap()
    extent = [-82.0, -65.0, 38.0, 48.0]  # Northeast US sector (customizable)

    max_fxx = 23
    generated = 0

    for fxx in range(max_fxx + 1):
        try:
            H = Herbie(
                run_time,
                model="hrrr",
                product="sfc",
                fxx=fxx,
                search=":REFC:",          # Composite Reflectivity
            )
            ds = H.xarray()
            
            # Single variable downloaded
            var_name = list(ds.data_vars.keys())[0]
            data = ds[var_name]

            fig = plt.figure(figsize=(12, 8), dpi=150)
            ax = plt.subplot(projection=ccrs.PlateCarree())
            ax.set_extent(extent, crs=ccrs.PlateCarree())

            # Plot reflectivity
            im = ax.pcolormesh(
                ds.longitude, ds.latitude, data,
                cmap=cmap, norm=norm,
                transform=ccrs.PlateCarree()
            )

            # Map features
            states = NaturalEarthFeature(category='cultural', scale='50m',
                                         facecolor='none', name='admin_1_states_provinces')
            ax.add_feature(states, linewidth=0.8, edgecolor='black')
            ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=1.2)
            ax.add_feature(cfeature.BORDERS.with_scale('50m'), linewidth=0.6)

            # Titles
            init_str = ds.time.dt.strftime('%Y-%m-%d %H:%M UTC').item()
            valid_str = ds.valid_time.dt.strftime('%Y-%m-%d %H:%M UTC').item()
            ax.set_title(f"HRRR Composite Reflectivity (WRF-ARW)\n"
                         f"Init: {init_str}   |   Valid: {valid_str}  (F{fxx:02d})",
                         fontsize=14, pad=20)

            cbar = fig.colorbar(im, ax=ax, orientation='horizontal', pad=0.08, shrink=0.7)
            cbar.set_label('Composite Reflectivity (dBZ)', fontsize=12)

            fname = f"images/hrrr_ne_refc_f{fxx:02d}.png"
            plt.savefig(fname, bbox_inches='tight', dpi=150)
            plt.close(fig)
            
            print(f"✅ Saved {fname}")
            generated += 1

        except Exception as e:
            print(f"⏹️  Hour {fxx} not yet available: {e}")
            break

    # Generate viewer HTML
    generate_html(run_time, generated - 1)

def generate_html(init_time, max_fxx):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Northeast HRRR Composite Reflectivity</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; }}
        .map-img {{ max-width: 100%; height: auto; box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.2); }}
    </style>
</head>
<body class="bg-zinc-950 text-white">
    <div class="max-w-6xl mx-auto p-6">
        <div class="flex justify-between items-center mb-8">
            <div>
                <h1 class="text-4xl font-bold tracking-tight">Northeast US</h1>
                <p class="text-2xl text-emerald-400">HRRR Composite Reflectivity (WRF-ARW)</p>
            </div>
            <div class="text-right">
                <p class="text-zinc-400">Latest model run</p>
                <p class="font-mono text-lg">{init_time.strftime('%Y-%m-%d %H:%M UTC')}</p>
            </div>
        </div>

        <div class="bg-zinc-900 rounded-2xl p-4 mb-8">
            <img id="main-image" class="map-img rounded-xl" src="images/hrrr_ne_refc_f00.png" alt="HRRR Reflectivity">
            <div class="flex items-center gap-4 mt-6">
                <button onclick="prevHour()" class="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-xl font-medium">← Previous</button>
                <div class="flex-1">
                    <input type="range" id="hour-slider" min="0" max="{max_fxx}" value="0" 
                           oninput="updateHour(this.value)" class="w-full accent-emerald-500">
                </div>
                <button onclick="nextHour()" class="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 rounded-xl font-medium">Next →</button>
                <span id="hour-label" class="font-mono w-20 text-center">F00</span>
            </div>
        </div>

        <p class="text-center text-zinc-500 text-sm">
            One frame per hour • Updated every 6 hours automatically via GitHub Actions • 
            Data from NOAA HRRR (WRF-based)
        </p>
    </div>

    <script>
        let currentHour = 0;
        const maxHour = {max_fxx};
        
        function updateHour(h) {{
            currentHour = parseInt(h);
            document.getElementById('main-image').src = `images/hrrr_ne_refc_f${{currentHour.toString().padStart(2, '0')}}.png`;
            document.getElementById('hour-label').textContent = `F${{currentHour.toString().padStart(2, '0')}}`;
        }}
        
        function prevHour() {{ 
            let h = Math.max(0, currentHour - 1); 
            document.getElementById('hour-slider').value = h;
            updateHour(h);
        }}
        
        function nextHour() {{ 
            let h = Math.min(maxHour, currentHour + 1); 
            document.getElementById('hour-slider').value = h;
            updateHour(h);
        }}
        
        // Keyboard support
        document.addEventListener('keydown', function(e) {{
            if (e.key === "ArrowLeft") prevHour();
            if (e.key === "ArrowRight") nextHour();
        }});
    </script>
</body>
</html>"""
    with open("index.html", "w") as f:
        f.write(html)

if __name__ == "__main__":
    main()
