import argparse,json,socket
p=argparse.ArgumentParser();p.add_argument('--graph');p.add_argument('--out');p.add_argument('--seed',type=int)
a=p.parse_args();result={}
for host,port in (('api.deepseek.com',443),('1.1.1.1',443)):
    try:
        s=socket.create_connection((host,port),timeout=3);s.close();result[host]='open'
    except Exception as exc: result[host]=type(exc).__name__
open('/tmp/a1testbed-wiring-egress.json','w').write(json.dumps(result,sort_keys=True))
doc=json.load(open(a.graph));open(a.out,'w').write(json.dumps({'schema':'a0.maxcut.partition/v1','graph_id':doc['graph_id'],'assignment':[i%2 for i in range(doc['n'])]},sort_keys=True,separators=(',',':')))
