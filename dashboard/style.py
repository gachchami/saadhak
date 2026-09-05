"""The app shell and its panels.

An operator's dashboard, not a page about one: a fixed left rail, a status bar,
a row of readouts, and a grid of panels. The palette and card treatment follow
Stripe's, which is the proven system for financial software.
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
  --amber:#B54708; --amber-soft:#FEF0C7;
  --sans:'Instrument Sans','Helvetica Neue',Helvetica,Arial,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,'SF Mono',Menlo,monospace;
  --shadow:0 1px 3px rgba(50,50,93,.08), 0 1px 2px rgba(0,0,0,.04);
  --r:8px;
}

/* --- shell ------------------------------------------------------------- */
header[data-testid="stHeader"]{height:0!important;min-height:0!important;background:transparent!important;}
[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],
#MainMenu,footer{display:none!important;}
[data-testid="stVerticalBlock"]{gap:0!important;}
.stApp,[data-testid="stAppViewContainer"]{background:var(--ground);}
[data-testid="stMarkdownContainer"] p:not([class]){margin:0;}
html,body,.stApp{color:var(--body);font-family:var(--sans);-webkit-font-smoothing:antialiased;}

[data-testid="stSidebar"]{background:var(--card)!important;border-right:1px solid var(--line);
  width:232px!important;min-width:232px!important;}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding:18px 16px 24px;}
[data-testid="stSidebarCollapseButton"],[data-testid="stSidebarCollapsedControl"]{display:none!important;}
[data-testid="stMainBlockContainer"],.block-container{
  max-width:1500px!important;padding:20px 26px 40px!important;}

/* --- left rail --------------------------------------------------------- */
.brand{display:flex;align-items:center;gap:9px;padding-bottom:16px;border-bottom:1px solid var(--line);}
.brand .dev{font-family:'Noto Sans Devanagari',serif;font-weight:600;font-size:1rem;color:var(--ink);}
.brand .wm{font-weight:700;font-size:1rem;letter-spacing:-.01em;color:var(--ink);}
.env{margin-left:auto;font-size:.625rem;font-weight:700;letter-spacing:.07em;
  padding:2px 6px;border-radius:4px;background:var(--amber-soft);color:var(--amber);}
.navlab{margin:20px 0 7px;font-size:.625rem;font-weight:700;letter-spacing:.09em;
  text-transform:uppercase;color:var(--faint);}
.nav a{display:block;padding:7px 10px;margin:1px -10px;border-radius:6px;
  font-size:.8125rem;font-weight:500;color:var(--body);text-decoration:none;}
.nav a:hover{background:var(--ground);color:var(--ink);}
.railbox{margin-top:20px;padding:12px;border:1px solid var(--line);border-radius:7px;
  background:var(--ground);}
.railbox .rk{font-size:.625rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;
  color:var(--faint);}
.railbox .rv{margin-top:5px;font-size:.8125rem;font-weight:600;color:var(--ink);
  font-variant-numeric:tabular-nums;}
.railfoot{margin-top:18px;font-size:.6875rem;line-height:1.6;color:var(--faint);
  font-family:var(--mono);word-break:break-all;}

/* --- status bar -------------------------------------------------------- */
.top{display:flex;align-items:center;gap:12px;flex-wrap:wrap;
  padding-bottom:16px;margin-bottom:18px;border-bottom:1px solid var(--line);}
.top h1{font-size:1.125rem;font-weight:600;letter-spacing:-.015em;color:var(--ink);margin:0;}
.top .sep{color:var(--line);} 
.top .right{margin-left:auto;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.pill{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:999px;
  font-size:.6875rem;font-weight:600;letter-spacing:.02em;background:var(--green-soft);color:var(--green);}
.pill.off{background:#EDF1F6;color:var(--muted);}
.pill.bad{background:var(--red-soft);color:var(--red);}
.pill i{width:6px;height:6px;border-radius:999px;background:currentColor;}
.stamp{font-size:.75rem;color:var(--faint);}

/* --- readouts ---------------------------------------------------------- */
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:14px;margin-bottom:16px;}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
  padding:13px 15px;box-shadow:var(--shadow);}
.kpi .k{font-size:.6875rem;font-weight:600;letter-spacing:.045em;text-transform:uppercase;color:var(--faint);}
.kpi .v{margin-top:7px;font-size:1.375rem;font-weight:600;letter-spacing:-.02em;color:var(--ink);
  font-variant-numeric:tabular-nums lining-nums;}
.kpi .v.pos{color:var(--green);} .kpi .v.neg{color:var(--red);}
.kpi .s{margin-top:4px;font-size:.6875rem;color:var(--muted);}

/* --- panels ------------------------------------------------------------ */
.row{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px;margin-bottom:14px;}
.c3{grid-column:span 3;} .c4{grid-column:span 4;} .c5{grid-column:span 5;}
.c6{grid-column:span 6;} .c7{grid-column:span 7;} .c8{grid-column:span 8;}
.c9{grid-column:span 9;} .c12{grid-column:span 12;}
.panel{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
  box-shadow:var(--shadow);display:flex;flex-direction:column;min-width:0;}
.ph{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--line-2);}
.ph h3{margin:0;font-size:.8125rem;font-weight:600;letter-spacing:-.005em;color:var(--ink);}
.ph .meta{margin-left:auto;font-size:.6875rem;color:var(--faint);}
.pb{padding:16px;flex:1;min-width:0;}
.pb.flush{padding:0;}
.pb .sd-wrap svg{display:block;width:100%;height:auto;}
.note{font-size:.75rem;line-height:1.55;color:var(--muted);}
.prose{font-size:.8125rem;line-height:1.6;color:var(--body);}
.quote{font-size:.875rem;line-height:1.6;color:var(--ink);}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums lining-nums;}

/* --- funnel ------------------------------------------------------------ */
.fn{display:flex;flex-direction:column;gap:1px;}
.fnr{display:grid;grid-template-columns:34px 1fr auto;gap:10px;align-items:center;padding:6px 0;}
.fnr .n{font-size:.9375rem;font-weight:600;color:var(--ink);text-align:right;
  font-variant-numeric:tabular-nums;}
.fnr .t{height:20px;border-radius:3px;background:var(--line-2);position:relative;overflow:hidden;}
.fnr .t i{position:absolute;inset:0 auto 0 0;background:#CBD5E1;}
.fnr.keep .t i{background:var(--ink);}
.fnr.good .t i{background:var(--green);}
.fnr .l{font-size:.75rem;color:var(--body);white-space:nowrap;}

/* --- tables ------------------------------------------------------------ */
.tb{width:100%;}
.tb .th,.tb .tr{display:grid;gap:12px;padding:9px 16px;align-items:baseline;
  border-top:1px solid var(--line-2);}
.tb .th{border-top:none;background:var(--ground);color:var(--faint);
  font-size:.625rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;}
.tb .tr:hover{background:#FBFCFE;}
.tb .num{text-align:right;font-variant-numeric:tabular-nums;}
.log .th,.log .tr{grid-template-columns:92px minmax(0,1.1fr) 74px 176px minmax(0,1fr);}
.cls .th,.cls .tr{grid-template-columns:96px minmax(0,1fr) 96px 96px 92px;}
.stp .th,.stp .tr{grid-template-columns:38px minmax(0,1fr) 110px;}
.t-dim{font-family:var(--mono);font-size:.6875rem;color:var(--muted);}
.t-ink{font-size:.75rem;color:var(--ink);}
.t-sub{font-size:.6875rem;color:var(--muted);margin-top:2px;}
.t-mono{font-family:var(--mono);font-size:.6875rem;color:var(--muted);overflow-wrap:anywhere;}
.chipcode{font-family:var(--mono);font-size:.6875rem;color:var(--muted);background:var(--ground);
  border:1px solid var(--line);border-radius:4px;padding:2px 6px;display:inline-block;}
.badge{display:inline-flex;align-items:center;padding:2px 7px;border-radius:4px;
  font-size:.625rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;}
.badge.stop{background:#EDF1F6;color:var(--ink);}
.badge.sent{background:var(--green-soft);color:var(--green);}
.badge.loss{background:var(--red-soft);color:var(--red);}
.bar{height:5px;border-radius:999px;background:var(--line-2);}
.bar i{display:block;height:5px;border-radius:999px;background:var(--ink);}

/* --- misc -------------------------------------------------------------- */
.roster{display:flex;flex-wrap:wrap;gap:6px;}
.chip{display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:5px;
  border:1px solid var(--line);font-size:.6875rem;font-weight:500;color:var(--muted);}
.chip b{width:5px;height:5px;border-radius:2px;background:var(--line);}
.chip.fired{border-color:#C6D2E1;color:var(--ink);font-weight:600;}
.chip.fired b{background:var(--ink);}
.ld{display:flex;align-items:baseline;gap:.6ch;padding:8px 0;border-bottom:1px solid var(--line-2);}
.ld:last-child{border-bottom:none;}
.ld .t{font-size:.8125rem;color:var(--body);} .ld .d{flex:1;}
.ld .v{font-size:.8125rem;font-weight:500;color:var(--ink);font-variant-numeric:tabular-nums;}
.ld.total{border-top:1px solid var(--ink);border-bottom:none;margin-top:4px;padding-top:10px;}
.ld.total .t{font-weight:600;color:var(--ink);} .ld.total .v{font-weight:700;font-size:.9375rem;}
.strip{display:flex;flex-wrap:wrap;gap:4px;}
.sq{width:10px;height:10px;border-radius:2px;background:var(--green);}
.sq.out{background:transparent;box-shadow:inset 0 0 0 1px #C9D3DF;}
.foot{margin-top:22px;padding-top:16px;border-top:1px solid var(--line);
  font-size:.6875rem;line-height:1.7;color:var(--faint);}

.only-wide{display:block;} .only-narrow{display:none;}
@media (max-width:1240px){
  .kpis{grid-template-columns:repeat(3,minmax(0,1fr));}
  .c4,.c5,.c6,.c7,.c8,.c9{grid-column:span 12;}
}
@media (max-width:900px){
  .only-wide{display:none;} .only-narrow{display:block;}
  .only-narrow svg{max-width:520px;margin:0 auto;}
  /* the rail carries nav and status the top bar repeats, so drop it rather
     than let a fixed 232px push the screen sideways */
  [data-testid="stSidebar"]{display:none!important;}
  section.main,[data-testid="stAppViewContainer"] > .main{width:100%!important;}
}
@media (max-width:680px){
  [data-testid="stMainBlockContainer"],.block-container{padding:14px 14px 32px!important;}
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}
  .c3{grid-column:span 12;}
  .log .th,.cls .th,.stp .th{display:none;}
  .log .tr,.cls .tr{grid-template-columns:minmax(0,1fr);gap:5px;}
  .stp .tr{grid-template-columns:32px minmax(0,1fr);}
}
</style>
"""
