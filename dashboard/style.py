"""The page's visual system.

The layout language is borrowed from Stripe's: a very light blue-grey ground,
white cards with a soft two-layer shadow, deep navy ink, hairline vertical
guides, and small letterspaced labels. It is the most thoroughly proven system
in financial software, and a trading agent should look like it belongs there.
"""

CSS = """
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+Devanagari:wght@600&display=swap">
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+Devanagari:wght@600&display=swap');

:root{
  --ground:#F6F9FC; --card:#FFFFFF; --line:#E3E8EE; --line-2:#EEF2F7;
  --ink:#0A2540; --body:#425466; --muted:#697386; --faint:#8792A2;
  --green:#0E7C66; --green-soft:#E6F2EF;
  --red:#CD3D64; --red-soft:#FCEBEF;
  --sans:'Instrument Sans','Helvetica Neue',Helvetica,Arial,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,'SF Mono',Menlo,monospace;
  --shadow:0 2px 5px -1px rgba(50,50,93,.09), 0 1px 3px -1px rgba(0,0,0,.07);
  --shadow-lg:0 15px 35px -5px rgba(50,50,93,.10), 0 5px 15px -5px rgba(0,0,0,.07);
  --r:8px;
}

/* Streamlit chrome. !important is required; emotion wins the cascade otherwise. */
header[data-testid="stHeader"]{height:0!important;min-height:0!important;background:transparent!important;}
[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],
[data-testid="stSidebar"],#MainMenu,footer{display:none!important;}
[data-testid="stVerticalBlock"]{gap:0!important;}
[data-testid="stMainBlockContainer"],.block-container{
  max-width:1180px!important;padding:0 40px 88px!important;}
.stApp,[data-testid="stAppViewContainer"]{background:var(--ground);}
[data-testid="stMarkdownContainer"] p:not([class]){margin:0;}

html,body,.stApp{color:var(--body);font-family:var(--sans);
  -webkit-font-smoothing:antialiased;}
.sd-wrap *{box-sizing:border-box;}
.sd-wrap svg{display:block;width:100%;height:auto;}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums lining-nums;}
.num{font-variant-numeric:tabular-nums lining-nums;}

/* the hairline guides that run the height of the page */
.stApp::before,.stApp::after{content:"";position:fixed;top:0;bottom:0;width:1px;
  background:var(--line);z-index:0;pointer-events:none;}
.stApp::before{left:calc(50% - 590px);} .stApp::after{left:calc(50% + 589px);}
@media (max-width:1260px){.stApp::before,.stApp::after{display:none;}}

/* type devices */
.eyebrow{font-family:var(--sans);font-weight:600;font-size:.75rem;letter-spacing:.06em;
  text-transform:uppercase;color:var(--green);}
.eyebrow.plain{color:var(--faint);}
.h2{font-family:var(--sans);font-weight:600;font-size:1.75rem;line-height:1.25;
  color:var(--ink);letter-spacing:-.018em;margin:10px 0 12px;max-width:22ch;}
.lead{font-size:1.0625rem;line-height:1.6;color:var(--body);max-width:62ch;margin:0 0 8px;}
.prose{font-size:.9375rem;line-height:1.62;color:var(--body);max-width:64ch;}
.note{font-size:.8125rem;line-height:1.55;color:var(--muted);}
.quote{font-size:1rem;line-height:1.6;color:var(--ink);max-width:60ch;}
.sec{margin-top:80px;margin-bottom:24px;}

/* top bar */
.bar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;
  padding:22px 0 20px;border-bottom:1px solid var(--line);}
.mark{display:flex;align-items:center;gap:10px;}
.dev{font-family:'Noto Sans Devanagari',serif;font-weight:600;font-size:1.0625rem;
  color:var(--ink);line-height:1;}
.wordmark{font-weight:700;font-size:1.0625rem;letter-spacing:-.01em;color:var(--ink);}
.bar .tag{font-size:.8125rem;color:var(--muted);padding-left:14px;border-left:1px solid var(--line);}
.bar .right{margin-left:auto;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
.pill{display:inline-flex;align-items:center;gap:7px;padding:4px 11px;border-radius:999px;
  font-size:.75rem;font-weight:600;letter-spacing:.02em;
  background:var(--green-soft);color:var(--green);}
.pill.off{background:#EDF1F6;color:var(--muted);}
.pill i{width:6px;height:6px;border-radius:999px;background:currentColor;}

/* hero */
.hero{padding:56px 0 8px;}
.hero h1{font-family:var(--sans);font-weight:700;font-size:clamp(2rem,4.2vw,3.25rem);
  line-height:1.08;letter-spacing:-.032em;color:var(--ink);margin:14px 0 0;max-width:17ch;}
.hero h1 em{font-style:normal;color:var(--green);}
.hero .sub{margin-top:22px;font-size:1.0625rem;line-height:1.62;color:var(--body);max-width:56ch;}

/* cards */
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
  box-shadow:var(--shadow);}
.card.raised{box-shadow:var(--shadow-lg);}
.pad{padding:26px 28px;}
.grid2{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;}
.grid37{display:grid;grid-template-columns:minmax(0,4fr) minmax(0,6fr);gap:24px;align-items:start;}

/* stat strip inside a card */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));}
.stat{padding:22px 24px;border-left:1px solid var(--line);}
.stat:first-child{border-left:none;}
.stat .k{font-size:.75rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  color:var(--faint);}
.stat .v{margin-top:9px;font-size:1.625rem;font-weight:600;letter-spacing:-.02em;
  color:var(--ink);font-variant-numeric:tabular-nums lining-nums;}
.stat .s{margin-top:6px;font-size:.8125rem;color:var(--muted);}
.stat .v.pos{color:var(--green);} .stat .v.neg{color:var(--red);}

/* the two headline figures */
.tally{display:flex;gap:40px;align-items:flex-start;}
.fig{font-size:3rem;font-weight:700;line-height:1;letter-spacing:-.035em;color:var(--ink);
  font-variant-numeric:tabular-nums lining-nums;}
.fig.go{color:var(--green);}
.fig-k{margin-top:8px;font-size:.75rem;font-weight:600;letter-spacing:.05em;
  text-transform:uppercase;color:var(--faint);}
.ratio{display:flex;height:6px;border-radius:999px;overflow:hidden;margin-top:20px;
  background:var(--line);}
.ratio span:first-child{background:var(--ink);}
.ratio span:last-child{background:var(--green);}

/* legend */
.legend{display:flex;gap:24px;flex-wrap:wrap;margin-top:16px;
  font-size:.75rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--faint);}
.legend i{display:inline-block;vertical-align:middle;margin-right:8px;}
.legend .sw-stop{width:16px;height:5px;border-radius:2px;background:var(--ink);}
.legend .sw-pass{width:16px;height:2px;background:#C9D3DF;}
.legend .sw-sent{width:7px;height:7px;border-radius:2px;background:var(--green);}

/* stop ledger */
.stop{display:grid;grid-template-columns:52px minmax(0,1fr) 132px;gap:22px;align-items:center;
  padding:18px 28px;border-top:1px solid var(--line-2);}
.stop:first-child{border-top:none;}
.stop .c{font-size:1.25rem;font-weight:700;color:var(--ink);text-align:right;
  font-variant-numeric:tabular-nums;}
.stop .nm{font-size:.9375rem;font-weight:600;color:var(--ink);}
.stop .why{font-size:.875rem;line-height:1.5;color:var(--body);margin-top:3px;}
.stop .verbatim{font-family:var(--mono);font-size:.75rem;color:var(--muted);margin-top:7px;
  background:var(--ground);border:1px solid var(--line);border-radius:5px;
  padding:5px 8px;display:inline-block;overflow-wrap:anywhere;}
.stop .bar{height:5px;border-radius:999px;background:var(--line);}
.stop .bar i{display:block;height:5px;border-radius:999px;background:var(--ink);}

/* roster chips */
.roster{display:flex;flex-wrap:wrap;gap:7px;}
.chip{display:inline-flex;align-items:center;gap:7px;padding:5px 10px;border-radius:6px;
  border:1px solid var(--line);background:var(--card);
  font-size:.75rem;font-weight:500;color:var(--muted);}
.chip b{width:6px;height:6px;border-radius:2px;background:var(--line);}
.chip.fired{border-color:#C6D2E1;color:var(--ink);font-weight:600;}
.chip.fired b{background:var(--ink);}

/* worksheet */
.ld{display:flex;align-items:baseline;gap:.6ch;padding:11px 0;
  border-bottom:1px solid var(--line-2);}
.ld:last-child{border-bottom:none;}
.ld .t{font-size:.9375rem;color:var(--body);}
.ld .d{flex:1;min-width:1ch;}
.ld .v{font-size:.9375rem;font-weight:500;color:var(--ink);
  font-variant-numeric:tabular-nums lining-nums;}
.ld.total{border-top:1px solid var(--ink);border-bottom:none;margin-top:6px;padding-top:14px;}
.ld.total .t{font-weight:600;color:var(--ink);}
.ld.total .v{font-weight:700;font-size:1.125rem;}

/* outcome strip */
.strip{display:flex;flex-wrap:wrap;gap:5px;}
.sq{width:11px;height:11px;border-radius:3px;background:var(--green);}
.sq.out{background:transparent;box-shadow:inset 0 0 0 1px #C9D3DF;}

/* decision log */
.log .head,.log .row{display:grid;
  grid-template-columns:88px minmax(0,1.15fr) 88px 200px minmax(0,1fr);
  gap:18px;padding:14px 28px;align-items:baseline;border-top:1px solid var(--line-2);}
.log .head{border-top:none;border-bottom:1px solid var(--line);background:var(--ground);
  border-radius:var(--r) var(--r) 0 0;padding-top:12px;padding-bottom:12px;
  font-size:.6875rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--faint);}
.log .row:first-of-type{border-top:none;}
.log .t{font-family:var(--mono);font-size:.75rem;color:var(--muted);}
.log .s{font-size:.8125rem;color:var(--ink);font-variant-numeric:tabular-nums;overflow-wrap:anywhere;}
.log .r{font-family:var(--mono);font-size:.75rem;color:var(--muted);overflow-wrap:anywhere;}
.log .k{font-size:.8125rem;font-weight:500;color:var(--ink);}
.log .k.none{color:var(--faint);}
.badge{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:5px;
  font-size:.6875rem;font-weight:600;letter-spacing:.03em;text-transform:uppercase;}
.badge.stopped{background:#EDF1F6;color:var(--ink);}
.badge.sent{background:var(--green-soft);color:var(--green);}

/* footer */
.foot{margin-top:80px;padding-top:26px;border-top:1px solid var(--line);
  font-size:.8125rem;line-height:1.75;color:var(--faint);}

/* responsive */
.only-wide{display:block;} .only-narrow{display:none;}
@media (max-width:1080px){
  .only-wide{display:none;} .only-narrow{display:block;}
  .only-narrow svg{max-width:560px;margin:0 auto;}
  .grid37,.grid2{grid-template-columns:minmax(0,1fr);}
}
@media (max-width:680px){
  [data-testid="stMainBlockContainer"],.block-container{padding:0 18px 56px!important;}
  .sec{margin-top:52px;margin-bottom:18px;}
  .hero{padding:34px 0 4px;}
  .stats{grid-template-columns:1fr 1fr;}
  .stat{border-left:1px solid var(--line);border-top:1px solid var(--line);padding:18px 16px;}
  .stat:nth-child(odd){border-left:none;}
  .stat:nth-child(1),.stat:nth-child(2){border-top:none;}
  .stat .v{font-size:1.375rem;}
  .tally{gap:28px;} .fig{font-size:2.5rem;}
  .stop{grid-template-columns:44px minmax(0,1fr);gap:14px;padding:16px 18px;}
  .stop .bar{display:none;}
  .pad{padding:20px 18px;}
  .log .head{display:none;}
  .log .row{grid-template-columns:minmax(0,1fr);gap:6px;padding:16px 18px;}
}
</style>
"""
