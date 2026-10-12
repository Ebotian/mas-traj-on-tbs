// replay/data.ts —— 轨迹重建的数据契约与加载器(框架无关)。
export interface ReplayResult {
  ts: string | null; uuid?: string; parent?: string | null; callId: string | null
  status: string | null; executionStatus: string | null
  resultDisplay: { type?: string; exitCode?: number | null; output?: string; [k: string]: unknown } | null
  parts: unknown[]; raw?: string
}
export interface ReplayCall { call: { id?: string; callId?: string; name?: string; args?: Record<string, unknown> }; result: ReplayResult | null }
export interface ReplayUsage { promptTokenCount?: number; candidatesTokenCount?: number; thoughtsTokenCount?: number; cachedContentTokenCount?: number; totalTokenCount?: number }
export interface ReplayPart { thought?: boolean; text?: string; functionCall?: { id?: string; name?: string; args?: Record<string, unknown> } }
export interface ReplayTurn { actor: string; t0: string | null; t1: string | null; model: string | null; usage: ReplayUsage | null; parts: ReplayPart[]; calls: ReplayCall[]; texts: string[]; thoughts: string[]; results: ReplayResult[]; raw?: string }
export interface ReplaySystem { actor: string; ts: string | null; payload: unknown; raw?: string }
export interface ReplayCommit { sha: string; parents: string[]; date: string; refs: string; subject: string; branches: string[] }
export interface ReplayGate { ts: string; text: string }
export interface ReplayBoardItem { kind: string; id?: string; subject?: string; createdBy?: string; createdAt?: number }
export interface ReplayTokenStats { prompt: number; cached: number; uncached: number; out: number; out_visible: number; out_thoughts: number; total: number }
export interface ReplayCost { scheme: string; currency: string; peak?: boolean; rate?: number; usd?: number; cny?: number; cr_k1?: number; cr_k072?: number }
export interface ReplayActorStats { turns: number; model: string | null; models: string[]; span_s: number | null; durations_ms: number[]; tokens: ReplayTokenStats; cost: ReplayCost | null }
export interface ReplayStats { actors: Record<string, ReplayActorStats>; mapping: Record<string, string> }
export interface ReplayBundle { exp: string; label: string; generated_at: string; actors: {actor:string;model:string;effort:string}[]; sessions:{turns:ReplayTurn[];systems:ReplaySystem[];raw_lines?:number;userPrompts?:{actor:string;parts:{text?:string}[]|null;raw?:string;ts?:string}[]}; git:{commits:ReplayCommit[];tags:{name:string;sha:string}[];raw:string}; ops:{gate:ReplayGate[];board:ReplayBoardItem[];state?:Record<string,unknown>}; time_range:{t0:string|null;t1:string|null}; counts:{turns:number;thoughts:number;calls:number;commits:number;tags:number;gate:number;board:number;systems:number}; stats?: ReplayStats; mode?: string; sources?: string[] }
export interface IndexEntry { exp: string; label: string; trial: string; counts: ReplayBundle['counts']; time_range: {t0:string|null;t1:string|null}; mode?: string; tokens_total?: number; costs?: Record<string, ReplayCost> }

let idxCache: IndexEntry[] | null = null; const bndleCache = new Map<string,ReplayBundle>()
export async function loadIndex(): Promise<IndexEntry[]> { if(idxCache) return idxCache; const r=await fetch('replay/index.json'); if(!r.ok)throw new Error(`HTTP ${r.status}`); const d=await r.json() as IndexEntry[]; idxCache=d; return d }
export async function loadBundle(exp: string): Promise<ReplayBundle> { const h=bndleCache.get(exp); if(h)return h; const r=await fetch(`replay/${exp}.json`); if(!r.ok)throw new Error(`HTTP ${r.status}`); const b=await r.json() as ReplayBundle; bndleCache.set(exp,b); return b }
export function ms(v:string|null|undefined):number{return v?Date.parse(v):NaN}
export function hhmmss(iso:string|null|undefined,sub=false){const t=ms(iso);if(Number.isNaN(t))return'\u2014';const d=new Date(t);const base=[d.getUTCHours(),d.getUTCMinutes(),d.getUTCSeconds()].map(x=>String(x).padStart(2,'0')).join(':');return sub?`${base}.${String(d.getUTCMilliseconds()).padStart(3,'0')}`:base}
export function dur(a:string|null|undefined,b:string|null|undefined):string{const d=ms(b)-ms(a);if(Number.isNaN(d))return'\u2014';const ad=Math.abs(d);if(ad<1e3)return`${ad}ms`;if(ad<6e4)return`${(ad/1e3).toFixed(1)}s`;const m=Math.floor(ad/6e4),s=Math.round((ad%6e4)/1e3);return`${m}m${s?s+'s':''}`}
export function fmtBytes(n:number){return n<1024?`${n} B`:n<1048576?`${(n/1024).toFixed(1)} KB`:`${(n/1048576).toFixed(2)} MB`}
export function sha7(s:string){return s.slice(0,7)}
export function commitsAsc(b:ReplayBundle):ReplayCommit[]{return[...b.git.commits].reverse()}
export function mapSystems(b:ReplayBundle):Map<number,ReplaySystem[]>{const m=new Map<number,ReplaySystem[]>();for(const ev of b.sessions.systems){let target=-1;for(let i=0;i<b.sessions.turns.length;i++){if(b.sessions.turns[i].actor===ev.actor&&ms(b.sessions.turns[i].t0)>=ms(ev.ts)){target=i;break}}if(target<0)for(let i=b.sessions.turns.length-1;i>=0;i--){if(b.sessions.turns[i].actor===ev.actor){target=i;break}}if(target<0)continue;let arr=m.get(target);if(!arr){arr=[];m.set(target,arr)}arr.push(ev)}return m}
