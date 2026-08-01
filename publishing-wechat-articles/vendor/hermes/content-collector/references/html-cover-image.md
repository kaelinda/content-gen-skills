# HTML Cover Image Generation (Fallback)

When `image_generate` is unavailable (no FAL_KEY, no provider), generate cover images via HTML + browser screenshot.

## Steps

1. Write an HTML file to `/tmp/cover.html` with:
   - Fixed dimensions: 1200×514px (20:9 for WeChat)
   - Dark gradient background
   - CSS-only decorative elements (glow circles, grid, SVG lines)
   - Chinese title with highlight spans
   - Stats badges at bottom
   - `-apple-system, 'PingFang SC', sans-serif` font stack

2. Navigate: `browser_navigate(url="file:///tmp/cover.html")`

3. Screenshot: `browser_vision(question="Take a screenshot of this cover image")`

4. Copy from cache: `cp <screenshot_path> /tmp/cover-final.png`

## Design Tips
- Use `filter: blur(60px)` for glow effects (no images needed)
- `background-image` with linear-gradient for grid pattern
- Inline SVG for node connection lines
- `text-shadow` for title readability
- Stats in pill-shaped cards with `rgba` backgrounds
- Keep text centered, leave margin for WeChat crop

## WeChat Cover Requirements
- Aspect ratio: 20:9 (recommended 1080×486 or 1200×514)
- Title should be large and readable at thumbnail size
- Avoid small text in corners (cropped on mobile)
- Confirmed working: 1080×486 with dark gradient + grid + decorative circles
