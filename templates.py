"""قالب‌های HTML صفحه‌ی ورود و داشبورد .

بازطراحی کامل — کانسپت «Ops Console»: یک زبان بصری یکپارچه برای هر
سه صفحه (ورود، داشبورد، Subscription) به‌جای سه سبک ناهمخوان قبلی.
پس‌زمینه‌ی مشکی-سرمه‌ای عمیق با یک تک‌رنگ سیگنال زمردی (Emerald) برای
وضعیت/تأیید و یک آبی آسمانی کم‌رنگ برای داده‌های ثانویه؛ کارت‌ها با
مرز ظریف و یک هایلایت بالا، به‌جای افکت‌های نئون یا گرادیان تصادفی.
تایپوگرافی: Vazirmatn برای متن فارسی، JetBrains Mono برای داده‌های
عددی/فنی (شناسه‌ها، نرخ‌ها، زمان‌ها).

تمام شناسه‌ها (id)، کلاس‌های وابسته به جاوااسکریپت، و پلیس‌هولدرهای
__…__ صفحه‌ی Subscription دقیقاً از نسخه‌ی قبلی حفظ شده‌اند تا هیچ
عملکردی نشکند؛ فقط زبان بصری بازطراحی شده است.
"""

FONT_LINKS = """<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">"""

BASE_TOKENS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0f1c;--bg2:#0d1420;--surface:#111a2b;--surface2:#16213a;--surface3:#1c2a42;
  --line:rgba(234,240,247,.09);--line-soft:rgba(234,240,247,.05);--line-hi:rgba(52,211,153,.45);
  --accent:#34d399;--accent-deep:#10b981;--accent-soft:rgba(52,211,153,.12);--accent-ink:#052e1c;
  --info:#38bdf8;--info-soft:rgba(56,189,248,.12);
  --relay:#f59e0b;--relay-soft:rgba(245,158,11,.12);
  --danger:#f87171;--danger-soft:rgba(248,113,113,.12);
  --ok:#34d399;--green:#34d399;
  --text:#eaf0f7;--text-dim:#8b99af;--text-dim2:#4c5a73;--muted:#8b99af;
  --shadow:0 24px 60px -18px rgba(0,0,0,.6);
  --f-display:'Vazirmatn','Segoe UI',Tahoma,sans-serif;
  --f-body:'Vazirmatn','Segoe UI',Tahoma,sans-serif;
  --f-mono:'JetBrains Mono',ui-monospace,'SFMono-Regular',Consolas,Menlo,monospace;
}
html,body{height:100%}
::-webkit-scrollbar{width:7px;height:7px}::-webkit-scrollbar-thumb{background:#1c2a42;border-radius:4px}
a{color:inherit;text-decoration:none}
button,input,select{font:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important}}
"""

SIGNAL_SVG_DEFS = """<defs>
  <linearGradient id="sg1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#34d399"/><stop offset="1" stop-color="#38bdf8"/></linearGradient>
  <linearGradient id="sg2" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#38bdf8"/><stop offset="1" stop-color="#34d399"/></linearGradient>
</defs>"""

BRAND_MARK_SVG = """<circle cx="12" cy="15.5" r="2.1" fill="url(#sg1)"/>
  <path d="M12 15.5V6" stroke="url(#sg1)" stroke-width="2" stroke-linecap="round"/>
  <path d="M8.2 8.6a5.2 5.2 0 0 1 7.6 0" stroke="url(#sg1)" stroke-width="1.8" stroke-linecap="round" fill="none" opacity=".9"/>
  <path d="M5.6 6.1a8.8 8.8 0 0 1 12.8 0" stroke="url(#sg1)" stroke-width="1.8" stroke-linecap="round" fill="none" opacity=".55"/>"""
LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ورود · </title>
""" + FONT_LINKS + """
<style>
""" + BASE_TOKENS + """
body{font-family:var(--f-body);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px;background:var(--bg);position:relative;overflow:hidden}

body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:
    linear-gradient(rgba(234,240,247,.035) 1px,transparent 1px),
    linear-gradient(90deg,rgba(234,240,247,.035) 1px,transparent 1px);
  background-size:44px 44px;
  mask-image:radial-gradient(circle at 50% 26%, black, transparent 68%);}

.glow{position:absolute;border-radius:50%;filter:blur(100px);pointer-events:none}
.glow.g1{width:380px;height:380px;background:var(--accent);opacity:.16;top:-160px;left:50%;transform:translateX(-50%)}
.glow.g2{width:280px;height:280px;background:var(--info);opacity:.12;bottom:-120px;right:6%}

.wrap{position:relative;z-index:2;width:100%;max-width:384px}
.beacon{display:flex;flex-direction:column;align-items:center;margin-bottom:28px}
.beacon-ring{position:relative;width:84px;height:84px;display:flex;align-items:center;justify-content:center;margin-bottom:18px}
.beacon-ring svg.arc{position:absolute;inset:0;width:100%;height:100%}
.beacon-ring .arc-spin{animation:spin 16s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.beacon-core{position:relative;z-index:2;width:54px;height:54px;border-radius:16px;
  background:linear-gradient(155deg,var(--surface2),var(--surface));border:1px solid var(--line-hi);
  display:flex;align-items:center;justify-content:center;box-shadow:0 14px 32px -10px rgba(52,211,153,.35), 0 1px 0 rgba(255,255,255,.06) inset}
.beacon-core svg{width:27px;height:27px}
.beacon-name{font-family:var(--f-display);font-weight:700;font-size:21px;letter-spacing:.02em;
  background:linear-gradient(90deg,#fff,var(--accent));-webkit-background-clip:text;background-clip:text;color:transparent}
.beacon-tag{font-family:var(--f-mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--text-dim2);margin-top:5px}

.card{position:relative;background:linear-gradient(180deg,var(--surface2),var(--surface));
  border:1px solid var(--line);border-radius:20px;padding:32px 28px 28px;
  box-shadow:var(--shadow), 0 1px 0 rgba(255,255,255,.04) inset}
.card::before{content:'';position:absolute;top:0;right:26px;left:26px;height:1px;
  background:linear-gradient(90deg,transparent,var(--accent),transparent);opacity:.55}

.card-lead{font-size:13px;color:var(--text-dim);text-align:center;margin-bottom:24px;line-height:1.75}
.field-full{margin-bottom:18px}
.field-full label{display:flex;align-items:center;gap:6px;font-size:11px;font-family:var(--f-mono);
  color:var(--text-dim);margin-bottom:8px;letter-spacing:.05em;text-transform:uppercase}
.field-full input{width:100%;padding:13px 15px;border-radius:12px;border:1px solid var(--line);
  background:rgba(0,0,0,.28);color:var(--text);font-family:var(--f-body);font-size:14px;outline:none;
  box-shadow:0 2px 6px rgba(0,0,0,.3) inset;transition:.15s}
.field-full input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft), 0 2px 6px rgba(0,0,0,.3) inset}

.err{display:none;align-items:center;gap:8px;background:var(--danger-soft);border:1px solid rgba(248,113,113,.3);
  color:#ffc4c4;border-radius:11px;padding:10px 13px;font-size:12.5px;margin-bottom:16px}
.err.show{display:flex}

.submit{width:100%;padding:14px;border-radius:12px;border:none;font-family:var(--f-body);font-weight:700;
  font-size:14px;cursor:pointer;background:linear-gradient(180deg,#5eead4,var(--accent));color:var(--accent-ink);
  display:flex;align-items:center;justify-content:center;gap:8px;
  box-shadow:0 1px 0 rgba(255,255,255,.45) inset, 0 12px 24px -10px rgba(52,211,153,.55);transition:.15s}
.submit:hover{filter:brightness(1.06);transform:translateY(-1px)}
.submit:active{transform:translateY(0)}
.submit:disabled{opacity:.6;cursor:not-allowed;transform:none}

.foot{margin-top:24px;text-align:center;font-family:var(--f-mono);font-size:10px;letter-spacing:.12em;
  color:var(--text-dim2);text-transform:uppercase}
</style>
</head>
<body>
<div class="glow g1"></div>
<div class="glow g2"></div>

<div class="wrap">
  <div class="beacon">
    <div class="beacon-ring">
      <svg class="arc arc-spin" viewBox="0 0 84 84">
        <circle cx="42" cy="42" r="38" fill="none" stroke="url(#sg1)" stroke-width="1.4" stroke-dasharray="6 10" opacity=".5"/>
        """ + SIGNAL_SVG_DEFS + """
      </svg>
      <svg class="arc" viewBox="0 0 84 84">
        <circle cx="42" cy="42" r="30" fill="none" stroke="url(#sg2)" stroke-width="1" opacity=".28"/>
      </svg>
      <div class="beacon-core">
        <svg viewBox="0 0 24 24" fill="none">""" + BRAND_MARK_SVG + """</svg>
      </div>
    </div>
    <div class="beacon-name"></div>
    <div class="beacon-tag">Gateway Control</div>
  </div>

  <div class="card">
    <p class="card-lead" id="lead">در حال بررسی وضعیت راه‌اندازی پنل...</p>
    <div class="err" id="err"><i class="ti ti-alert-triangle"></i><span id="err-text"></span></div>
    <form id="form">
      <div class="field-full">
        <label><i class="ti ti-key"></i> <span id="label1">رمز عبور</span></label>
        <input type="password" id="password" placeholder="••••••••" autofocus required autocomplete="current-password" minlength="4">
      </div>
      <div class="field-full" id="confirmWrap" style="display:none">
        <label><i class="ti ti-key"></i> تکرار رمز عبور</label>
        <input type="password" id="passwordConfirm" placeholder="••••••••" autocomplete="new-password" minlength="4">
      </div>
      <div id="hint" style="display:none;font-size:11px;line-height:1.9;color:var(--text-dim);margin:-4px 0 14px">حداقل ۴ کاراکتر؛ می‌تواند شامل هر نوع حرف، عدد یا نماد باشد.</div>
      <button class="submit" id="btn" type="submit"><i class="ti ti-bolt"></i> ورود به پنل</button>
    </form>
    <div class="foot">Gateway · Encrypted Session</div>
  </div>
</div>

<script>
const form = document.getElementById('form');
const btn = document.getElementById('btn');
const errBox = document.getElementById('err');
const errText = document.getElementById('err-text');
const lead = document.getElementById('lead');
const label1 = document.getElementById('label1');
const confirmWrap = document.getElementById('confirmWrap');
const hint = document.getElementById('hint');
let setupMode = false;

function showErr(msg){ errText.textContent = msg; errBox.classList.add('show'); }
function setSetupMode(enabled){
  setupMode = enabled;
  if(enabled){
    lead.textContent = 'پنل برای اولین بار راه‌اندازی می‌شود. رمز ورود مدیریت را خودت تعیین کن.';
    label1.textContent = 'رمز جدید پنل';
    confirmWrap.style.display = '';
    hint.style.display = '';
    document.getElementById('password').autocomplete = 'new-password';
    btn.innerHTML = '<i class="ti ti-shield-check"></i> ذخیره رمز و ورود';
  }else{
    lead.textContent = 'برای ورود به پنل مدیریت رله، رمز عبور را وارد کنید.';
    label1.textContent = 'رمز عبور';
    confirmWrap.style.display = 'none';
    hint.style.display = 'none';
    btn.innerHTML = '<i class="ti ti-bolt"></i> ورود به پنل';
  }
}

(async()=>{
  try{
    const r = await fetch('/api/setup-status', {cache:'no-store'});
    const d = await r.json();
    setSetupMode(Boolean(d.setup_required));
  }catch(e){
    setSetupMode(false);
    showErr('خطا در بررسی وضعیت راه‌اندازی پنل');
  }
})();

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errBox.classList.remove('show');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader-2"></i> در حال پردازش...';
  try{
    const password = document.getElementById('password').value;
    const url = setupMode ? '/api/setup-password' : '/api/login';
    const body = setupMode ? {password, password_confirm: document.getElementById('passwordConfirm').value} : {password};
    const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    if(r.ok){ location.href = '/dashboard'; return; }
    const d = await r.json().catch(() => ({}));
    showErr(d.detail || 'عملیات ناموفق بود');
  }catch(err){ showErr('خطا در ارتباط با سرور'); }
  finally{
    btn.disabled = false;
    btn.innerHTML = setupMode ? '<i class="ti ti-shield-check"></i> ذخیره رمز و ورود' : '<i class="ti ti-bolt"></i> ورود به پنل';
  }
});
</script>

</body>
</html>"""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>· Control Center</title>
""" + FONT_LINKS + r"""
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
""" + BASE_TOKENS + r"""
html,body{background:var(--bg);color:var(--text);font-family:var(--f-body);font-size:14px}
body{overflow-x:hidden}
button{cursor:pointer}

.app{min-height:100vh;display:grid;grid-template-columns:242px minmax(0,1fr)}

/* Sidebar */
.sidebar{position:sticky;top:0;height:100vh;background:var(--bg2);border-left:1px solid var(--line);
  padding:22px 15px;display:flex;flex-direction:column;z-index:50}
.brand{display:flex;align-items:center;gap:11px;padding:0 8px 22px;border-bottom:1px solid var(--line)}
.brand-mark{width:38px;height:38px;border-radius:12px;background:linear-gradient(155deg,var(--surface2),var(--surface));
  border:1px solid var(--line-hi);display:grid;place-items:center;box-shadow:0 8px 20px -6px rgba(52,211,153,.35)}
.brand-mark svg{width:20px;height:20px}
.brand-name{font-weight:800;letter-spacing:.08em;font-size:15px;color:var(--text)}
.brand-caption{display:block;color:var(--text-dim2);font-size:10px;margin-top:2px}
.menu-toggle{display:none;width:36px;height:36px;border:1px solid var(--line);background:var(--surface);
  border-radius:10px;color:var(--text-dim);align-items:center;justify-content:center;font-size:19px;flex:0 0 auto;transition:.15s}
.menu-toggle:hover{color:var(--accent);border-color:var(--line-hi)}
.sidebar-menu{display:flex;flex-direction:column;flex:1;min-height:0}
.nav-label{font-size:10px;color:var(--text-dim2);margin:22px 10px 8px;letter-spacing:.1em;font-family:var(--f-mono)}
.tb-tabs{display:flex;flex-direction:column;gap:3px}
.tb-tab{display:flex;align-items:center;gap:11px;padding:11px 12px;border-radius:10px;color:var(--text-dim);
  transition:.15s;position:relative;font-size:12.5px;cursor:pointer}
.tb-tab i{font-size:17px}
.tb-tab:hover{background:var(--surface2);color:var(--text)}
.tb-tab.active{background:var(--accent-soft);color:var(--accent)}
.tb-tab .chip{margin-right:auto;background:rgba(52,211,153,.14);color:var(--accent);border-radius:999px;padding:2px 7px;font:10px var(--f-mono)}
.sidebar-foot{margin-top:auto;padding-top:18px;border-top:1px solid var(--line)}
.system{display:flex;align-items:center;gap:9px;padding:10px 11px;color:var(--text-dim);font-size:11px}
.system-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px var(--accent-soft)}
.logout{width:100%;border:0;background:var(--surface2);color:var(--text-dim);border-radius:10px;padding:10px;
  display:flex;align-items:center;gap:9px;margin-top:8px;transition:.15s}
.logout:hover{background:var(--danger-soft);color:#ffc4c4}

/* Topbar */
.main{min-width:0}
.topbar{height:72px;background:rgba(10,15,28,.82);backdrop-filter:blur(14px);border-bottom:1px solid var(--line);
  display:flex;align-items:center;padding:0 32px;gap:18px;position:sticky;top:0;z-index:40}
.context{flex:1}.context-title{font-size:15px;font-weight:800}
.context-sub{font-size:10.5px;color:var(--text-dim);margin-top:3px;font-family:var(--f-mono)}
.top-actions{display:flex;align-items:center;gap:8px}
.top-pill{border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:7px 12px;
  color:var(--text-dim);font-size:11px;display:flex;align-items:center;gap:7px}
.top-pill .dot{width:6px;height:6px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.top-icon{width:36px;height:36px;border:1px solid var(--line);background:var(--surface);border-radius:10px;
  color:var(--text-dim);display:grid;place-items:center;transition:.15s}
.top-icon:hover{color:var(--accent);border-color:var(--line-hi)}

/* Stage */
.stage{max-width:1500px;margin:0 auto;padding:30px 32px 60px}
.vx-page{display:none}
.vx-page.active{display:block;animation:enter .2s ease}
@keyframes enter{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
.page-head{display:flex;align-items:end;justify-content:space-between;gap:15px;margin-bottom:24px}
.page-title{font-size:24px;font-weight:800;letter-spacing:-.02em}
.page-sub{font-size:11.5px;color:var(--text-dim);margin-top:5px}

/* Overview */
.overview-intro{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:22px;align-items:stretch;margin-bottom:24px}
.intro-copy{padding:10px 4px}
.eyebrow{font-size:10px;color:var(--accent);font-weight:800;letter-spacing:.14em;margin-bottom:10px;font-family:var(--f-mono)}
.intro-copy h1{font-size:32px;line-height:1.3;letter-spacing:-.03em;max-width:680px;font-weight:800}
.intro-copy p{color:var(--text-dim);font-size:12.5px;line-height:2;margin-top:12px;max-width:600px}
.command-panel{background:linear-gradient(160deg,var(--surface2),var(--surface));border:1px solid var(--line);
  color:var(--text);border-radius:18px;padding:22px;display:flex;flex-direction:column;justify-content:space-between;
  min-height:172px;box-shadow:var(--shadow)}
.command-kicker{font-size:10px;color:var(--text-dim);letter-spacing:.08em;font-family:var(--f-mono)}
.command-value{font:800 30px var(--f-mono);margin:10px 0;color:var(--accent)}
.command-meta{display:flex;justify-content:space-between;color:var(--text-dim);font-size:10px}
.command-meta strong{color:var(--text);font-family:var(--f-mono)}

.signal-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:1px solid var(--line);
  border-radius:16px;background:var(--surface);margin-bottom:24px;overflow:hidden}
.signal{padding:18px 20px;min-width:0;border-right:1px solid var(--line)}
.signal:first-child{border-right:0}
.signal-label{font-size:10px;color:var(--text-dim);margin-bottom:7px}
.signal-value{font-size:22px;font-weight:800;letter-spacing:-.02em;font-family:var(--f-mono)}
.signal-value small{font-size:10px;color:var(--text-dim);font-weight:500;margin-right:3px}
.signal-note{font-size:9.5px;color:var(--text-dim2);margin-top:4px}

.workbench{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:22px}
.section-line{display:flex;justify-content:space-between;align-items:center;margin-bottom:13px}
.section-title{font-size:13.5px;font-weight:800}
.section-meta{font-size:10px;color:var(--text-dim)}

.feed{background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.feed-row{display:grid;grid-template-columns:38px minmax(0,1fr) auto;align-items:center;gap:12px;padding:14px 16px;
  border-bottom:1px solid var(--line-soft)}
.feed-row:last-child{border-bottom:0}
.feed-icon{width:32px;height:32px;border-radius:9px;background:var(--surface3);display:grid;place-items:center;color:var(--accent)}
.feed-main{min-width:0}
.feed-main strong{font-size:12px}
.feed-main span{display:block;color:var(--text-dim);font-size:10px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.feed-value{font:700 11px var(--f-mono);color:var(--text)}

.side-rail{display:flex;flex-direction:column;gap:18px}
.rail-block{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px}
.rail-title{font-size:12px;font-weight:800;margin-bottom:14px}
.mini-stat{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line-soft);font-size:10.5px}
.mini-stat:last-child{border-bottom:0}
.mini-stat span{color:var(--text-dim)}
.mini-stat strong{font-family:var(--f-mono)}

/* Controls */
.btn{border:1px solid var(--line);background:var(--surface);color:var(--text);border-radius:9px;padding:10px 14px;
  display:inline-flex;align-items:center;gap:7px;font-size:11.5px;font-weight:700;transition:.15s}
.btn:hover{border-color:var(--line-hi);transform:translateY(-1px)}
.btn-grad{background:linear-gradient(180deg,#5eead4,var(--accent));border-color:var(--accent);color:var(--accent-ink);
  box-shadow:0 8px 18px -8px rgba(52,211,153,.45)}
.btn-grad:hover{filter:brightness(1.05)}
.btn-outline{background:var(--surface)}
.btn-danger{background:var(--danger-soft);color:#ffb4b4;border-color:rgba(248,113,113,.3)}
.btn-sm{padding:7px 10px;font-size:10px}
.btn:disabled{opacity:.45;cursor:not-allowed;transform:none}

/* Links page */
.link-layout{display:grid;grid-template-columns:330px minmax(0,1fr);gap:22px;align-items:start}
.create-panel{background:linear-gradient(160deg,var(--surface2),var(--surface));border:1px solid var(--line);
  color:var(--text);padding:22px;border-radius:16px;position:sticky;top:96px}
.create-panel h2{font-size:16px;margin-bottom:5px}
.create-panel p{font-size:10.5px;color:var(--text-dim);line-height:1.9;margin-bottom:20px}
.create-panel .field label{color:var(--text-dim)}
.create-panel .field input,.create-panel .field select{background:var(--surface3);border-color:var(--line);color:var(--text)}
.create-grid{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.create-grid .wide{grid-column:1/-1}
.create-submit{width:100%;justify-content:center;margin-top:15px}
.field{display:flex;flex-direction:column;gap:6px}
.field label{font-size:10px;color:var(--text-dim);font-weight:700}
.field input,.field select{width:100%;border:1px solid var(--line);background:var(--surface3);color:var(--text);
  border-radius:8px;padding:10px 11px;outline:0;font-size:11.5px}
.field input:focus,.field select:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}

.list-area{min-width:0}
.list-tools{display:flex;gap:8px;align-items:center;margin-bottom:14px}
.bulk-bar{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;
  background:var(--accent-soft);border:1px solid var(--accent);border-radius:11px;padding:9px 12px;margin-bottom:12px}
.bulk-count{display:flex;align-items:center;gap:6px;font-size:11.5px;font-weight:700;color:var(--accent)}
.bulk-actions{display:flex;gap:6px;flex-wrap:wrap}
.filter-row{display:flex;gap:8px;flex:1}
.filter-row input,.filter-row select{border:1px solid var(--line);background:var(--surface);border-radius:8px;
  padding:10px 11px;font-size:11px;color:var(--text);outline:0}
.filter-row input{flex:1;min-width:130px}
.filter-row input:focus,.filter-row select:focus{border-color:var(--accent)}

.table-shell{background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:auto}
.vx-table{width:100%;border-collapse:collapse;min-width:760px}
.vx-table th{text-align:right;padding:12px 14px;color:var(--text-dim);font-size:9.5px;font-weight:800;
  border-bottom:1px solid var(--line);background:var(--surface2)}
.vx-table td{padding:14px 14px;border-bottom:1px solid var(--line-soft);font-size:11px;vertical-align:middle}
.vx-table tr:last-child td{border-bottom:0}
.vx-table tr:hover td{background:var(--surface2)}
.uid-chip{font:10px var(--f-mono);background:var(--surface3);padding:4px 7px;border-radius:5px;color:var(--text-dim)}
.usage-wrap{min-width:150px}
.usage-bar{height:5px;background:var(--surface3);border-radius:99px;overflow:hidden;margin-bottom:5px}
.usage-fill{height:100%;background:var(--accent);border-radius:99px}
.usage-text{font:9px var(--f-mono);color:var(--text-dim)}
.toggle{width:36px;height:21px;border-radius:99px;background:var(--surface3);border:1px solid var(--line);position:relative}
.toggle:after{content:'';position:absolute;top:2px;right:2px;width:15px;height:15px;border-radius:50%;
  background:var(--text-dim);box-shadow:0 1px 3px rgba(0,0,0,.3);transition:.15s}
.toggle.on{background:var(--accent-soft);border-color:var(--accent)}
.toggle.on:after{right:16px;background:var(--accent)}
.badge{display:inline-flex;align-items:center;gap:4px;font-size:9px;padding:4px 7px;border-radius:5px;white-space:nowrap}
.badge.ok{background:var(--accent-soft);color:var(--accent)}
.badge.warn{background:var(--relay-soft);color:var(--relay)}
.badge.dim{background:var(--surface3);color:var(--text-dim)}

/* Other pages */
.clean-page{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:22px}
.chart-wrap{position:relative;height:280px;width:100%}
.clean-page .chart-wrap{height:330px}
.empty{text-align:center;padding:70px 20px;color:var(--text-dim);font-size:12px}
.empty i{display:block;font-size:30px;color:var(--text-dim2);margin-bottom:10px}
.connection-list,.error-list{background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.conn-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 16px;
  border-bottom:1px solid var(--line-soft);font-size:11px}
.conn-row:last-child{border-bottom:0}
.conn-id{display:flex;align-items:center;gap:8px;font-weight:700}
.conn-id i{color:var(--accent)}
.conn-meta{color:var(--text-dim);font-size:10px;font-family:var(--f-mono)}
.err-row{padding:14px 16px;border-bottom:1px solid var(--line-soft)}
.err-row:last-child{border-bottom:0}
.err-time{font:9px var(--f-mono);color:var(--text-dim2)}
.err-msg{font-size:11px;color:var(--danger);margin-top:4px}

.settings-layout{display:grid;grid-template-columns:210px minmax(0,1fr);gap:22px}
.settings-nav{background:var(--surface);border:1px solid var(--line);padding:10px;border-radius:14px;height:max-content}
.settings-nav button{width:100%;border:0;background:transparent;color:var(--text-dim);padding:11px;
  border-radius:8px;text-align:right;font-size:11px;transition:.15s}
.settings-nav button:first-child{background:var(--accent-soft);color:var(--accent)}
.settings-content{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.setting-section{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:20px}
.setting-section.wide{grid-column:1/-1}
.setting-section h3{font-size:13px;margin-bottom:6px}
.setting-section p{font-size:10.5px;color:var(--text-dim);line-height:1.9;margin-bottom:17px}
.setting-form{display:grid;gap:12px;max-width:420px}

.modal-backdrop{position:fixed;inset:0;background:rgba(6,10,18,.7);backdrop-filter:blur(6px);z-index:100;
  display:none;align-items:center;justify-content:center;padding:20px}
.modal-backdrop.show{display:flex}
.modal-box{width:100%;max-width:440px;background:linear-gradient(160deg,var(--surface2),var(--surface));
  border:1px solid var(--line);border-radius:16px;padding:22px;box-shadow:0 30px 80px rgba(0,0,0,.5)}
.modal-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.modal-title{font-weight:800;font-size:14px;color:var(--text)}
.modal-close{border:0;background:var(--surface3);color:var(--text-dim);width:30px;height:30px;border-radius:8px;font-size:18px}
.modal-actions{display:flex;justify-content:flex-start;gap:8px;margin-top:18px}
.qr-wrap{background:#fff;border:1px solid var(--line);padding:14px;display:flex;justify-content:center;border-radius:10px;margin-bottom:13px}
.toast{position:fixed;left:26px;bottom:24px;background:var(--surface2);border:1px solid var(--line-hi);color:var(--text);
  padding:11px 16px;border-radius:10px;font-size:11px;z-index:200;opacity:0;transform:translateY(10px);transition:.2s}
.toast.show{opacity:1;transform:none}
.toast.err{background:#3a1518;border-color:rgba(248,113,113,.4)}

.update-banner{display:none;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;
  background:linear-gradient(90deg,var(--accent-soft),var(--surface2));border-bottom:1px solid var(--accent);
  padding:10px 16px;font-size:11.5px;color:var(--text);position:sticky;top:0;z-index:60}
.update-banner.show{display:flex}
.update-banner b{color:var(--accent)}
.update-banner .btn{padding:7px 14px;font-size:11px}

@media(max-width:1100px){.app{grid-template-columns:86px minmax(0,1fr)}.sidebar{padding:18px 10px}.brand{justify-content:center;padding-left:0;padding-right:0}.brand-name,.brand-caption,.nav-label,.tb-tab span,.system span,.logout span{display:none}.tb-tab{justify-content:center}.tb-tab .chip{display:none}.overview-intro,.workbench{grid-template-columns:1fr}.link-layout{grid-template-columns:1fr}.create-panel{position:relative;top:auto}.settings-layout{grid-template-columns:1fr}.settings-nav{display:flex;gap:5px;overflow:auto}.settings-nav button{white-space:nowrap;width:auto}.settings-content{grid-template-columns:1fr}}
@media(max-width:720px){.app{display:block}.sidebar{position:fixed;right:0;left:0;top:0;bottom:auto;height:64px;width:100%;padding:7px 14px;flex-direction:row;align-items:center;border-left:0;border-bottom:1px solid var(--line)}.brand{border:0;padding:0;flex:1;justify-content:flex-start}.brand-name,.brand-caption{display:block}.brand-name{font-size:12px}.brand-mark{width:34px;height:34px}.menu-toggle{display:flex}.sidebar-menu{position:fixed;top:64px;right:0;left:0;max-height:calc(100vh - 64px);overflow:auto;background:var(--bg2);border-bottom:1px solid var(--line);box-shadow:0 20px 40px -20px rgba(0,0,0,.5);padding:4px 15px 18px;transform-origin:top;transform:scaleY(0);opacity:0;pointer-events:none;transition:transform .18s ease,opacity .18s ease;z-index:49;display:block}.sidebar-menu.open{transform:scaleY(1);opacity:1;pointer-events:auto}.sidebar-menu .nav-label{display:block}.tb-tabs{flex-direction:column;gap:3px}.tb-tab{justify-content:flex-start;padding:11px 12px}.tb-tab span{display:inline}.tb-tab .chip{display:inline-block}.sidebar-foot{display:block;margin-top:14px;padding-top:14px}.system span,.logout span{display:inline}.main{padding-top:64px}.topbar{height:64px;padding:0 15px}.top-pill{display:none}.stage{padding:22px 15px 40px}.page-title{font-size:21px}.signal-row{grid-template-columns:1fr 1fr}.signal:nth-child(2){border-right:0}.signal:nth-child(n+3){border-top:1px solid var(--line)}.intro-copy h1{font-size:26px}.create-grid{grid-template-columns:1fr}.create-grid .wide{grid-column:auto}.list-tools{display:block}.filter-row{margin-bottom:8px;flex-wrap:wrap}.filter-row input{min-width:100%}.clean-page{padding:15px}.conn-row{flex-wrap:wrap}.settings-content{display:block}.setting-section{margin-bottom:14px}}
</style>
</head>
<body>
<div class="toast" id="toast"></div>
<div class="update-banner" id="updateBanner">
  <i class="ti ti-arrow-big-up-lines"></i>
  <span>یک بروزرسانی جدید (<b id="updateVersionText"></b>) در دسترس است</span>
  <button class="btn btn-grad" id="applyUpdateBtn"><i class="ti ti-download"></i> بروزرسانی</button>
</div>
<div class="app">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark"><svg viewBox="0 0 24 24" fill="none">""" + BRAND_MARK_SVG + SIGNAL_SVG_DEFS + r"""</svg></div>
      <div><div class="brand-name"></div><span class="brand-caption">gateway control</span></div>
      <button class="menu-toggle" id="menuToggle" aria-label="باز کردن منو"><i class="ti ti-menu-2"></i></button>
    </div>
    <div class="sidebar-menu" id="sidebarMenu">
      <div class="nav-label">WORKSPACE</div>
      <nav class="tb-tabs" id="tabs">
        <div class="tb-tab active" data-page="overview"><i class="ti ti-home-2"></i><span>خانه</span></div>
        <div class="tb-tab" data-page="links"><i class="ti ti-route"></i><span>کانفیگ‌ها</span><span class="chip" id="linksBadge">0</span></div>
        <div class="tb-tab" data-page="traffic"><i class="ti ti-wave-sine"></i><span>مصرف</span></div>
        <div class="tb-tab" data-page="connections"><i class="ti ti-activity-heartbeat"></i><span>زنده</span><span class="chip" id="connsBadge">0</span></div>
        <div class="tb-tab" data-page="errors"><i class="ti ti-shield-exclamation"></i><span>گزارش خطا</span></div>
      </nav>
      <div class="nav-label">SYSTEM</div>
      <nav class="tb-tabs">
        <div class="tb-tab" data-page="system"><i class="ti ti-server-2"></i><span>وضعیت سیستم</span></div>
        <div class="tb-tab" data-page="settings"><i class="ti ti-adjustments-horizontal"></i><span>تنظیمات</span></div>
      </nav>
      <div class="sidebar-foot">
        <div class="system"><span class="system-dot"></span><span>Gateway online</span></div>
        <button class="logout" id="logoutBtn"><i class="ti ti-logout-2"></i><span>خروج از پنل</span></button>
      </div>
    </div>
  </aside>

  <div class="main">
    <header class="topbar">
      <div class="context"><div class="context-title">مرکز کنترل </div><div class="context-sub" id="lastUpdate">در حال همگام‌سازی...</div></div>
      <div class="top-actions"><span class="top-pill"><span class="dot"></span> سرویس آنلاین</span><button class="top-icon" id="refreshBtn" title="به‌روزرسانی"><i class="ti ti-refresh"></i></button></div>
    </header>

    <main class="stage">
      <section class="vx-page active" id="page-overview">
        <div class="overview-intro">
          <div class="intro-copy"><div class="eyebrow">/ CONTROL CENTER</div><h1>مدیریت گیت‌وی، در یک نگاه.</h1><p>وضعیت سرویس، کانفیگ‌های فعال، مصرف و رخدادها را همین‌جا و بدون شلوغی ببین.</p></div>
          <div class="command-panel"><div class="command-kicker">SERVER STATE</div><div class="command-value" id="statUptime">--</div><div class="command-meta"><span>Links <strong id="statLinks">0</strong></span><span>Host <strong id="statHost">--</strong></span></div></div>
        </div>
        <div class="signal-row">
          <div class="signal"><div class="signal-label">اتصالات فعال</div><div class="signal-value" id="mConns">0</div><div class="signal-note">Live connections</div></div>
          <div class="signal"><div class="signal-label">مصرف کل</div><div class="signal-value" id="mTraffic">0 <small>MB</small></div><div class="signal-note">Total traffic</div></div>
          <div class="signal"><div class="signal-label">درخواست‌ها</div><div class="signal-value" id="mReqs">0</div><div class="signal-note">Gateway requests</div></div>
          <div class="signal"><div class="signal-label">خطاها</div><div class="signal-value" id="mErrs">0</div><div class="signal-note">Recent errors</div></div>
        </div>
        <div class="workbench">
          <div>
            <div class="section-line"><div class="section-title">آخرین وضعیت کانفیگ‌ها</div><div class="section-meta">بدون نمایش URLهای طولانی</div></div>
            <div class="feed" id="overviewFeed"><div class="feed-row"><div class="feed-icon"><i class="ti ti-loader-2"></i></div><div class="feed-main"><strong>در حال دریافت لینک‌ها...</strong><span>اطلاعات از Gateway خوانده می‌شود</span></div><div class="feed-value">—</div></div></div>
          </div>
          <aside class="side-rail">
            <div class="rail-block"><div class="rail-title">وضعیت سرویس</div><div class="mini-stat"><span>وضعیت</span><strong style="color:var(--ok)">ONLINE</strong></div><div class="mini-stat"><span>لینک‌ها</span><strong id="overviewLinksCount">0</strong></div><div class="mini-stat"><span>اتصالات</span><strong id="overviewConnCount">0</strong></div></div>
            <div class="rail-block"><div class="rail-title">دسترسی سریع</div><button class="btn btn-grad" id="goLinksBtn" style="width:100%;justify-content:center">مدیریت کانفیگ‌ها <i class="ti ti-arrow-left"></i></button></div>
          </aside>
        </div>
        <canvas id="trafficChart" width="1" height="1" style="display:none" aria-hidden="true"></canvas>
      </section>

      <section class="vx-page" id="page-links">
        <div class="page-head"><div><div class="page-title">کانفیگ‌ها</div><div class="page-sub">ایجاد و مدیریت دسترسی‌های VLESS</div></div></div>
        <div class="link-layout">
          <aside class="create-panel"><h2>کانفیگ تازه</h2><p>یک دسترسی جدید بساز. جزئیات را وارد کن و بقیه تنظیمات از سمت Gateway مدیریت می‌شود.</p>
            <div class="create-grid">
              <div class="field wide"><label>عنوان</label><input type="text" id="newLabel" placeholder="مثلاً مشتری اصلی"></div>
              <div class="field"><label>سقف ترافیک</label><input type="number" id="newLimitValue" placeholder="0 = نامحدود" min="0"></div>
              <div class="field"><label>واحد</label><select id="newLimitUnit"><option value="GB">GB</option><option value="MB">MB</option></select></div>
              <div class="field"><label>انقضا</label><input type="number" id="newExpiresAt" placeholder="روز / خالی" min="0"></div>
              <div class="field"><label>سرعت</label><input type="number" id="newSpeedValue" placeholder="0 = نامحدود" min="0"></div>
              <div class="field"><label>واحد سرعت</label><select id="newSpeedUnit"><option value="KBps">KB/s</option><option value="MBps">MB/s</option></select></div>
              <div class="field wide"><label>مسیر اتصال</label><select id="newRouteVia">
                <option value="auto">خودکار (اگر Cloudflare فعال باشد از آن استفاده کن)</option>
                <option value="railway">همیشه مستقیم Railway</option>
                <option value="cloudflare">همیشه از طریق Cloudflare Worker</option>
              </select></div>
            </div>
            <button class="btn btn-grad create-submit" id="createLinkBtn"><i class="ti ti-plus"></i> ایجاد کانفیگ</button>
          </aside>
          <div class="list-area">
            <div class="list-tools"><div class="filter-row"><input type="text" id="linkSearch" placeholder="جستجو در کانفیگ‌ها..."><select id="linkFilterStatus"><option value="all">همه</option><option value="active">فعال</option><option value="inactive">غیرفعال</option><option value="expired">منقضی</option></select><select id="linkSort"><option value="created_desc">جدیدترین</option><option value="created_asc">قدیمی‌ترین</option><option value="usage_desc">بیشترین مصرف</option><option value="label_asc">عنوان</option></select></div></div>
            <div class="bulk-bar" id="bulkBar" style="display:none">
              <span class="bulk-count"><i class="ti ti-checkbox"></i> <span id="bulkCount">0</span> لینک انتخاب شده</span>
              <div class="bulk-actions">
                <button class="btn btn-sm btn-outline" data-bulk="activate"><i class="ti ti-player-play"></i> فعال‌سازی</button>
                <button class="btn btn-sm btn-outline" data-bulk="deactivate"><i class="ti ti-player-pause"></i> غیرفعال‌سازی</button>
                <button class="btn btn-sm btn-outline" data-bulk="reset"><i class="ti ti-refresh"></i> ریست مصرف</button>
                <button class="btn btn-sm btn-outline" data-bulk="extend30"><i class="ti ti-calendar-plus"></i> تمدید ۳۰ روز</button>
                <button class="btn btn-sm btn-danger" data-bulk="delete"><i class="ti ti-trash"></i> حذف</button>
                <button class="btn btn-sm" id="bulkClearBtn"><i class="ti ti-x"></i> لغو انتخاب</button>
              </div>
            </div>
            <div class="table-shell" id="linksTableWrap"></div>
          </div>
        </div>
      </section>

      <section class="vx-page" id="page-traffic"><div class="page-head"><div><div class="page-title">مصرف</div><div class="page-sub">نمایش روند مصرف Gateway در طول زمان</div></div></div><div class="clean-page"><div class="section-line"><div class="section-title">روند ترافیک</div><div class="section-meta">داده ساعتی</div></div><div class="chart-wrap"><canvas id="trafficChartBig"></canvas></div></div></section>
      <section class="vx-page" id="page-connections"><div class="page-head"><div><div class="page-title">اتصالات زنده</div><div class="page-sub">اتصال‌های فعال در همین لحظه</div></div></div><div class="connection-list" id="connsWrap"><div class="empty"><i class="ti ti-activity-heartbeat"></i>اتصال فعالی وجود ندارد</div></div></section>
      <section class="vx-page" id="page-errors"><div class="page-head"><div><div class="page-title">گزارش خطا</div><div class="page-sub">آخرین رخدادهای ثبت‌شده</div></div></div><div class="error-list" id="errorsWrap"><div class="empty"><i class="ti ti-circle-check"></i>خطایی ثبت نشده</div></div></section>

      <section class="vx-page" id="page-system">
        <div class="page-head"><div><div class="page-title">وضعیت سیستم</div><div class="page-sub">یک نگاه سریع به سلامت و آماده‌بودن Railway</div></div><button class="btn btn-grad" id="systemRefreshBtn"><i class="ti ti-refresh"></i> بررسی دوباره</button></div>
        <div class="signal-row" id="systemSignals">
          <div class="signal"><div class="signal-label">Database</div><div class="signal-value" id="sysDb">—</div><div class="signal-note" id="sysDbNote">در حال بررسی</div></div>
          <div class="signal"><div class="signal-label">Storage</div><div class="signal-value" id="sysStorage">—</div><div class="signal-note" id="sysStorageNote">در حال بررسی</div></div>
          <div class="signal"><div class="signal-label">Backup</div><div class="signal-value" id="sysBackup">—</div><div class="signal-note" id="sysBackupNote">در حال بررسی</div></div>
          <div class="signal"><div class="signal-label">Redis</div><div class="signal-value" id="sysRedis">—</div><div class="signal-note" id="sysRedisNote">اختیاری</div></div>
        </div>
        <div class="workbench">
          <div class="clean-page">
            <div class="section-line"><div class="section-title">جزئیات استقرار</div><div class="section-meta" id="sysVersion">—</div></div>
            <div class="mini-stat"><span>محیط</span><strong id="sysPlatform">—</strong></div>
            <div class="mini-stat"><span>مسیر دیتابیس</span><strong id="sysDbPath" style="font-family:var(--f-mono);font-size:9px;direction:ltr">—</strong></div>
            <div class="mini-stat"><span>فضای آزاد</span><strong id="sysDisk">—</strong></div>
            <div class="mini-stat"><span>اتصالات فعال</span><strong id="sysConnections">—</strong></div>
          </div>
          <aside class="side-rail">
            <div class="rail-block"><div class="rail-title">Storage</div><p style="font-size:10px;line-height:1.9;color:var(--text-dim);margin-bottom:10px">قبل از استفاده جدی، مطمئن شو دیتابیس روی Volume پایدار قرار دارد.</p><button class="btn btn-grad" id="storageTestBtn" style="width:100%;justify-content:center"><i class="ti ti-device-floppy"></i> تست نوشتن</button></div>
            <div class="rail-block"><div class="rail-title">راهنمای Railway</div><p style="font-size:10px;line-height:1.9;color:var(--text-dim)">اگر Storage قرمز بود، یک Volume با مسیر <code>/data</code> متصل کن. بقیه تنظیمات توسط مدیریت می‌شود.</p></div>
          </aside>
        </div>
      </section>

      <section class="vx-page" id="page-settings">
        <div class="page-head"><div><div class="page-title">تنظیمات</div><div class="page-sub">امنیت، داده و اعلان‌ها</div></div></div>
        <div class="settings-layout">
          <nav class="settings-nav"><button>امنیت</button><button>داده‌ها</button><button>اعلان‌ها</button></nav>
          <div class="settings-content">
            <section class="setting-section"><h3>امنیت پنل</h3><p>رمز عبور مدیریت را بدون تغییر سایر تنظیمات سرویس به‌روزرسانی کن.</p><div class="setting-form"><div class="field"><label>رمز فعلی</label><input type="password" id="curPass"></div><div class="field"><label>رمز جدید</label><input type="password" id="newPass"></div><button class="btn btn-grad" id="changePasswordBtn"><i class="ti ti-lock-check"></i> ذخیره رمز</button></div></section>
            <section class="setting-section wide"><h3>Cloudflare Worker Relay</h3>
              <p>Worker فقط <strong>Relay</strong> است: <span dir="ltr">Client → Cloudflare Worker → Gateway</span>. منطق VLESS و احراز هویت روی Gateway می‌ماند؛ Worker صرفاً درخواست را به Origin عبور می‌دهد.</p>
              <div id="cfStatusBox" style="margin:12px 0;padding:13px;border:1px solid var(--line);border-radius:12px;background:var(--bg2)">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px"><strong>وضعیت Worker</strong><span id="cfStatusBadge" class="badge dim">بررسی نشده</span></div>
                <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 14px;font-size:10px;line-height:1.9">
                  <div>Worker: <b id="cfStatusName">—</b></div><div>Latency: <b id="cfStatusLatency">—</b></div>
                  <div>آخرین Deploy: <b id="cfStatusDeployedAt">—</b></div><div>آخرین Check: <b id="cfStatusCheckedAt">—</b></div>
                  <div style="grid-column:1/-1;direction:ltr;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">URL: <b id="cfStatusUrl">—</b></div>
                  <div style="grid-column:1/-1;color:var(--text-dim)" id="cfStatusError"></div>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px"><button class="btn" id="cfRefreshStatusBtn" type="button"><i class="ti ti-refresh"></i> بررسی وضعیت</button><button class="btn" id="cfDisableBtn" type="button" style="border-color:rgba(255,180,0,.35);color:#ffd166"><i class="ti ti-player-pause"></i> غیرفعال‌سازی</button><button class="btn" id="cfDeleteBtn" type="button" style="border-color:rgba(255,80,80,.35);color:#ff8f8f"><i class="ti ti-trash"></i> حذف کامل Worker</button></div>
              </div>

              <div class="setting-form">
                <div class="field"><label>API Token کلادفلر</label><div style="display:flex;gap:8px"><input type="password" id="cfApiToken" autocomplete="off" placeholder="برای Deploy / تغییر دامنه / حذف لازم است" style="flex:1"><button class="btn" id="cfPasteTokenBtn" type="button" title="چسباندن از کلیپ‌بورد"><i class="ti ti-clipboard"></i></button></div></div>
                <button class="btn" id="cfOpenTokenBtn" type="button" style="width:100%;justify-content:center"><i class="ti ti-external-link"></i> ساخت Token با دسترسی پیشنهادی</button>
                <div class="field"><label>نوع آدرس Worker</label><select id="cfDomainMode" style="width:100%"><option value="workers_dev">workers.dev (ساده و فوری)</option><option value="custom">دامنه / زیردامنه اختصاصی</option></select></div>
                <div class="field" id="cfHostnameWrap" style="display:none"><label>دامنه یا زیردامنه</label><div style="display:flex;gap:8px"><input id="cfHostname" autocomplete="off" placeholder="relay.example.com" style="flex:1"><button class="btn" id="cfLoadDomainsBtn" type="button" title="نمایش دامنه‌های قبلاً متصل‌شده"><i class="ti ti-list"></i></button></div><small style="color:var(--text-dim)">دامنه باید داخل Cloudflare باشد؛ Custom Domain خودش DNS و گواهی لازم را مدیریت می‌کند.</small></div>
                <button class="btn btn-grad" id="cfDeployBtn" type="button"><i class="ti ti-cloud-bolt"></i> Deploy / بروزرسانی Worker</button>
              </div>
              <div id="cfDomainList" style="display:none;margin-top:10px;padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--bg2)"></div>
              <div id="cfWorkerInfo" style="display:none;margin-top:12px;padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--bg2);font-size:11px;line-height:2"></div>
            </section>
            <section class="setting-section"><h3>بکاپ و بازیابی</h3><p>از تنظیمات و لینک‌ها نسخه پشتیبان بگیر یا یک فایل قبلی را برگردان.</p><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-grad" id="downloadBackupBtn"><i class="ti ti-download"></i> دریافت بکاپ</button><button class="btn" id="restoreFileBtn"><i class="ti ti-upload"></i> بازیابی</button><input type="file" id="restoreFile" accept=".,application/octet-stream" style="display:none"></div></section>
            <section class="setting-section"><h3>بروزرسانی نرم‌افزار</h3><p>نسخه فعلی: <b id="settingsCurrentVersion" style="font-family:var(--f-mono)">—</b><br>پنل به‌صورت خودکار Commit جدید مخزن گیت‌هاب پروژه را چک می‌کند. وقتی چیزی جدید پیدا شود، همینجا و در بالای صفحه اطلاع داده می‌شود و فقط کافیست دکمه‌ی «بروزرسانی» را بزنی.</p><div id="updateStatusBox" style="font-size:10.5px;color:var(--text-dim);margin-bottom:12px">در حال بررسی...</div><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-grad" id="settingsApplyUpdateBtn" style="display:none"><i class="ti ti-download"></i> بروزرسانی</button></div></section>
            <section class="setting-section wide"><h3>اعلان تلگرام</h3><p>وضعیت اتصال و ارسال پیام تست را از این بخش کنترل کن.</p><div class="mini-stat" style="max-width:520px"><span>وضعیت اتصال</span><strong id="telegramStatus">—</strong></div><button class="btn" id="sendTestNotifBtn" style="margin-top:12px"><i class="ti ti-send"></i> ارسال پیام تست</button></section>
            <section class="setting-section wide"><h3>مسدودسازی تبلیغات</h3><p>وقتی فعال باشد، مقصدهای شناخته‌شده‌ی تبلیغاتی/ردیاب (مثل شبکه‌های تبلیغاتی و آنالیتیکس پراستفاده) پیش از اتصال، مستقیم توسط گیت‌وی بسته می‌شوند — روی همه‌ی کانفیگ‌های VLESS به‌صورت یکجا اثر می‌گذارد.</p>
              <div class="mini-stat" style="max-width:520px;margin-bottom:12px"><span>وضعیت</span><button class="toggle" id="adsBlockToggle" title="فعال / غیرفعال"></button></div>
              <div class="mini-stat" style="max-width:520px"><span>لیست پایه</span><strong id="adsBlockBuiltinCount">—</strong></div>
              <div class="mini-stat" style="max-width:520px"><span>مسدودشده تاکنون</span><strong id="adsBlockCount">0</strong></div>
              <div class="field wide" style="margin-top:12px"><label>دامنه‌های سفارشی (هر خط یک دامنه)</label><textarea id="adsBlockCustomDomains" rows="4" placeholder="example-ads.com&#10;tracker.example.net" style="width:100%;background:var(--bg2);border:1px solid var(--line);border-radius:8px;color:var(--text);font:11px var(--f-mono);padding:10px;resize:vertical"></textarea></div>
              <button class="btn btn-grad" id="adsBlockSaveDomainsBtn" style="margin-top:10px"><i class="ti ti-device-floppy"></i> ذخیره دامنه‌های سفارشی</button>
            </section>
          </div>
        </div>
      </section>
    </main>
  </div>
</div>

<div class="modal-backdrop" id="setupModal"><div class="modal-box" style="max-width:620px">
  <div class="modal-head"><div class="modal-title"><i class="ti ti-rocket"></i> راه‌اندازی اولیه </div></div>
  <div style="padding:6px 0 16px;line-height:2">
    <h2 style="font-size:20px;margin-bottom:8px">خوش اومدی 👋</h2>
    <p style="color:var(--text-dim);font-size:11px">پنل آماده‌ست. چند نکته مهم درباره استقرار Railway رو بررسی کنیم؛ نیازی به کدنویسی نیست.</p>
    <div id="setupStorage" style="margin-top:18px;display:grid;gap:10px"></div>
    <div style="margin-top:16px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--bg2);font-size:10.5px;color:var(--text-dim)">
      <strong style="color:var(--text)">راه‌اندازی اولیه:</strong> در اولین اجرای پنل، رمز مدیریت را خودت تعیین می‌کنی. رمز خام هرگز در دیتابیس ذخیره یا در لاگ چاپ نمی‌شود؛ فقط Hash امن آن نگهداری می‌شود.
    </div>
  </div>
  <div class="modal-actions"><button class="btn btn-grad" id="setupDoneBtn"><i class="ti ti-check"></i> متوجه شدم، ادامه بده</button></div>
</div></div>

<div class="modal-backdrop" id="qrModal"><div class="modal-box"><div class="modal-head"><div class="modal-title"><i class="ti ti-qrcode"></i> QR کانفیگ</div><button class="modal-close" id="qrModalCloseBtn">×</button></div><div class="qr-wrap" id="qrCanvas"></div><div style="font:9.5px var(--f-mono);color:var(--text-dim);word-break:break-all;line-height:1.7" id="qrLinkText"></div></div></div>
<div class="modal-backdrop" id="editModal"><div class="modal-box"><div class="modal-head"><div class="modal-title">ویرایش کانفیگ</div><button class="modal-close" id="editModalCloseBtn">×</button></div><input type="hidden" id="editUid"><div class="field" style="margin-bottom:12px"><label>عنوان</label><input type="text" id="editLabel"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><div class="field"><label>سقف ترافیک</label><input type="number" id="editLimitValue" min="0"></div><div class="field"><label>واحد</label><select id="editLimitUnit"><option value="GB">GB</option><option value="MB">MB</option></select></div><div class="field"><label>انقضا</label><input type="number" id="editExpiresAt" min="0"></div><div class="field"><label>سرعت</label><input type="number" id="editSpeedValue" min="0"></div><div class="field"><label>واحد سرعت</label><select id="editSpeedUnit"><option value="KBps">KB/s</option><option value="MBps">MB/s</option></select></div><div class="field" style="grid-column:1/-1"><label>مسیر اتصال</label><select id="editRouteVia">
  <option value="auto">خودکار (اگر Cloudflare فعال باشد از آن استفاده کن)</option>
  <option value="railway">همیشه مستقیم Railway</option>
  <option value="cloudflare">همیشه از طریق Cloudflare Worker</option>
</select></div></div><div class="modal-actions"><button class="btn" id="editModalCancelBtn">انصراف</button><button class="btn btn-grad" id="saveEditLinkBtn">ذخیره</button></div></div></div>
<div class="modal-backdrop" id="chartModal"><div class="modal-box" style="max-width:560px"><div class="modal-head"><div class="modal-title"><i class="ti ti-chart-line"></i> <span id="chartModalTitle">نمودار مصرف</span></div><button class="modal-close" id="chartModalCloseBtn">×</button></div><div class="chart-wrap" style="height:250px"><canvas id="linkTrafficChart"></canvas></div></div></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>
const toastEl = document.getElementById('toast');
function toast(msg, isErr){toastEl.textContent=msg;toastEl.className='toast show'+(isErr?' err':'');setTimeout(()=>toastEl.classList.remove('show'),2600);}

function getCsrfToken(){
  const m = document.cookie.match(/(?:^|; )_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}
async function apiFetch(url, options={}){
  const method = (options.method || 'GET').toUpperCase();
  if(method !== 'GET' && method !== 'HEAD'){
    options.headers = Object.assign({}, options.headers, {'X-CSRF-Token': getCsrfToken()});
  }
  return fetch(url, options);
}

function daysToExpiryDateStr(days){
  const n = parseInt(days, 10);
  if(!n || n <= 0) return null;
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}
function expiryDateStrToDays(isoString){
  if(!isoString) return '';
  const target = new Date(isoString);
  if(isNaN(target)) return '';
  const diffMs = target.setHours(0,0,0,0) - new Date().setHours(0,0,0,0);
  const days = Math.ceil(diffMs / 86400000);
  return days > 0 ? days : '';
}

function goPage(name){
  document.querySelectorAll('.tb-tab').forEach(i=>i.classList.toggle('active', i.dataset.page===name));
  document.querySelectorAll('.vx-page').forEach(p=>p.classList.toggle('active', p.id==='page-'+name));
  closeMobileMenu();
}
document.querySelectorAll('.tb-tab').forEach(tab=>tab.addEventListener('click', ()=>goPage(tab.dataset.page)));

const menuToggleBtn = document.getElementById('menuToggle');
const sidebarMenuEl = document.getElementById('sidebarMenu');
function closeMobileMenu(){ sidebarMenuEl.classList.remove('open'); }
function toggleMobileMenu(){ sidebarMenuEl.classList.toggle('open'); }
menuToggleBtn.addEventListener('click', (e)=>{ e.stopPropagation(); toggleMobileMenu(); });
document.addEventListener('click', (e)=>{
  if(!sidebarMenuEl.classList.contains('open')) return;
  if(sidebarMenuEl.contains(e.target) || menuToggleBtn.contains(e.target)) return;
  closeMobileMenu();
});

document.getElementById('logoutBtn').addEventListener('click', async ()=>{await apiFetch('/api/logout',{method:'POST'});location.href='/login';});

document.getElementById('refreshBtn').addEventListener('click', refreshAll);
// Optional legacy button removed from the new UI; no binding needed.
document.getElementById('goLinksBtn').addEventListener('click', ()=>goPage('links'));
document.getElementById('createLinkBtn').addEventListener('click', createLink);
document.getElementById('linkSearch').addEventListener('input', renderLinksTable);
document.getElementById('linkFilterStatus').addEventListener('change', renderLinksTable);
document.getElementById('linkSort').addEventListener('change', renderLinksTable);
document.getElementById('changePasswordBtn').addEventListener('click', changePassword);
document.getElementById('downloadBackupBtn').addEventListener('click', downloadBackup);
document.getElementById('restoreFileBtn').addEventListener('click', ()=>document.getElementById('restoreFile').click());
document.getElementById('restoreFile').addEventListener('change', restoreBackup);
document.getElementById('sendTestNotifBtn').addEventListener('click', sendTestNotification);

for(const id of ['qrModal','editModal','chartModal']){
  document.getElementById(id).addEventListener('click', (e)=>{ if(e.target.id===id) closeModal(id); });
}
document.getElementById('qrModalCloseBtn').addEventListener('click', ()=>closeModal('qrModal'));
document.getElementById('editModalCloseBtn').addEventListener('click', ()=>closeModal('editModal'));
document.getElementById('editModalCancelBtn').addEventListener('click', ()=>closeModal('editModal'));
document.getElementById('saveEditLinkBtn').addEventListener('click', saveEditLink);
document.getElementById('chartModalCloseBtn').addEventListener('click', ()=>closeModal('chartModal'));

document.getElementById('linksTableWrap').addEventListener('click', (e)=>{
  const el = e.target.closest('[data-action]');
  if(!el) return;
  const uid = el.dataset.uuid;
  switch(el.dataset.action){
    case 'toggle': toggleLink(uid, el.dataset.next === 'true'); break;
    case 'copy': copyLink(uid); break;
    case 'copysub': copySubLink(uid); break;
    case 'qr': showQr(uid); break;
    case 'chart': showLinkChart(uid); break;
    case 'edit': openEditModal(uid); break;
    case 'reset': resetLink(uid); break;
    case 'extend30': extendLink30(uid); break;
    case 'delete': deleteLink(uid); break;
  }
});

document.querySelectorAll('.tilt').forEach(el=>{
  el.addEventListener('mousemove', e=>{
    const r=el.getBoundingClientRect();
    const x=(e.clientX-r.left)/r.width-0.5, y=(e.clientY-r.top)/r.height-0.5;
    el.style.transform=`perspective(700px) rotateY(${x*7}deg) rotateX(${-y*7}deg) translateZ(2px)`;
  });
  el.addEventListener('mouseleave', ()=>{el.style.transform='perspective(700px) rotateY(0) rotateX(0)';});
});

let trafficChart, trafficChartBig;
function buildChart(ctx, hourly){
  if(!ctx) return null;
  const labels=Object.keys(hourly).sort();
  const data=labels.map(l=>+(hourly[l]/1024/1024).toFixed(2));
  return new Chart(ctx,{type:'line',data:{labels,datasets:[{label:'MB',data,borderColor:'#34d399',
    backgroundColor:'rgba(52,211,153,.14)',fill:true,tension:.35,pointRadius:2,pointBackgroundColor:'#34d399'}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},
      scales:{x:{ticks:{color:'#8b99af',font:{size:10}},grid:{color:'rgba(234,240,247,.08)'}},
               y:{ticks:{color:'#8b99af',font:{size:10}},grid:{color:'rgba(234,240,247,.08)'}}}}});
}

async function refreshAll(){
  try{
    const s = await (await fetch('/api/stats')).json();
    document.getElementById('mConns').textContent=s.active_connections;
    document.getElementById('mTraffic').textContent=s.total_traffic_mb+' MB';
    document.getElementById('mReqs').textContent=s.total_requests;
    document.getElementById('mErrs').textContent=s.total_errors;
    document.getElementById('statUptime').textContent=s.uptime;
    document.getElementById('statLinks').textContent=s.links_count;
    document.getElementById('statHost').textContent=location.host;
    document.getElementById('linksBadge').textContent=s.links_count;
    document.getElementById('connsBadge').textContent=s.active_connections;
    document.getElementById('lastUpdate').textContent='آخرین به‌روزرسانی: '+new Date().toLocaleTimeString('fa-IR');
    const tgEl = document.getElementById('telegramStatus');
    if(tgEl) tgEl.textContent = s.telegram_configured ? 'فعال ✅' : 'تنظیم نشده';

    if(trafficChart) trafficChart.destroy();
    trafficChart = buildChart(document.getElementById('trafficChart'), s.hourly);
    if(trafficChartBig) trafficChartBig.destroy();
    trafficChartBig = buildChart(document.getElementById('trafficChartBig'), s.hourly);

    const errWrap=document.getElementById('errorsWrap');
    if(s.recent_errors.length===0){errWrap.innerHTML='<div class="empty"><i class="ti ti-mood-smile"></i>خطایی ثبت نشده</div>';}
    else{errWrap.innerHTML=s.recent_errors.slice().reverse().map(e=>
      `<div class="err-row"><div class="err-time">${new Date(e.time).toLocaleString('fa-IR')}</div><div class="err-msg">${escapeHtml(e.error)}</div></div>`).join('');}
  }catch(e){}
  await loadLinks();
  await loadConnections();
}

async function loadConnections(){
  const wrap = document.getElementById('connsWrap');
  try{
    const r = await fetch('/api/connections');
    if(!r.ok) return;
    const {connections} = await r.json();
    if(connections.length===0){
      wrap.innerHTML='<div class="empty"><i class="ti ti-plug-off"></i>اتصال فعالی وجود ندارد</div>';
      return;
    }
    wrap.innerHTML = connections.map(c=>{
      const mb = (c.bytes/1024/1024).toFixed(2);
      const since = new Date(c.connected_at).toLocaleTimeString('fa-IR');
      return `<div class="conn-row">
        <div><div class="conn-id"><i class="ti ti-plug-connected"></i> ${escapeHtml(c.label)}</div>
        <div class="conn-meta">شناسه اتصال: ${c.conn_id}</div></div>
        <div class="conn-meta">${mb} MB · از ${since}</div>
      </div>`;
    }).join('');
  }catch(e){}
}

async function sendTestNotification(){
  const r = await apiFetch('/api/notify/test', {method:'POST'});
  const d = await r.json().catch(()=>({}));
  if(r.ok) toast('پیام تست به تلگرام ارسال شد');
  else toast(d.detail||'ارسال پیام تست ناموفق بود', true);
}

function escapeHtml(str){
  const d=document.createElement('div'); d.textContent=String(str); return d.innerHTML;
}

function fmtSpeed(bps){
  if(!bps) return null;
  return bps>=1024*1024 ? (bps/1024/1024).toFixed(1)+' MB/s' : (bps/1024).toFixed(0)+' KB/s';
}
function fmtDate(iso){
  try{ return new Date(iso).toLocaleDateString('fa-IR'); }catch(e){ return iso; }
}

async function loadLinks(){
  const r = await fetch('/api/links');
  if(!r.ok) return;
  const {links} = await r.json();
  const def = links.find(l=>l.label==='لینک پیش‌فرض') || links[links.length-1];
  if(def){window._defaultLink=def.vless_link;}
  window._links = links;
  const feed=document.getElementById('overviewFeed');
  const count=document.getElementById('overviewLinksCount');
  if(count) count.textContent=links.length;
  if(feed){
    if(!links.length){feed.innerHTML='<div class=\"empty\"><i class=\"ti ti-route-off\"></i>هنوز کانفیگی ساخته نشده</div>';}
    else{feed.innerHTML=links.slice(0,6).map(l=>{
      const used=(l.used_bytes/1024/1024).toFixed(1);
      const state=l.expired?'منقضی':(l.active?'فعال':'متوقف');
      return `<div class=\"feed-row\"><div class=\"feed-icon\"><i class=\"ti ti-route\"></i></div><div class=\"feed-main\"><strong>${escapeHtml(l.label)}</strong><span>${escapeHtml(state)} · ${used} MB مصرف</span></div><div class=\"feed-value\">${l.active&&!l.expired?'ON':'OFF'}</div></div>`;
    }).join('');}
  }
  renderLinksTable();
}

function renderLinksTable(){
  const links = window._links || [];
  const wrap = document.getElementById('linksTableWrap');
  if(links.length===0){wrap.innerHTML='<div class="empty"><i class="ti ti-link-off"></i>هنوز لینکی ساخته نشده</div>';return;}

  const q = (document.getElementById('linkSearch').value||'').trim().toLowerCase();
  const status = document.getElementById('linkFilterStatus').value;
  const sortBy = document.getElementById('linkSort').value;

  let filtered = links.filter(l=>{
    if(q && !l.label.toLowerCase().includes(q)) return false;
    if(status==='active' && !(l.active && !l.expired)) return false;
    if(status==='inactive' && l.active) return false;
    if(status==='expired' && !l.expired) return false;
    return true;
  });

  filtered.sort((a,b)=>{
    if(sortBy==='created_asc') return a.created_at.localeCompare(b.created_at);
    if(sortBy==='usage_desc') return b.used_bytes-a.used_bytes;
    if(sortBy==='label_asc') return a.label.localeCompare(b.label,'fa');
    return b.created_at.localeCompare(a.created_at);
  });

  if(filtered.length===0){wrap.innerHTML='<div class="empty"><i class="ti ti-search-off"></i>لینکی با این فیلتر پیدا نشد</div>';return;}

  let rows = filtered.map(l=>{
    const pct = l.limit_bytes>0 ? Math.min(100, (l.used_bytes/l.limit_bytes*100)) : 0;
    const used = (l.used_bytes/1024/1024).toFixed(1);
    const limit = l.limit_bytes>0 ? (l.limit_bytes/1024/1024/1024).toFixed(2)+' GB' : 'نامحدود';
    const speed = fmtSpeed(l.speed_limit_bps);
    let expiryBadge = '<span class="badge dim">بدون انقضا</span>';
    if(l.expires_at){
      expiryBadge = l.expired
        ? '<span class="badge warn"><i class="ti ti-clock-off"></i> منقضی</span>'
        : `<span class="badge ok"><i class="ti ti-calendar-due"></i> تا ${fmtDate(l.expires_at)}</span>`;
    }
    const checked = selectedLinkUids.has(l.uuid) ? 'checked' : '';
    return `<tr>
      <td><input type="checkbox" class="row-check" data-uuid="${l.uuid}" ${checked}></td>
      <td>${escapeHtml(l.label)}</td>
      <td><span class="uid-chip">${l.uuid.slice(0,8)}...</span></td>
      <td><div class="usage-wrap"><div class="usage-bar"><div class="usage-fill" style="width:${pct}%"></div></div>
          <div class="usage-text">${used} MB / ${limit}</div></div></td>
      <td>${expiryBadge}${speed?`<br><span class="badge dim" style="margin-top:4px"><i class="ti ti-gauge"></i> ${speed}</span>`:''}<br>${routeBadge(l.route_via)}</td>
      <td><button class="toggle ${l.active && !l.expired?'on':''}" ${l.expired?'disabled title="لینک منقضی شده"':''} data-action="toggle" data-uuid="${l.uuid}" data-next="${!l.active}"></button></td>
      <td style="display:flex;gap:6px;flex-wrap:wrap">
        <button class="btn btn-sm btn-grad" data-action="copysub" data-uuid="${l.uuid}" title="کپی لینک ساب (Subscription) — همین را به کاربر بده"><i class="ti ti-share"></i></button>
        <button class="btn btn-sm btn-outline" data-action="copy" data-uuid="${l.uuid}" title="کپی لینک مستقیم VLESS"><i class="ti ti-copy"></i></button>
        <button class="btn btn-sm btn-outline" data-action="qr" data-uuid="${l.uuid}" title="نمایش QR"><i class="ti ti-qrcode"></i></button>
        <button class="btn btn-sm btn-outline" data-action="chart" data-uuid="${l.uuid}" title="نمودار مصرف"><i class="ti ti-chart-line"></i></button>
        <button class="btn btn-sm btn-outline" data-action="edit" data-uuid="${l.uuid}" title="ویرایش"><i class="ti ti-edit"></i></button>
        <button class="btn btn-sm btn-outline" data-action="reset" data-uuid="${l.uuid}" title="بازنشانی مصرف"><i class="ti ti-refresh"></i></button>
        <button class="btn btn-sm btn-outline" data-action="extend30" data-uuid="${l.uuid}" title="تمدید ۳۰ روزه انقضا"><i class="ti ti-calendar-plus"></i></button>
        <button class="btn btn-sm btn-danger" data-action="delete" data-uuid="${l.uuid}" title="حذف"><i class="ti ti-trash"></i></button>
      </td>
    </tr>`;
  }).join('');
  wrap.innerHTML = `<table class="vx-table"><thead><tr><th><input type="checkbox" id="selectAllLinks"></th><th>عنوان</th><th>شناسه</th><th>مصرف</th><th>انقضا / سرعت</th><th>فعال</th><th>عملیات</th></tr></thead><tbody>${rows}</tbody></table>`;
  const selectAllEl = document.getElementById('selectAllLinks');
  const visibleUids = filtered.map(l=>l.uuid);
  selectAllEl.checked = visibleUids.length>0 && visibleUids.every(u=>selectedLinkUids.has(u));
  selectAllEl.addEventListener('change', ()=>{
    if(selectAllEl.checked) visibleUids.forEach(u=>selectedLinkUids.add(u));
    else visibleUids.forEach(u=>selectedLinkUids.delete(u));
    updateBulkBar();
    renderLinksTable();
  });
  wrap.querySelectorAll('.row-check').forEach(cb=>{
    cb.addEventListener('change', ()=>{
      const uid = cb.dataset.uuid;
      if(cb.checked) selectedLinkUids.add(uid); else selectedLinkUids.delete(uid);
      updateBulkBar();
    });
  });
}

// ───── انتخاب چندتایی و عملیات دسته‌ای روی جدول لینک‌ها ─────
const selectedLinkUids = new Set();
function updateBulkBar(){
  const bar = document.getElementById('bulkBar');
  const count = selectedLinkUids.size;
  document.getElementById('bulkCount').textContent = count;
  bar.style.display = count>0 ? 'flex' : 'none';
}
document.getElementById('bulkClearBtn').addEventListener('click', ()=>{
  selectedLinkUids.clear();
  updateBulkBar();
  renderLinksTable();
});
const BULK_CONFIRM = {
  delete: 'همه‌ی لینک‌های انتخاب‌شده برای همیشه حذف شوند؟',
  deactivate: 'همه‌ی لینک‌های انتخاب‌شده غیرفعال شوند؟',
};
const BULK_SUCCESS_MSG = {
  delete: 'حذف شد', reset: 'مصرف بازنشانی شد', activate: 'فعال شد',
  deactivate: 'غیرفعال شد', extend30: 'انقضا ۳۰ روز تمدید شد',
};
document.getElementById('bulkBar').addEventListener('click', async (e)=>{
  const btn = e.target.closest('[data-bulk]');
  if(!btn) return;
  const action = btn.dataset.bulk;
  const uids = Array.from(selectedLinkUids);
  if(uids.length===0) return;
  const confirmMsg = BULK_CONFIRM[action];
  if(confirmMsg && !confirm(`${confirmMsg} (${uids.length} لینک)`)) return;
  btn.disabled = true;
  try{
    const r = await apiFetch('/api/links/bulk', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({uids, action})});
    const d = await r.json().catch(()=>({}));
    if(r.ok){
      toast(`${d.affected} لینک: ${BULK_SUCCESS_MSG[action]||'انجام شد'}`);
      selectedLinkUids.clear();
      await loadLinks();
    } else toast(d.detail||'خطا در انجام عملیات گروهی', true);
  } catch(e){ toast('خطا در ارتباط با سرور', true); }
  finally{ btn.disabled = false; }
});
async function extendLink30(uid){
  const r = await apiFetch('/api/links/bulk', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({uids:[uid], action:'extend30'})});
  if(r.ok){ toast('انقضا ۳۰ روز تمدید شد'); loadLinks(); }
  else toast('خطا در تمدید انقضا', true);
}

function routeBadge(routeVia){
  const v = routeVia || 'auto';
  if(v==='railway') return '<span class="badge dim" title="این کانفیگ همیشه مستقیم به Railway وصل می‌شود"><i class="ti ti-train"></i> Railway مستقیم</span>';
  if(v==='cloudflare') return '<span class="badge ok" title="این کانفیگ همیشه از Cloudflare Worker رد می‌شود"><i class="ti ti-brand-cloudflare"></i> Cloudflare</span>';
  return '<span class="badge dim" title="اگر Cloudflare Worker فعال باشد از آن استفاده می‌شود، وگرنه مستقیم Railway"><i class="ti ti-route-2"></i> خودکار</span>';
}

async function createLink(){
  const label=document.getElementById('newLabel').value||'لینک جدید';
  const limit_value=document.getElementById('newLimitValue').value||0;
  const limit_unit=document.getElementById('newLimitUnit').value;
  const expires_at=daysToExpiryDateStr(document.getElementById('newExpiresAt').value);
  const speed_limit_value=document.getElementById('newSpeedValue').value||0;
  const speed_limit_unit=document.getElementById('newSpeedUnit').value;
  const route_via=document.getElementById('newRouteVia').value;
  const r=await apiFetch('/api/links',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({label,limit_value,limit_unit,expires_at,speed_limit_value,speed_limit_unit,route_via})});
  if(r.ok){
    toast('لینک جدید ساخته شد');
    document.getElementById('newLabel').value='';
    document.getElementById('newLimitValue').value='';
    document.getElementById('newExpiresAt').value='';
    document.getElementById('newSpeedValue').value='';
    document.getElementById('newRouteVia').value='auto';
    loadLinks();
  } else toast('خطا در ساخت لینک', true);
}
async function toggleLink(uid, active){await apiFetch('/api/links/'+uid,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({active})});loadLinks();}
async function resetLink(uid){await apiFetch('/api/links/'+uid,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({reset_usage:true})});toast('مصرف بازنشانی شد');loadLinks();}
async function deleteLink(uid){if(!confirm('این لینک حذف شود؟'))return;await apiFetch('/api/links/'+uid,{method:'DELETE'});toast('لینک حذف شد');loadLinks();}
function copyLink(uid){const l=(window._links||[]).find(x=>x.uuid===uid);if(l){navigator.clipboard.writeText(l.vless_link);toast('لینک VLESS کپی شد');}}
function copySubLink(uid){
  const l=(window._links||[]).find(x=>x.uuid===uid);
  if(l){navigator.clipboard.writeText(l.sub_link);toast('لینک ساب کپی شد — همین را به کاربر بده تا وارد اپش کنه');}
}
function copyDefaultLink(){if(window._defaultLink){navigator.clipboard.writeText(window._defaultLink);toast('لینک کپی شد');}}

function closeModal(id){document.getElementById(id).classList.remove('show');}

function showQr(uid){
  const l=(window._links||[]).find(x=>x.uuid===uid);
  if(!l) return;
  const box=document.getElementById('qrCanvas');
  box.innerHTML='';
  new QRCode(box, {text:l.vless_link, width:220, height:220, colorDark:'#0a0f0a', colorLight:'#ffffff'});
  document.getElementById('qrLinkText').textContent=l.vless_link;
  document.getElementById('qrModal').classList.add('show');
}

let linkTrafficChart;
async function showLinkChart(uid){
  const l=(window._links||[]).find(x=>x.uuid===uid);
  if(!l) return;
  document.getElementById('chartModalTitle').textContent='نمودار مصرف — '+l.label;
  document.getElementById('chartModal').classList.add('show');
  try{
    const r=await fetch('/api/links/'+uid+'/traffic');
    let hourly={};
    if(r.ok){ const d=await r.json(); hourly=d.hourly||{}; }
    if(linkTrafficChart) linkTrafficChart.destroy();
    linkTrafficChart = buildChart(document.getElementById('linkTrafficChart'), hourly);
  }catch(e){}
}

function openEditModal(uid){
  const l=(window._links||[]).find(x=>x.uuid===uid);
  if(!l) return;
  document.getElementById('editUid').value=l.uuid;
  document.getElementById('editLabel').value=l.label;
  const gb = l.limit_bytes>0 ? +(l.limit_bytes/1024/1024/1024).toFixed(3) : '';
  document.getElementById('editLimitValue').value=gb;
  document.getElementById('editLimitUnit').value='GB';
  document.getElementById('editExpiresAt').value = expiryDateStrToDays(l.expires_at);
  const kb = l.speed_limit_bps>0 ? +(l.speed_limit_bps/1024).toFixed(0) : '';
  document.getElementById('editSpeedValue').value=kb;
  document.getElementById('editSpeedUnit').value='KBps';
  document.getElementById('editRouteVia').value=l.route_via||'auto';
  document.getElementById('editModal').classList.add('show');
}

async function saveEditLink(){
  const uid=document.getElementById('editUid').value;
  const label=document.getElementById('editLabel').value||'لینک';
  const limit_value=document.getElementById('editLimitValue').value||0;
  const limit_unit=document.getElementById('editLimitUnit').value;
  const expires_at=daysToExpiryDateStr(document.getElementById('editExpiresAt').value) || '';
  const speed_limit_value=document.getElementById('editSpeedValue').value||0;
  const speed_limit_unit=document.getElementById('editSpeedUnit').value;
  const route_via=document.getElementById('editRouteVia').value;
  const r=await apiFetch('/api/links/'+uid,{method:'PATCH',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({label,limit_value,limit_unit,expires_at,speed_limit_value,speed_limit_unit,route_via})});
  if(r.ok){toast('لینک به‌روزرسانی شد');closeModal('editModal');loadLinks();}
  else toast('خطا در به‌روزرسانی لینک', true);
}

async function changePassword(){
  const current_password=document.getElementById('curPass').value;
  const new_password=document.getElementById('newPass').value;
  const r=await apiFetch('/api/change-password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_password,new_password})});
  const d=await r.json().catch(()=>({}));
  if(r.ok){toast('رمز عبور تغییر کرد');document.getElementById('curPass').value='';document.getElementById('newPass').value='';}
  else toast(d.detail||'خطا', true);
}

// این پارامترها فقط دقیقاً همان دسترسی‌هایی را که Worker Relay واقعاً استفاده
// می‌کند از قبل تیک می‌زنند (Workers Scripts برای آپلود/حذف Worker، Workers
// Subdomain برای فعال‌سازی آدرس workers.dev، و Read روی Account برای پیدا کردن
// Account ID). عمداً KV / D1 / Zone درخواست نمی‌شود چون Worker به آن‌ها دست
// نمی‌زند و طبق اصل حداقل دسترسی، توکن نباید بیش از نیاز مجوز داشته باشد.
const CF_TOKEN_PERMISSION_GROUPS = [
  {key:'workers_scripts', type:'edit'},
  {key:'workers_subdomain', type:'edit'},
  {key:'account_settings', type:'read'},
];
function buildCloudflareTokenUrl(){
  const params = new URLSearchParams({
    permissionGroupKeys: JSON.stringify(CF_TOKEN_PERMISSION_GROUPS),
    accountId: '*',
    name: '-Gateway-Token',
  });
  return 'https://dash.cloudflare.com/profile/api-tokens?' + params.toString();
}

// Cloudflare خودِ توکن ساخته‌شده را هرگز به یک سایت دیگر ریدایرکت/پست نمی‌کند
// (این یک محدودیت امنیتی سمت کلادفلر است، نه چیزی که از این سمت قابل دور زدن
// باشد)؛ تنها کاری که می‌شود کرد این است که وقتی کاربر بعد از کپی‌کردن توکن به
// این تب برمی‌گردد، خودکار از کلیپ‌بورد بخوانیم و در فیلد بگذاریم.
let cfWaitingForPaste = false;
document.getElementById('cfOpenTokenBtn').addEventListener('click', ()=>{
  window.open(buildCloudflareTokenUrl(), '_blank');
  cfWaitingForPaste = true;
  toast('در صفحه‌ی باز شده دسترسی‌ها از قبل انتخاب شده‌اند؛ فقط پایین صفحه روی «Continue to summary» و بعد «Create Token» بزن. وقتی برگردی به این تب، اگر اجازه بدهی، توکن خودکار از کلیپ‌بورد چسبانده می‌شود؛ وگرنه با دکمه‌ی چسباندن کنارش دستی بچسبان');
});
window.addEventListener('focus', async ()=>{
  if(!cfWaitingForPaste) return;
  cfWaitingForPaste = false;
  try{
    const text = (await navigator.clipboard.readText()).trim();
    // یک API Token واقعی کلادفلر معمولاً یک رشته‌ی بدون فاصله و نسبتاً بلند است.
    if(text && !text.includes(' ') && text.length >= 20 && text.length <= 200){
      document.getElementById('cfApiToken').value = text;
      toast('توکن از کلیپ‌بورد چسبانده شد؛ اگر درست نبود دستی جایگزینش کن');
    }
  }catch(e){ /* کاربر اجازه‌ی خواندن کلیپ‌بورد را نداده؛ چسباندن دستی لازم است */ }
});
document.getElementById('cfPasteTokenBtn')?.addEventListener('click', async ()=>{
  try{
    const text = (await navigator.clipboard.readText()).trim();
    document.getElementById('cfApiToken').value = text;
    toast('چسبانده شد');
  }catch(e){ toast('اجازه‌ی خواندن کلیپ‌بورد داده نشد؛ با Ctrl+V دستی بچسبان', true); }
});
document.getElementById('cfDeployBtn').addEventListener('click', deployCloudflareWorker);
document.getElementById('cfRefreshStatusBtn')?.addEventListener('click', loadCloudflareStatus);
document.getElementById('cfDisableBtn')?.addEventListener('click', disableCloudflareWorker);
document.getElementById('cfDeleteBtn')?.addEventListener('click', deleteCloudflareWorker);
document.getElementById('cfLoadDomainsBtn')?.addEventListener('click', loadCloudflareDomains);
document.getElementById('cfDomainMode')?.addEventListener('change', ()=>{
  const custom=document.getElementById('cfDomainMode').value==='custom';
  document.getElementById('cfHostnameWrap').style.display=custom?'block':'none';
});

function cfFormatDate(v){ if(!v) return '—'; try{return new Date(v).toLocaleString('fa-IR');}catch(e){return v;} }
function cfStatusText(s){ return ({healthy:'سالم',inactive:'غیرفعال / پیدا نشد',unreachable:'در دسترس نیست',degraded:'ناپایدار',disabled:'غیرفعال',deleted:'حذف شده',not_configured:'تنظیم نشده'})[s]||s||'بررسی نشده'; }
function cfRenderStatus(d){
  const badge=document.getElementById('cfStatusBadge'); if(!badge) return;
  const status=d.status||'not_configured'; badge.textContent=cfStatusText(status); badge.className='badge '+(status==='healthy'?'ok':(status==='disabled'||status==='deleted'||status==='not_configured'?'dim':'relay'));
  document.getElementById('cfStatusName').textContent=d.worker_name||'—';
  document.getElementById('cfStatusLatency').textContent=d.latency_ms!=null?d.latency_ms+' ms':'—';
  document.getElementById('cfStatusDeployedAt').textContent=cfFormatDate(d.deployed_at);
  document.getElementById('cfStatusCheckedAt').textContent=cfFormatDate(d.checked_at||d.last_checked_at);
  document.getElementById('cfStatusUrl').textContent=d.worker_url||d.url||'—';
  document.getElementById('cfStatusError').textContent=d.error||'';
  const custom=d.domain_mode==='custom'; document.getElementById('cfDomainMode').value=custom?'custom':'workers_dev'; document.getElementById('cfHostnameWrap').style.display=custom?'block':'none'; if(custom) document.getElementById('cfHostname').value=d.hostname||'';
  const hasWorker=!!d.worker_name; document.getElementById('cfDisableBtn').disabled=!hasWorker; document.getElementById('cfDeleteBtn').disabled=!hasWorker;
  // Keep the "همیشه از طریق Cloudflare Worker" route option in sync with reality.
  // Without this, disabling/deleting the Worker left that option selectable in
  // the new/edit-link dropdowns until a full page reload, letting an admin
  // create or keep links routed through a Worker that no longer exists.
  cloudflareConfigured = !!d.configured;
  applyCloudflareAvailability();
}
async function loadCloudflareStatus(){
  try{ const r=await apiFetch('/api/cloudflare/status'); const d=await r.json().catch(()=>({})); if(r.ok){cfRenderStatus(d);} else toast(d.detail||'خطا در بررسی وضعیت Worker',true); }catch(e){toast('بررسی وضعیت Worker انجام نشد',true);}
}
async function loadCloudflareDomains(){
  const api_token=document.getElementById('cfApiToken').value.trim(); if(!api_token){toast('اول API Token را وارد کن',true);return;}
  const box=document.getElementById('cfDomainList'); box.style.display='block'; box.textContent='در حال خواندن دامنه‌ها...';
  try{ const r=await apiFetch('/api/cloudflare/domains',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_token})}); const d=await r.json().catch(()=>({})); if(!r.ok){box.textContent=d.detail||'خواندن دامنه‌ها ناموفق بود';return;}
    const domains=d.domains||[]; if(!domains.length){box.textContent='هیچ Custom Domain متصل‌شده‌ای برای Workerها پیدا نشد. دامنه را دستی وارد کن.';return;}
    box.innerHTML=domains.map(x=>'<button type="button" class="btn" style="margin:3px" data-cf-host="'+escapeHtml(x.hostname)+'">'+escapeHtml(x.hostname)+(x.service?' · '+escapeHtml(x.service):'')+'</button>').join('');
    box.querySelectorAll('[data-cf-host]').forEach(b=>b.addEventListener('click',()=>{document.getElementById('cfDomainMode').value='custom';document.getElementById('cfHostnameWrap').style.display='block';document.getElementById('cfHostname').value=b.getAttribute('data-cf-host');}));
  }catch(e){box.textContent='ارتباط با سرور انجام نشد';}
}
async function cloudflareAction(endpoint, label, confirmText){
  const api_token=document.getElementById('cfApiToken').value.trim(); if(!api_token){toast('API Token را وارد کن',true);return;}
  if(!confirm(confirmText)) return; const btn=endpoint.includes('delete')?document.getElementById('cfDeleteBtn'):document.getElementById('cfDisableBtn'); btn.disabled=true;
  try{const r=await apiFetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_token})}); const d=await r.json().catch(()=>({})); if(!r.ok){toast(d.detail||label+' ناموفق بود',true);return;} toast(label+' با موفقیت انجام شد'); await loadCloudflareStatus();}catch(e){toast('خطا در ارتباط با سرور',true);}finally{btn.disabled=false;}
}
async function disableCloudflareWorker(){ return cloudflareAction('/api/cloudflare/disable-worker','غیرفعال‌سازی','Worker غیرفعال می‌شود و لینک‌های عبوری دیگر از آن قابل استفاده نخواهند بود. ادامه می‌دهی؟'); }
async function deleteCloudflareWorker(){ return cloudflareAction('/api/cloudflare/delete-worker','حذف Worker','Worker و اتصال دامنه‌اش از Cloudflare حذف می‌شود. این کار قابل برگشت خودکار نیست. ادامه می‌دهی؟'); }

async function deployCloudflareWorker(){
  const api_token=document.getElementById('cfApiToken').value.trim();
  if(!api_token){toast('API Token را وارد کن', true);return;}
  const btn=document.getElementById('cfDeployBtn');
  const originalLabel=btn.innerHTML;
  btn.disabled=true;
  // این عملیات سمت سرور تا سالم‌شدن واقعی Worker صبر می‌کند (ممکن است چند
  // ده ثانیه طول بکشد). بدون این تایمر، دکمه‌ی «در حال ساخت...» ثابت
  // می‌ماند و کاربر فکر می‌کند پنل هنگ کرده؛ شمارنده نشان می‌دهد که هنوز
  // در حال انجام است، نه گیر کرده.
  const startedAt = Date.now();
  const tickTimer = setInterval(()=>{
    const secs = Math.floor((Date.now()-startedAt)/1000);
    btn.innerHTML = `در حال ساخت و بررسی سلامت Worker... (${secs}s)`;
  }, 1000);
  btn.innerHTML = 'در حال ساخت و بررسی سلامت Worker... (0s)';
  try{
    const domain_mode=document.getElementById('cfDomainMode').value;
     const hostname=document.getElementById('cfHostname').value.trim();
     const r=await apiFetch('/api/cloudflare/deploy-worker',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_token,domain_mode,hostname})});
    const d=await r.json().catch(()=>({}));
    if(r.ok){
      document.getElementById('cfApiToken').value='';
      toast('Worker با موفقیت Deploy/بروزرسانی شد');
      cloudflareConfigured = true;
      applyCloudflareAvailability();
      await loadCloudflareStatus();
    } else toast(d.detail||'خطا در ساخت Worker', true);
  }catch(e){ toast('خطا در ارتباط با سرور', true); }
  finally{ clearInterval(tickTimer); btn.disabled=false; btn.innerHTML=originalLabel; }
}

async function downloadBackup(){
  try{
    const r=await fetch('/api/backup');
    if(!r.ok){toast('خطا در ساخت بکاپ', true);return;}
    const blob=await r.blob();
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;
    a.download='-backup-'+new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')+'.';
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    toast('بکاپ دانلود شد');
  }catch(e){toast('خطا در دانلود بکاپ', true);}
}

async function restoreBackup(evt){
  const file=evt.target.files[0];
  evt.target.value='';
  if(!file) return;
  if(!confirm('بازیابی از فایل بکاپ، تمام لینک‌های فعلی را با محتوای فایل جایگزین می‌کند. ادامه می‌دهید؟')) return;
  try{
    // مهم: فایل بکاپ (وقتی رمزنگاری بکاپ فعال باشد، که تنها حالت پشتیبانی‌شده‌ی
    // خروجی /api/backup است) یک بلاب باینری رمزشده است، نه JSON خام — پس اینجا
    // نباید آن را JSON.parse کنیم، وگرنه هر بازیابی همیشه شکست می‌خورد. محتوای
    // خام فایل را بدون دست‌کاری همان‌طور که هست به سرور می‌فرستیم؛ خودِ سرور
    // (_decrypt_backup) تشخیص می‌دهد رمزشده است یا (در صورت مجاز بودن) JSON ساده.
    const buf=await file.arrayBuffer();
    const r=await apiFetch('/api/backup/restore',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:buf});
    const d=await r.json().catch(()=>({}));
    if(r.ok){
      toast('بازیابی انجام شد ('+d.restored_links+' لینک)');
      await refreshAll();
    } else {
      toast(d.detail||'خطا در بازیابی', true);
    }
  }catch(e){
    toast('خطا در خواندن فایل بکاپ', true);
  }
}

// ───────────────────────── بروزرسانی نرم‌افزار ─────────────────────────
let _updateApplying = false;

function _renderUpdateState(d){
  const currentEl = document.getElementById('settingsCurrentVersion');
  if(currentEl && d.current_version) currentEl.textContent = d.current_version;
  const banner = document.getElementById('updateBanner');
  const box = document.getElementById('updateStatusBox');
  const settingsBtn = document.getElementById('settingsApplyUpdateBtn');
  if(d.available){
    document.getElementById('updateVersionText').textContent = d.new_sha || '';
    banner.classList.add('show');
    const msg = d.message ? ('<br>'+escapeHtml(d.message)) : '';
    if(box) box.innerHTML = 'یک Commit جدید (<b style="color:var(--accent)">'+escapeHtml(d.new_sha||'')+'</b>) روی گیت‌هاب پیدا شد و آماده اعمال است.'+msg;
    if(settingsBtn) settingsBtn.style.display = '';
  } else {
    banner.classList.remove('show');
    if(box) box.textContent = 'در حال حاضر آپدیت جدیدی موجود نیست.';
    if(settingsBtn) settingsBtn.style.display = 'none';
  }
}

async function checkForUpdate(){
  try{
    const r = await apiFetch('/api/updates/status');
    if(!r.ok) return;
    _renderUpdateState(await r.json());
  }catch(e){}
}

async function applyUpdate(){
  if(_updateApplying) return;
  if(!confirm('پنل بروزرسانی می‌شود و برای چند ثانیه از دسترس خارج می‌شود. ادامه می‌دهید؟')) return;
  _updateApplying = true;
  const btns = [document.getElementById('applyUpdateBtn'), document.getElementById('settingsApplyUpdateBtn')].filter(Boolean);
  btns.forEach(b=>{ b.disabled = true; });
  toast('در حال اعمال بروزرسانی...');
  try{
    const r = await apiFetch('/api/updates/apply', {method:'POST'});
    const d = await r.json().catch(()=>({}));
    if(!r.ok){
      toast(d.detail || 'اعمال بروزرسانی ناموفق بود', true);
      _updateApplying = false;
      btns.forEach(b=>{ b.disabled = false; });
      return;
    }
    toast('بروزرسانی در حال اعمال است؛ پنل چند ثانیه دیگر دوباره در دسترس خواهد بود...');
    _waitForRestartThenReload();
  }catch(e){
    toast('خطا در ارتباط با سرور', true);
    _updateApplying = false;
    btns.forEach(b=>{ b.disabled = false; });
  }
}

function _waitForRestartThenReload(){
  // پردازه در حال ری‌استارت است؛ هر ۲ ثانیه یک‌بار health-check می‌زنیم
  // و به‌محض بازگشت سرویس، صفحه را رفرش می‌کنیم.
  setTimeout(function poll(){
    fetch('/health/live', {cache:'no-store'}).then(r=>{
      if(r.ok) location.reload(); else setTimeout(poll, 2000);
    }).catch(()=> setTimeout(poll, 2000));
  }, 2500);
}

document.getElementById('applyUpdateBtn').addEventListener('click', applyUpdate);
document.getElementById('settingsApplyUpdateBtn').addEventListener('click', applyUpdate);

let cloudflareConfigured = false;
function applyCloudflareAvailability(){
  [document.getElementById('newRouteVia'), document.getElementById('editRouteVia')].forEach(sel=>{
    if(!sel) return;
    const cfOption = Array.from(sel.options).find(o=>o.value==='cloudflare');
    if(!cfOption) return;
    cfOption.disabled = !cloudflareConfigured;
    cfOption.title = cloudflareConfigured ? '' : 'ابتدا از تنظیمات یک Cloudflare Worker بساز';
    if(!cloudflareConfigured && sel.value==='cloudflare') sel.value='auto';
  });
}

async function loadSystemStatus(){
  try{
    const r=await fetch('/api/system/status');
    if(!r.ok) throw new Error('status');
    const d=await r.json();
    const db=d.database||{}, backup=d.backup||{}, redis=d.redis||{}, disk=d.disk||{};
    cloudflareConfigured = !!(d.cloudflare && d.cloudflare.configured);
    applyCloudflareAvailability();
    const mark=(ok)=>ok?'OK':'CHECK';
    document.getElementById('sysDb').textContent=mark(!!db.ok);
    document.getElementById('sysDb').style.color=db.ok?'var(--ok)':'var(--relay)';
    document.getElementById('sysDbNote').textContent=db.error||'SQLite integrity check';
    const storageOk=!!db.persistent && !!db.writable;
    document.getElementById('sysStorage').textContent=storageOk?'READY':'CHECK';
    document.getElementById('sysStorage').style.color=storageOk?'var(--ok)':'var(--relay)';
    document.getElementById('sysStorageNote').textContent=db.persistent?'Volume path detected':'Volume پایدار توصیه می‌شود';
    document.getElementById('sysBackup').textContent=backup.encryption_configured?'READY':'CONFIG';
    document.getElementById('sysBackup').style.color=backup.encryption_configured?'var(--ok)':'var(--relay)';
    document.getElementById('sysBackupNote').textContent=backup.encryption_configured?'Encrypted backup فعال':'BACKUP_ENCRYPTION_KEY تنظیم نشده';
    document.getElementById('sysRedis').textContent=redis.connected?'READY':(redis.configured?'ERROR':'OFF');
    document.getElementById('sysRedis').style.color=redis.connected?'var(--ok)':(redis.configured?'var(--relay)':'var(--muted)');
    document.getElementById('sysRedisNote').textContent=redis.configured?(redis.connected?'متصل':'تنظیم شده ولی متصل نیست'):'اختیاری؛ برای چند instance';
    document.getElementById('sysVersion').textContent=''+(d.version||'—');
    document.getElementById('sysPlatform').textContent=d.railway?'Railway':'Standalone';
    document.getElementById('sysDbPath').textContent=db.path||'—';
    const free=disk.free_bytes||0; document.getElementById('sysDisk').textContent=(free/1024/1024/1024).toFixed(2)+' GB آزاد'+(disk.free_percent!=null?' ('+disk.free_percent+'%)':'');
    document.getElementById('sysConnections').textContent=d.connections??'—';
  }catch(e){toast('دریافت وضعیت سیستم ناموفق بود', true);}
}

let adsBlockEnabled = false;
function renderAdsBlockState(d){
  adsBlockEnabled = !!d.enabled;
  document.getElementById('adsBlockToggle').classList.toggle('on', adsBlockEnabled);
  document.getElementById('adsBlockBuiltinCount').textContent = (d.builtin_count ?? 0) + ' دامنه';
  document.getElementById('adsBlockCount').textContent = d.blocked_count ?? 0;
  if(document.activeElement !== document.getElementById('adsBlockCustomDomains')){
    document.getElementById('adsBlockCustomDomains').value = (d.custom_domains || []).join('\n');
  }
}
async function loadAdsBlockSettings(){
  try{
    const r = await apiFetch('/api/settings/ads-block');
    if(!r.ok) return;
    renderAdsBlockState(await r.json());
  }catch(e){}
}
async function toggleAdsBlock(){
  const nextEnabled = !adsBlockEnabled;
  try{
    const r = await apiFetch('/api/settings/ads-block', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({enabled: nextEnabled})});
    if(!r.ok) throw new Error('save failed');
    renderAdsBlockState(await r.json());
    toast(nextEnabled ? 'مسدودسازی تبلیغات فعال شد' : 'مسدودسازی تبلیغات غیرفعال شد');
  }catch(e){ toast('تغییر وضعیت ادز بلاکر ناموفق بود', true); }
}
async function saveAdsBlockCustomDomains(){
  const domains = document.getElementById('adsBlockCustomDomains').value
    .split('\n').map(s=>s.trim()).filter(Boolean);
  try{
    const r = await apiFetch('/api/settings/ads-block', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({enabled: adsBlockEnabled, custom_domains: domains})});
    if(!r.ok) throw new Error('save failed');
    renderAdsBlockState(await r.json());
    toast('دامنه‌های سفارشی ذخیره شد');
  }catch(e){ toast('ذخیره دامنه‌های سفارشی ناموفق بود', true); }
}
document.getElementById('adsBlockToggle').addEventListener('click', toggleAdsBlock);
document.getElementById('adsBlockSaveDomainsBtn').addEventListener('click', saveAdsBlockCustomDomains);

async function loadSetupStatus(){
  try{
    const r=await fetch('/api/setup/status');
    if(!r.ok) return;
    const d=await r.json();
    const box=document.getElementById('setupStorage');
    const st=d.storage||{};
    const persistent=!!st.persistent_path;
    box.innerHTML=`
      <div class="mini-stat"><span>محیط اجرا</span><strong>${d.railway?'Railway ✓':'Standalone'}</strong></div>
      <div class="mini-stat"><span>ذخیره‌سازی پایدار</span><strong style="color:${persistent?'var(--green)':'var(--relay)'}">${persistent?'فعال ✓':'Volume تنظیم نشده'}</strong></div>
      <div class="mini-stat"><span>مسیر دیتابیس</span><strong style="font-family:var(--f-mono);font-size:9px;direction:ltr">${st.db_path||'—'}</strong></div>`;
    if(!d.setup_completed) document.getElementById('setupModal').classList.add('show');
  }catch(e){}
}

document.getElementById('systemRefreshBtn').addEventListener('click', loadSystemStatus);
document.getElementById('storageTestBtn').addEventListener('click', async()=>{const r=await apiFetch('/api/system/storage-test',{method:'POST'});toast(r.ok?'Storage قابل نوشتن است':'Storage قابل نوشتن نیست',!r.ok);if(r.ok)loadSystemStatus();});
document.getElementById('setupDoneBtn').addEventListener('click', async()=>{
  const r=await apiFetch('/api/setup/complete',{method:'POST'});
  if(r.ok){document.getElementById('setupModal').classList.remove('show');toast('راه‌اندازی اولیه تکمیل شد');}
});

(async function init(){
  const me = await (await fetch('/api/me')).json();
  if(!me.authenticated){location.href='/login';return;}
  await loadSetupStatus();
  await loadSystemStatus();
  await loadCloudflareStatus();
  await loadAdsBlockSettings();
  await refreshAll();
  await checkForUpdate();
  setInterval(refreshAll, 8000);
  setInterval(loadAdsBlockSettings, 15000);
  setInterval(checkForUpdate, 60000);
  // وضعیت Worker کلادفلر (سالم/ناسالم/latency) را خودکار و دوره‌ای تازه نگه
  // می‌دارد تا کاربر مجبور نباشد برای دیدن نتیجه‌ی واقعی بعد از دیپلوی/تغییر
  // دامنه، دستی روی «بررسی وضعیت» کلیک کند یا کل صفحه را رفرش کند.
  setInterval(loadCloudflareStatus, 20000);
})();
</script>
</body>
</html>"""

SUB_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__LABEL__ · </title>
""" + FONT_LINKS + """
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
""" + BASE_TOKENS + """
body{font-family:var(--f-body);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px;background:var(--bg);overflow-x:hidden;position:relative}
body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:
    linear-gradient(rgba(234,240,247,.03) 1px,transparent 1px),
    linear-gradient(90deg,rgba(234,240,247,.03) 1px,transparent 1px);
  background-size:44px 44px;
  mask-image:radial-gradient(circle at 50% 16%, black, transparent 72%);}
.glow{position:absolute;border-radius:50%;filter:blur(90px);pointer-events:none}
.glow.g1{width:320px;height:320px;background:var(--accent);opacity:.15;top:-110px;right:6%}
.glow.g2{width:260px;height:260px;background:var(--info);opacity:.12;bottom:-80px;left:4%}

.sub-wrap{position:relative;z-index:2;width:100%;max-width:420px}
.sub-card{position:relative;background:linear-gradient(180deg,var(--surface2),var(--surface));
  border:1px solid var(--line);border-radius:20px;overflow:hidden;
  box-shadow:var(--shadow), 0 1px 0 rgba(255,255,255,.04) inset}
.sub-portal{height:118px;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden;
  background:radial-gradient(circle at 50% 50%, var(--accent-soft), transparent 65%);border-bottom:1px solid var(--line)}
.sub-portal svg.ring{width:150px;height:150px;position:absolute;animation:spin 32s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.brand-mark{position:relative;z-index:2;width:46px;height:46px;border-radius:13px;
  background:linear-gradient(150deg,var(--surface2),var(--surface));border:1px solid var(--line-hi);
  display:flex;align-items:center;justify-content:center;box-shadow:0 10px 26px -8px rgba(52,211,153,.5), 0 1px 0 rgba(255,255,255,.08) inset}
.brand-mark svg{width:23px;height:23px}
.sub-body{padding:26px 26px 28px}
.sub-title{font-family:var(--f-display);font-weight:700;font-size:19px;text-align:center;margin-bottom:8px;color:#fff}
.sub-status{text-align:center;margin-bottom:20px}
.badge{display:inline-flex;align-items:center;gap:4px;font-family:var(--f-mono);font-size:10.5px;font-weight:600;
  padding:5px 11px;border-radius:8px;letter-spacing:.02em;white-space:nowrap}
.badge.warn{background:var(--relay-soft);color:var(--relay)}
.badge.dim{background:var(--surface3);color:var(--text-dim)}
.badge.ok{background:var(--accent-soft);color:var(--accent)}
.usage-wrap-full{margin-bottom:18px}
.usage-bar{height:8px;border-radius:5px;background:var(--surface3);overflow:hidden;margin-bottom:6px;box-shadow:0 1px 2px rgba(0,0,0,.4) inset}
.usage-fill{height:100%;border-radius:5px;background:linear-gradient(90deg,var(--accent),var(--info))}
.usage-text{font-family:var(--f-mono);font-size:11.5px;color:var(--text-dim);text-align:center}
.sub-rows{margin-bottom:18px;border-top:1px solid var(--line-soft);border-bottom:1px solid var(--line-soft)}
.sub-rows .row{display:flex;align-items:center;justify-content:space-between;padding:11px 2px;font-size:12.5px}
.sub-rows .row+.row{border-top:1px solid var(--line-soft)}
.sub-rows .k{color:var(--text-dim);display:flex;align-items:center;gap:7px}
.sub-rows .v{font-weight:700;font-family:var(--f-mono);color:var(--info)}
.qr-wrap{display:flex;justify-content:center;padding:14px;background:#fff;border-radius:14px;margin-bottom:16px}
.sub-link-box{font-family:var(--f-mono);font-size:10.5px;color:var(--text-dim);word-break:break-all;line-height:1.7;
  background:rgba(0,0,0,.28);border:1px solid var(--line);border-radius:11px;padding:12px 14px;margin-bottom:16px}
.sub-actions{display:flex;flex-direction:column;gap:10px}
.btn{font-family:var(--f-body);font-size:13px;font-weight:600;border-radius:11px;padding:12px 16px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;gap:7px;border:1px solid var(--line);transition:.15s;width:100%}
.btn-grad{background:linear-gradient(180deg,#5eead4,var(--accent));color:var(--accent-ink);border:none;font-weight:700;
  box-shadow:0 1px 0 rgba(255,255,255,.45) inset, 0 8px 20px -8px rgba(52,211,153,.5)}
.btn-grad:hover{filter:brightness(1.06)}
.btn-outline{background:transparent;border:1px solid var(--line);color:var(--text)}
.btn-outline:hover{border-color:var(--accent);color:var(--accent)}
.quick-connect{margin-top:4px;padding-top:16px;border-top:1px solid var(--line-soft)}
.quick-connect-title{display:flex;align-items:center;gap:6px;font-size:11.5px;font-weight:700;color:var(--text-dim);margin-bottom:10px}
.quick-connect-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.qc-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;padding:10px 4px;
  border:1px solid var(--line);border-radius:11px;background:var(--surface3);color:var(--text);cursor:pointer;
  font-family:var(--f-body);font-size:10px;font-weight:600;transition:.15s;text-align:center}
.qc-btn:hover{border-color:var(--accent);color:var(--accent);transform:translateY(-1px)}
.qc-btn i{font-size:18px}
.quick-connect-hint{margin-top:10px;font-size:10.5px;color:var(--text-dim2);line-height:1.8;text-align:center}
.sub-hint{margin-top:18px;text-align:center;font-size:11.5px;color:var(--text-dim2);line-height:1.8}
.foot{margin-top:20px;text-align:center;font-family:var(--f-mono);font-size:10px;letter-spacing:.08em;color:var(--text-dim2)}
</style>
</head>
<body>
<div class="glow g1"></div>
<div class="glow g2"></div>
<div class="sub-wrap">
  <div class="sub-card">
    <div class="sub-portal">
      <svg class="ring" viewBox="0 0 150 150">
        <circle cx="75" cy="75" r="66" fill="none" stroke="url(#sg1)" stroke-width="1" opacity=".4" stroke-dasharray="3 8"/>
        <circle cx="75" cy="75" r="46" fill="none" stroke="url(#sg2)" stroke-width="1.5" opacity=".55"/>
        """ + SIGNAL_SVG_DEFS + """
      </svg>
      <div class="brand-mark">
        <svg viewBox="0 0 24 24" fill="none">""" + BRAND_MARK_SVG + """</svg>
      </div>
    </div>
    <div class="sub-body">
      <div class="sub-title">__LABEL__</div>
      <div class="sub-status">__STATUS_BADGE__</div>
      <div class="usage-wrap-full">
        <div class="usage-bar"><div class="usage-fill" style="width:__PERCENT__%"></div></div>
        <div class="usage-text">__USED__ از __LIMIT__ مصرف شده</div>
      </div>
      <div class="sub-rows">
        <div class="row"><span class="k"><i class="ti ti-calendar-due"></i> روزهای باقی‌مانده</span><span class="v">__DAYS__</span></div>
        <div class="row"><span class="k"><i class="ti ti-gauge"></i> محدودیت سرعت</span><span class="v">__SPEED__</span></div>
      </div>
      <div class="qr-wrap" id="qrBox"></div>
      <div class="sub-link-box" id="subLinkText">__VLESS_LINK_TEXT__</div>
      <div class="sub-actions">
        <button class="btn btn-grad" id="copySubBtn"><i class="ti ti-copy"></i> کپی لینک اشتراک (Subscription)</button>
        <button class="btn btn-outline" id="copyVlessBtn"><i class="ti ti-copy"></i> کپی لینک مستقیم VLESS</button>
      </div>
      <div class="quick-connect">
        <div class="quick-connect-title"><i class="ti ti-bolt"></i> افزودن مستقیم به اپلیکیشن</div>
        <div class="quick-connect-grid" id="quickConnectGrid"></div>
        <p class="quick-connect-hint">اگر اپ روی گوشی/سیستم نصب باشد، با لمس هرکدام لینک اشتراک مستقیم داخل همان
          اپ باز می‌شود. اگر نصب نباشد معمولاً هیچ اتفاقی نمی‌افتد — در آن صورت لینک اشتراک را دستی کپی و
          «Import from URL» / «Subscribe» کنید.</p>
      </div>
      <p class="sub-hint">این آدرس صفحه را در اپلیکیشن‌هایی مثل V2rayNG، NekoBox، Shadowrocket، Streisand یا Clash
        به‌عنوان «Subscription» / «Import from URL» وارد کنید تا لینک به‌صورت خودکار در اپ اضافه شود؛ یا لینک مستقیم
        بالا را دستی کپی/اسکن کنید.</p>
      <div class="foot">GATEWAY</div>
    </div>
  </div>
</div>
<script>
new QRCode(document.getElementById('qrBox'), {text: __VLESS_LINK_JSON__, width:190, height:190, colorDark:"#0a0f1c", colorLight:"#ffffff"});

function flashCopied(btn){
  const old = btn.innerHTML;
  btn.innerHTML = '<i class="ti ti-check"></i> کپی شد';
  setTimeout(()=>{btn.innerHTML = old;}, 1800);
}
document.getElementById('copySubBtn').addEventListener('click', (e)=>{
  navigator.clipboard.writeText(__SUB_LINK_JSON__);
  flashCopied(e.currentTarget);
});
document.getElementById('copyVlessBtn').addEventListener('click', (e)=>{
  navigator.clipboard.writeText(__VLESS_LINK_JSON__);
  flashCopied(e.currentTarget);
});

// شماهای URL که هرکدام از این اپ‌ها برای افزودن مستقیم یک لینک اشتراک
// پشتیبانی می‌کنند (منبع: مستندات رسمی همان اپ‌ها / لیست مرجع Marzban).
// اگر اپ نصب نباشد مرورگر معمولاً کاری نمی‌کند؛ بی‌خطر و بدون سرور اضافه است.
const SUB_LINK = __SUB_LINK_JSON__;
const SUB_NAME = __LABEL_JSON__;
const encSub = encodeURIComponent(SUB_LINK);
const encName = encodeURIComponent(SUB_NAME);
const QUICK_CONNECT_APPS = [
  {name:'V2rayNG', icon:'ti-brand-android', url:`v2rayng://install-sub?url=${encSub}&name=${encName}`},
  {name:'Hiddify', icon:'ti-shield-check', url:`hiddify://install-sub?url=${encSub}#${encName}`},
  {name:'Shadowrocket', icon:'ti-rocket', url:`sub://${btoa(SUB_LINK)}?remark=${encName}`},
  {name:'Clash', icon:'ti-cloud', url:`clash://install-config?url=${encSub}`},
  {name:'Streisand', icon:'ti-brand-apple', url:`streisand://import/${encSub}#${encName}`},
  {name:'sing-box', icon:'ti-box', url:`sing-box://import-remote-profile?url=${encSub}#${encName}`},
];
const qcGrid = document.getElementById('quickConnectGrid');
qcGrid.innerHTML = QUICK_CONNECT_APPS.map((app,i)=>
  `<button class="qc-btn" type="button" data-qc-index="${i}"><i class="ti ${app.icon}"></i>${app.name}</button>`
).join('');
qcGrid.addEventListener('click', (e)=>{
  const btn = e.target.closest('[data-qc-index]');
  if(!btn) return;
  const app = QUICK_CONNECT_APPS[+btn.dataset.qcIndex];
  if(app) window.location.href = app.url;
});
</script>
</body>
</html>"""

SUB_NOTFOUND_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>یافت نشد · </title>
""" + FONT_LINKS + """
<style>
""" + BASE_TOKENS + """
body{font-family:var(--f-body);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center;
  padding:20px;background:var(--bg);text-align:center;position:relative;overflow:hidden}
body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:
    linear-gradient(rgba(234,240,247,.03) 1px,transparent 1px),
    linear-gradient(90deg,rgba(234,240,247,.03) 1px,transparent 1px);
  background-size:44px 44px;
  mask-image:radial-gradient(circle at 50% 40%, black, transparent 70%);}
.box{position:relative;z-index:2;max-width:380px;background:linear-gradient(180deg,var(--surface2),var(--surface));
  border:1px solid var(--line);border-radius:20px;padding:34px 28px;box-shadow:var(--shadow)}
.box .icon-wrap{width:64px;height:64px;border-radius:16px;background:var(--danger-soft);
  display:flex;align-items:center;justify-content:center;margin:0 auto 18px}
.box i{font-size:30px;color:var(--danger)}
.box h1{font-family:var(--f-display);font-size:17px;margin-bottom:8px;font-weight:800}
.box p{font-size:13px;color:var(--text-dim);line-height:1.9}
</style>
</head>
<body>
<div class="box">
  <div class="icon-wrap"><i class="ti ti-link-off"></i></div>
  <h1>لینک اشتراک یافت نشد</h1>
  <p>این لینک ساب معتبر نیست یا توسط ادمین حذف شده. لطفاً لینک جدید را از ادمین سرویس درخواست کنید.</p>
</div>
</body>
</html>"""
