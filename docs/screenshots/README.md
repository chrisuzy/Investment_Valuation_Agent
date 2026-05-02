# Screenshots — drop-in zone

This folder is where screenshots of the running app get embedded into the main
[README](../../README.md).

## Taking screenshots

### On macOS
1. Run the app locally following the [Quickstart](../../README.md#-quickstart).
2. Open each page listed below.
3. `Cmd+Shift+4` → Space → click the browser window. Saves to `~/Desktop`.
4. Rename to match the filename column below and drop into this folder.

### On Windows (where this project was developed)
1. Run the app locally.
2. `Win+Shift+S` → rectangular snip around the browser viewport.
3. Save with the filename below into this folder.

### Automated (future)
A Playwright / Puppeteer-based capture script is on the roadmap. Until then,
manual screenshots are fine.

## Target images

| Filename | Route | What to capture |
|---|---|---|
| `01-input-sheet.png` | `/` | Full Input Sheet with data populated — rows 1–15 visible. Hover one cell first so the tooltip shows in the screenshot. |
| `02-cost-of-capital.png` | `/wacc` | The methodology selectors panel on top + the computed WACC panel below. Bonus: hover over β_L so its formula tooltip appears. |
| `03-geographic-segments.png` | `/wacc` (scroll down) | The Geographic Revenue Mix panel with 3–4 segments visible, ideally with one dropdown expanded showing Damodaran countries + their ERPs. |
| `04-valuation-output.png` | `/valuation-output` | The 10-year projection table. Full width, with the equity bridge visible below it. |
| `05-summary-sheet.png` | `/summary` | Year-by-year revenue + margin + FCFF, terminal value, and the VPS-vs-market-price block. |
| `06-ttm.png` | `/ttm` | Trailing-12-month derivation showing FY-0 + quarters visible. |
| `07-rd-converter.png` | `/rd` | Amortization schedule with 5–10 years of R&D visible. |
| `08-option-value.png` | `/options` | Black-Scholes inputs + `d1`, `d2`, `N(d1)`, `N(d2)` + final call value. |
| `09-synthetic-rating.png` | `/rating` | Coverage ratio → rating mapping with current firm's bucket highlighted. |
| `10-unresolved-fields.png` | any | Upload a ticker that isn't in the Damodaran classification. The amber UnresolvedFieldsPanel banner appears at top — screenshot that. |

## Wiring into the README

Once a PNG lands here, edit the main README's "See the app" section.
Replace the collapsed page-inventory `<details>` block with
real embeds:

```markdown
![Cost of Capital page](docs/screenshots/02-cost-of-capital.png)

*Every methodology choice exposed as a dropdown; WACC recomputes live.*
```

GitHub renders relative-path PNGs inline on the repo landing page.

## Recommended sizing

- **Width:** 1440px (Retina-like), or 1200px (standard). Either looks fine on GitHub.
- **Format:** PNG (lossless — important for rendered text).
- **File size:** keep each under 500 KB via `pngquant` / `oxipng` if needed.
  ```bash
  pngquant --quality=70-90 --force --ext .png docs/screenshots/*.png
  ```
