import sys, datetime as dt, subprocess, time, os, re, shutil
sys.path.insert(0, "tests")
import fakepdf as fp
from playwright.sync_api import sync_playwright
S=os.environ["S"]; PORT=int(sys.argv[1]); label=sys.argv[2]
data=f"{S}/browser-data-{label}"; shutil.rmtree(data, ignore_errors=True); os.makedirs(data, mode=0o700)
pdf=f"{S}/fake_ing_{label}.pdf"
open(pdf,"wb").write(fp.ing_statement(500000,[(dt.date(2025,3,1),"FAKE CAFE",-1500),(dt.date(2025,3,2),"FAKE SHOP",-2500)]))
env=dict(os.environ, BUDGET_DATA_DIR=data, BUDGET_PORT=str(PORT))
srv=subprocess.Popen([".venv/bin/python","-u","run.py"],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
link=None
for _ in range(40):
    line=srv.stdout.readline()
    m=re.search(r"(http://127\.0\.0\.1:\d+/enter\?t=\S+)",line)
    if m: link=m.group(1); break
try:
    with sync_playwright() as p:
        b=p.chromium.launch(channel="chrome",headless=True)
        pg=b.new_page()
        r=pg.goto(link); print("open link ->",r.status,pg.url.split("?")[0])
        print("home text:",pg.inner_text("body")[:60].replace("\n"," "))
        pg.set_input_files("input[name=statement]",pdf)
        with pg.expect_navigation() as nav:
            pg.click("button[type=submit], input[type=submit]")
        resp=nav.value; print("browser sent Origin:", resp.request.headers.get("origin"))
        print("upload ->",resp.status,pg.url.split("?")[0].replace(f"127.0.0.1:{PORT}","HOST"))
        print("page text:",pg.inner_text("body")[:90].replace("\n"," "))
        b.close()
finally:
    srv.terminate()
