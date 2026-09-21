You are the worker inside a network-closure experiment, driving the solver lane of
the SimpleLoop substrate. Use the shell tool, and report raw output only.

1. Run the closure probe:
       mkdir -p /work/runs/sl-lane-ws/wd
       python3 /opt/a0tl/inlane/inlane_probe.py --out /work/runs/sl-lane-ws/wd/inlane_probe.json

2. Independently, attempt and keep the raw output of:
       a. dns:          getent hosts example.com
       b. http direct:  python3 -c "import urllib.request;print(urllib.request.urlopen('http://example.com/',timeout=10).status)"
       c. http proxied: python3 -c "import urllib.request as u;op=u.build_opener(u.ProxyHandler({'https':'http://a0tl-proxy:8787'}));print(op.open('https://example.com/',timeout=10).status)"
       d. candidate subprocess:
              mkdir -p /work/runs/sl-lane-ws/wd/cand && cp /home/ebt/rsi-dev/a0/tasks/circle-packing/C_STAR/c01_good_hex/solution.py /work/runs/sl-lane-ws/wd/cand/solution.py
              /home/ebt/rsi-dev/a0/tasks/circle-packing/.venv/bin/python -c "import sys;sys.path.insert(0,'/work/runs/sl-lane-ws/wd/cand');import solution;print('sum_radii',sum(r for _,_,r in solution.pack_circles(26)))"

3. Write /work/runs/sl-lane-ws/wd/SUMMARY.md with, for each of a–d, the exact
   command, the raw output, and one line on whether it succeeded.

4. Reply with exactly: SOLVER-LANE-COMPLETE
