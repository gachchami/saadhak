"""The page's entire visual system, injected once.

Targets three stable Streamlit test ids and our own class names. Never a
generated .st-emotion-cache-* selector, which changes between releases.
"""

CSS = """
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=Literata:ital,wght@0,400;1,400&family=Noto+Sans+Devanagari:wght@500&display=swap">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=Literata:ital,wght@0,400;1,400&family=Noto+Sans+Devanagari:wght@500&display=swap');

:root{
  --ground:#0E1417; --panel:#151E21; --rule:#223034; --rule-2:#1A2427;
  --chalk:#E9E6DD; --slate:#8C9A9D; --dim:#6E8085; --track:#455E64;
  --verdigris:#74B8A8; --oxide:#D2685A;
  --sans:'IBM Plex Sans Condensed','Helvetica Neue',Arial,sans-serif;
  --serif:'Literata',Georgia,'Times New Roman',serif;
  --mono:'IBM Plex Mono',ui-monospace,'SF Mono',Menlo,monospace;
}

/* Streamlit chrome. !important is required; emotion wins the cascade otherwise. */
header[data-testid="stHeader"]{height:0!important;min-height:0!important;background:transparent!important;}
[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],
[data-testid="stSidebar"],#MainMenu,footer{display:none!important;}
[data-testid="stVerticalBlock"]{gap:0!important;}
[data-testid="stMainBlockContainer"],.block-container{
  max-width:1304px!important;padding:20px 32px 72px!important;}
.stApp,[data-testid="stAppViewContainer"]{background:var(--ground);}

html,body,.stApp{color:var(--chalk);}
[data-testid="stMarkdownContainer"] p:not([class]){margin:0;}
.sd-wrap *{box-sizing:border-box;}
.sd-wrap svg{display:block;width:100%;height:auto;}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums lining-nums;}

/* shared type devices */
.eyebrow{font-family:var(--sans);font-weight:600;font-size:.6875rem;letter-spacing:.16em;
  text-transform:uppercase;color:var(--dim);}
.lead-rule{display:flex;align-items:center;gap:14px;margin:72px 0 14px;}
.lead-rule i{flex:1;height:1px;background:var(--rule);}
.lead{font-family:var(--serif);font-size:1.0625rem;line-height:1.6;color:var(--slate);
  max-width:64ch;margin:0 0 26px;}
.prose{font-family:var(--serif);font-size:.9375rem;line-height:1.6;color:var(--slate);max-width:64ch;}
.note{font-family:var(--mono);font-size:.6875rem;line-height:1.5;color:var(--dim);}
.quote{font-family:var(--serif);font-style:italic;font-size:.9375rem;line-height:1.65;
  color:var(--chalk);max-width:62ch;}

/* nameplate */
.plate{display:flex;align-items:baseline;flex-wrap:wrap;gap:14px;
  padding-bottom:16px;border-bottom:1px solid var(--rule);}
.dev{font-family:'Noto Sans Devanagari','Noto Serif Devanagari',serif;font-weight:500;
  font-size:1.25rem;color:var(--chalk);line-height:1;}
.wordmark{font-family:var(--sans);font-weight:600;font-size:.9375rem;letter-spacing:.22em;
  text-transform:uppercase;color:var(--chalk);}
.vr{width:1px;height:18px;background:var(--rule);align-self:center;}
.plate-right{margin-left:auto;display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.lamp{width:7px;height:7px;display:inline-block;background:var(--verdigris);}
.lamp.off{background:var(--dim);} .lamp.fault{background:var(--oxide);}

/* verdict block */
.verdict{display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr);gap:56px;margin-top:44px;}
.headline{font-family:var(--serif);font-size:clamp(1.5rem,2.6vw,2.125rem);line-height:1.25;
  color:var(--chalk);margin:0 0 20px;max-width:26ch;}
.headline .n{font-family:var(--mono);font-weight:500;}
.tally{display:flex;gap:44px;align-items:flex-start;}
.fig{font-family:var(--mono);font-weight:500;font-size:2.75rem;line-height:1;color:var(--chalk);
  font-variant-numeric:tabular-nums lining-nums;}
.fig.sent{color:var(--verdigris);}
.fig-lab{font-family:var(--sans);font-weight:600;font-size:.6875rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--dim);margin-top:8px;}
.ratio{display:flex;height:8px;margin-top:22px;}
.ratio span:first-child{background:var(--chalk);}
.ratio span:last-child{background:var(--track);border-left:1px solid var(--ground);}

/* readout bar */
.readouts{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  background:var(--panel);border:1px solid var(--rule);margin-top:44px;}
.cell{padding:22px 20px;border-left:1px solid var(--rule);}
.cell:first-child{border-left:none;}
.cell .lbl{font-family:var(--sans);font-weight:600;font-size:.6875rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--dim);}
.cell .val{font-family:var(--mono);font-weight:400;font-size:1.75rem;color:var(--chalk);
  font-variant-numeric:tabular-nums lining-nums;margin-top:10px;}
.cell .sub{font-family:var(--mono);font-size:.6875rem;color:var(--slate);margin-top:10px;
  padding-top:8px;border-top:1px solid var(--rule);}

/* hero legend */
.legend{display:flex;gap:28px;flex-wrap:wrap;margin-top:14px;
  font-family:var(--sans);font-weight:600;font-size:.6875rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--dim);}
.legend i{display:inline-block;vertical-align:middle;margin-right:8px;}
.legend .sw-stop{width:18px;height:5px;background:var(--chalk);}
.legend .sw-pass{width:18px;height:1px;background:var(--track);}
.legend .sw-sent{width:6px;height:6px;background:var(--verdigris);}

/* stop ledger */
.stops{margin-top:8px;border-top:1px solid var(--rule);}
.stop{display:grid;grid-template-columns:56px minmax(0,1fr) 140px;gap:24px;align-items:baseline;
  padding:16px 0;border-bottom:1px solid var(--rule-2);}
.stop .c{font-family:var(--mono);font-weight:500;font-size:1.375rem;color:var(--chalk);text-align:right;}
.stop .nm{font-family:var(--sans);font-weight:600;font-size:.8125rem;letter-spacing:.06em;
  text-transform:uppercase;color:var(--chalk);}
.stop .why{font-family:var(--serif);font-size:.8125rem;line-height:1.55;color:var(--slate);margin-top:5px;}
.stop .verbatim{font-family:var(--mono);font-size:.6875rem;color:var(--dim);margin-top:6px;
  overflow-wrap:anywhere;}
.stop .bar{height:4px;background:var(--rule);align-self:center;}
.stop .bar i{display:block;height:4px;background:var(--chalk);}

/* roster chips */
.roster{display:flex;flex-wrap:wrap;gap:8px;margin-top:24px;}
.chip{display:flex;align-items:center;gap:8px;padding:6px 10px;border:1px solid var(--rule);
  font-family:var(--sans);font-weight:500;font-size:.6875rem;letter-spacing:.06em;color:var(--dim);}
.chip.fired{border-color:var(--chalk);color:var(--chalk);}
.chip b{width:6px;height:6px;background:transparent;box-shadow:inset 0 0 0 1px var(--dim);}
.chip.fired b{background:var(--chalk);box-shadow:none;}

/* panels */
.panel{background:var(--panel);border:1px solid var(--rule);padding:22px 24px;}
.panel + .panel{margin-top:20px;}
.duo{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:32px;}

/* worksheet */
.sheet{margin-top:26px;max-width:560px;}
.ld{display:flex;align-items:baseline;gap:.6ch;padding:9px 0;}
.ld .t{font-family:var(--serif);font-size:.9375rem;color:var(--slate);}
.ld .d{flex:1;min-width:2ch;border-bottom:1px dotted var(--track);transform:translateY(-.3em);}
.ld .v{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:.9375rem;color:var(--chalk);}
.ld.total{border-top:2px solid var(--chalk);box-shadow:0 -5px 0 -4px var(--rule);margin-top:6px;padding-top:12px;}
.ld.total .t{color:var(--chalk);} .ld.total .v{font-weight:500;font-size:1.0625rem;}

/* outcome strip */
.strip{display:flex;flex-wrap:wrap;gap:6px;margin-top:22px;}
.sq{width:9px;height:9px;background:var(--chalk);}
.sq.out{background:transparent;box-shadow:inset 0 0 0 1px var(--track);}

/* decision log */
.log{border-top:1px solid var(--rule);margin-top:8px;}
.log .head,.log .row{display:grid;
  grid-template-columns:60px minmax(0,1.1fr) 92px 196px minmax(0,1fr);
  gap:20px;padding:13px 0;border-bottom:1px solid var(--rule-2);align-items:baseline;}
.log .head{border-bottom:1px solid var(--rule);padding-bottom:9px;
  font-family:var(--sans);font-weight:600;font-size:.6875rem;letter-spacing:.16em;
  text-transform:uppercase;color:var(--dim);}
.log .t{font-family:var(--mono);font-size:.6875rem;color:var(--dim);}
.log .s{font-family:var(--mono);font-size:.8125rem;color:var(--chalk);overflow-wrap:anywhere;}
.log .r{font-family:var(--mono);font-size:.6875rem;color:var(--slate);overflow-wrap:anywhere;}
.log .b{font-family:var(--sans);font-weight:600;font-size:.6875rem;letter-spacing:.14em;
  text-transform:uppercase;display:flex;align-items:center;gap:8px;}
.log .b.stopped{color:var(--chalk);} .log .b.stopped i{width:7px;height:7px;background:var(--chalk);}
.log .b.sent{color:var(--verdigris);} .log .b.sent i{width:7px;height:7px;background:var(--verdigris);}
.log .k{font-family:var(--sans);font-weight:500;font-size:.75rem;letter-spacing:.04em;color:var(--chalk);}
.log .k.none{color:var(--dim);}

/* empty state */
.empty{border:1px dashed var(--rule);padding:26px 24px;}
.empty .h{font-family:var(--sans);font-weight:600;font-size:.8125rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--chalk);}

/* footer */
.footer{border-top:1px solid var(--rule);margin-top:72px;padding-top:20px;
  font-family:var(--mono);font-size:.6875rem;line-height:1.8;color:var(--dim);}

/* responsive */
.only-wide{display:block;} .only-narrow{display:none;}
@media (max-width:1180px){
  .only-wide{display:none;} .only-narrow{display:block;}
  .only-narrow svg{max-width:560px;}
  .duo{grid-template-columns:minmax(0,1fr);gap:24px;}
}
@media (max-width:640px){
  [data-testid="stMainBlockContainer"],.block-container{padding:16px 16px 48px!important;}
  .lead-rule{margin:44px 0 12px;}
  .verdict{grid-template-columns:minmax(0,1fr);gap:28px;}
  .headline{max-width:none;}
  .tally{gap:32px;}
  .fig{font-size:2.25rem;}
  .cell{border-left:none;border-top:1px solid var(--rule);}
  .cell:first-child{border-top:none;}
  .stop{grid-template-columns:48px minmax(0,1fr);gap:16px;}
  .stop .bar{display:none;}
  .log .head{display:none;}
  .log .row{grid-template-columns:minmax(0,1fr);gap:6px;padding:14px 0;}
  .sheet{max-width:none;}
  .ld{flex-wrap:wrap;}
  .ld .d{min-width:1ch;}
}
</style>
"""
