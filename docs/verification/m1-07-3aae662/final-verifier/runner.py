import hashlib,json,os,pathlib,subprocess,sys,statistics
ROOT=pathlib.Path("/private/tmp/dex-m1-07-audit/final-verifier")
REC="/private/tmp/dex-m1-07-audit/record.py"
WT={s:pathlib.Path("/private/tmp/dex-m1-07-final-"+s) for s in ("head","parent","trunk")}
ENV=["env","-u","PYTHONPATH","-u","VIRTUAL_ENV","UV_OFFLINE=1"]
def run(label,side,args):
    cmd=[sys.executable,REC,"--cwd",str(WT[side]),"--out",str(ROOT/(label+".txt")),"--",*args]
    print(json.dumps(cmd),flush=True)
    return subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
def save(name,data):
    p=ROOT/name
    with p.open("x") as f:f.write(data)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
    timer=pathlib.Path("/private/tmp/dex-m1-05-06-audit/measure.py")
    assert digest(timer)=="64349ee4f8d8959cb8a9cede296988d00e78941e38744a3b4805e99649f6b4b9"
    save("measure.py",timer.read_text())
    for name in ("recovery-complete","recovery-size-1000"):
        save(name+".json",(WT["head"]/("tests/scenarios/"+name+".json")).read_text())
    schedule={"method":"historical shared timer v2 unchanged; monotonic wall, adjacent UTC drift <=0.050 seconds, single child getrusage Darwin bytes","claim":"final head satisfies absolute recovery gates and supported median startup/workload wall and RSS regression <=20 percent","gates":{"recovery_workload_seconds":10,"full_cli_seconds":20,"rss_bytes":536870912,"median_regression":1.2},"order":[["cold-trunk-help","trunk","help"],["unsupported-trunk-workspace","trunk","workspace"],["unsupported-trunk-recovery","trunk","recovery"]]+[[f"help-{i}-{s}",s,"help"] for i in range(1,6) for s in (("trunk","head") if i%2 else ("head","trunk"))]+[[f"workload-{i}-{s}",s,"recovery"] for i in range(1,6) for s in (("parent","head") if i%2 else ("head","parent"))],"input_hash":digest(ROOT/"recovery-size-1000.json"),"inner":"durable_append + reopen_rebuild + recovery, unchanged source timers","validation":"all actual/expected matches; SQL event rows/remote unique operations; separate reopened state check outside timing","environment":"same Python 3.13.11 uv 0.11.31; clear PYTHONPATH VIRTUAL_ENV; offline locked dependency environments; no network models","first_failure":"formal/12-performance/report.md ISSUES retained; centisecond 0.06 -> 0.08 +33.3 percent, wrapper 19.03 percent, original cold RSS absent","exclusions":"only separately declared instrumentation; no discarded valid slow runs or repeats until green"}
    save("schedule.json",json.dumps(schedule,indent=2)+"\n")
    hashes={}
    for side in ("head","parent"):
        hashes[side]={str(p.relative_to(WT[side])):digest(p) for p in sorted((WT[side]/"src").rglob("*.py"))}
    changed=[p for p in hashes["head"] if hashes["head"][p]!=hashes["parent"].get(p)]
    assert changed==["src/dex/cli.py"],changed
    save("source-hashes.json",json.dumps(hashes,indent=2)+"\n")
    run("identity","head",["python3","-c","import subprocess,sys; print(sys.version); subprocess.run(['uv','--version']); subprocess.run(['.venv/bin/detect-secrets','--version']); subprocess.run(['git','diff','e7eabc89ac47e6abb870e4e4f4306dc891b53217','HEAD'])"])
def functional():
    r=run("focused-tests","head",ENV+["uv","run","--locked","pytest","-q","tests/test_cli.py","tests/workspace/test_recovery.py"])
    print(r.stdout[-2500:],flush=True)
    results=[]
    for p in sorted((WT["head"]/"tests/scenarios").glob("recovery-*.json")):
        if p.stem=="recovery-size-1000":continue
        out=ROOT/("functional-"+p.stem)
        r=run("cli-"+p.stem,"head",ENV+["uv","run","--locked","dex","eval","--scenario",str(p),"--out",str(out)])
        actual=json.loads((out/"actual.json").read_text())
        expected=json.loads((out/"expected.json").read_text())
        results.append({"name":p.stem,"exit":r.returncode,"actual":actual,"expected":expected})
        print(p.stem,r.returncode,flush=True)
    save("functional-results.json",json.dumps(results,indent=2)+"\n")
def perf():
    schedule=json.loads((ROOT/"schedule.json").read_text())
    results=[]
    for label,side,kind in schedule["order"]:
        if kind=="help":args=["--help"]
        elif kind=="workspace":args=["workspace"]
        else:args=["eval","--scenario",str(ROOT/"recovery-size-1000.json"),"--out",str(ROOT/label)]
        r=run(label,side,[sys.executable,str(ROOT/"measure.py"),"--",*ENV,"uv","run","--locked","dex",*args])
        lines=[x for x in r.stdout.splitlines() if x.startswith("MEASUREMENT ")]
        measurement=json.loads(lines[-1][12:]) if lines else None
        results.append({"label":label,"side":side,"kind":kind,"status":r.returncode,"measurement":measurement})
        print(label,r.returncode,measurement,flush=True)
    save("measurements.json",json.dumps(results,indent=2)+"\n")
if __name__=="__main__":globals()[sys.argv[1]]()

