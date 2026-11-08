# Slide Layouts Reference

Author `slides.html` using these patterns. `assets/carousel.css` locks the brand —
never inline colors, fonts, or sizes. Pick the layout that fits each slide's job;
don't force one layout on every slide.

## File skeleton

`slides.html` lives in the run folder. The CSS is copied next to it as
`carousel.css`, the illustrations sit in `images/`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="carousel.css">
</head>
<body>

  <!-- one .slide div per carousel slide, in order -->
  <div class="slide"> ... </div>
  <div class="slide"> ... </div>

</body>
</html>
```

Every `.slide` is exactly 1080×1350. `render.mjs` screenshots each one in order.

## Rules every slide follows

- **One idea per slide.** If it needs two sentences of explanation, it's two slides.
- **One teal element per slide.** The kicker is teal by default — if a slide has a
  kicker, that IS the teal element; don't also add `.accent` or `.highlight`.
- **Footer on every slide except the cover.** Handle left, slide number right.
- **No gradients, no drop shadows, no emoji** in slide chrome. Inter only.
- Keep visible words low — social attention. Headlines ≤ 12 words, body ≤ 30.

## Footer (all slides except cover)

```html
<div class="slide__footer">
  <span>@thecraighewitt</span>
  <span>03 / 07</span>
</div>
```

## Layout: Cover (slide 1 — the hook)

Teal variant. No footer. This is the scroll-stopper.

```html
<div class="slide slide--teal stack gap-md">
  <span class="kicker">AI for Marketing</span>
  <div class="grow stack center gap-md">
    <h1 class="title title--lg">The hook headline that earns the swipe</h1>
    <p class="body">One line of context or a promise.</p>
  </div>
  <div class="swipe"><span class="swipe__arrow">→</span><span>Swipe</span></div>
</div>
```

## Layout: Statement / content slide

```html
<div class="slide stack gap-md">
  <span class="kicker">Step 01</span>
  <div class="grow stack center gap-md">
    <h2 class="title">The one point this slide makes</h2>
    <p class="body body--gray">Supporting line. Short.</p>
  </div>
  <div class="slide__footer"><span>@thecraighewitt</span><span>02 / 07</span></div>
</div>
```

## Layout: Big stat

The number is the slide. Use for one striking figure.

```html
<div class="slide stack gap-md">
  <span class="kicker">The gap</span>
  <div class="grow stack center">
    <div class="stat">88%</div>
    <p class="body">of cited URLs already rank in search.</p>
  </div>
  <div class="slide__footer"><span>@thecraighewitt</span><span>04 / 07</span></div>
</div>
```

## Layout: Numbered steps

For a short process — 2-4 steps max on one slide.

```html
<div class="slide stack gap-md">
  <span class="kicker">The fix</span>
  <h2 class="title--sm title">Three writing moves</h2>
  <div class="grow stack center">
    <div class="steps">
      <div class="step"><div class="step__num">1</div><div class="step__text">Lead with the answer.</div></div>
      <div class="step"><div class="step__num">2</div><div class="step__text">Write it as fact.</div></div>
      <div class="step"><div class="step__num">3</div><div class="step__text">Name the noun.</div></div>
    </div>
  </div>
  <div class="slide__footer"><span>@thecraighewitt</span><span>05 / 07</span></div>
</div>
```

## Layout: Quote / declarative

```html
<div class="slide stack gap-md">
  <div class="grow stack center gap-md">
    <span class="quote__mark">"</span>
    <p class="quote">Ranking gets you found. <span class="accent">Being cited</span> gets you trusted.</p>
  </div>
  <div class="slide__footer"><span>@thecraighewitt</span><span>03 / 07</span></div>
</div>
```

## Layout: Comparison (this vs that)

```html
<div class="slide stack gap-md">
  <span class="kicker">Before / after</span>
  <div class="grow stack center">
    <div class="compare">
      <div class="compare__col">
        <span class="compare__label">Vague</span>
        <p class="body">"Ahrefs helps with a metric that's vague."</p>
      </div>
      <div class="compare__col compare__col--win">
        <span class="compare__label">Precise</span>
        <p class="body">"Ahrefs improves Core Web Vitals."</p>
      </div>
    </div>
  </div>
  <div class="slide__footer"><span>@thecraighewitt</span><span>06 / 07</span></div>
</div>
```

## Layout: Image + caption (uses a GPT Image (OpenAI) illustration)

For image slides only. The illustration goes in `images/`, referenced relative.

```html
<div class="slide stack gap-md">
  <span class="kicker">How it works</span>
  <h2 class="title title--sm">The workflow, drawn out</h2>
  <img class="illus illus--grow" src="images/slide-04.png" alt="">
  <div class="slide__footer"><span>@thecraighewitt</span><span>04 / 07</span></div>
</div>
```

## Layout: CTA (final slide)

Teal variant. Tell them to save, follow, and comment.

```html
<div class="slide slide--teal stack gap-lg">
  <div class="grow stack center gap-md">
    <h2 class="title">Save this for your next post.</h2>
    <p class="body">Follow @thecraighewitt for more AI-for-marketing teardowns.</p>
    <p class="body">Comment <strong>"CITED"</strong> and I'll send you the checklist.</p>
  </div>
  <div class="slide__footer"><span>@thecraighewitt</span><span>07 / 07</span></div>
</div>
```
