from pathlib import Path
import sys,copy,json,hashlib,zipfile
from lxml import etree as E
import argparse
parser=argparse.ArgumentParser(); parser.add_argument('--source',type=Path,required=True); parser.add_argument('--outdir',type=Path,required=True); args=parser.parse_args()
SRC=args.source;O=args.outdir;O.mkdir(parents=True,exist_ok=True);DEST=O/'IS5542-Group24-Slides-v6.pptx'
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def q(tag):prefix,local=tag.split(':');return '{'+NS[prefix]+'}'+local
def el(tag,**attrs):return E.Element(q(tag),{k:str(v) for k,v in attrs.items()})
def child(parent,tag,**attrs):n=el(tag,**attrs);parent.append(n);return n
def shape(tree,id):return tree.xpath(f'./p:spTree/*[.//p:cNvPr[@id="{id}"]]',namespaces=NS)[0] if tree.tag==q('p:cSld') else tree.xpath(f'.//p:spTree/*[.//p:cNvPr[@id="{id}"]]',namespaces=NS)[0]
def txbody(sh):return sh.find('p:txBody',NS)
def settext(sh,text,font=None,color=None,bold=None):
 tb=txbody(sh) if sh.tag==q('p:sp') else sh.find('a:txBody',NS)
 assert tb is not None
 rpr=tb.find('.//a:rPr',NS)
 default=copy.deepcopy(rpr) if rpr is not None else el('a:rPr',lang='en-US')
 if font is not None:default.set('sz',str(round(font*100)))
 if bold is not None:default.set('b','1' if bold else '0')
 if color:
  for f in default.findall('a:solidFill',NS):default.remove(f)
  fill=el('a:solidFill');child(fill,'a:srgbClr',val=color)
  default.insert(1 if len(default) and default[0].tag==q('a:ln') else 0,fill)
 body=tb.find('a:bodyPr',NS)
 if body is not None:
  body.set('anchor','t');body.set('lIns','0');body.set('rIns','0');body.set('tIns','0');body.set('bIns','0')
  for x in list(body):
   if x.tag in [q('a:normAutofit'),q('a:spAutoFit'),q('a:noAutofit')]:body.remove(x)
  child(body,'a:noAutofit')
 for p in list(tb.findall('a:p',NS)):tb.remove(p)
 for line in text.split('\n'):
  p=child(tb,'a:p');pp=child(p,'a:pPr',algn='l',marL='0',marR='0',indent='0')
  ls=child(pp,'a:lnSpc');child(ls,'a:spcPct',val='105000')
  r=child(p,'a:r');r.append(copy.deepcopy(default));child(r,'a:t').text=line
  child(p,'a:endParaRPr',lang='en-US',sz=default.get('sz','1500'))
def bounds(sh,x=None,y=None,w=None,h=None):
 xf=sh.find('p:spPr/a:xfrm',NS)
 if xf is None:xf=sh.find('p:xfrm',NS)
 if xf is None:xf=sh.find('a:xfrm',NS)
 assert xf is not None
 off=xf.find('a:off',NS);ext=xf.find('a:ext',NS)
 for k,v in [('x',x),('y',y)]:
  if v is not None:off.set(k,str(round(v*914400)))
 for k,v in [('cx',w),('cy',h)]:
  if v is not None:ext.set(k,str(round(v*914400)))
def textshape(id,text,x,y,w,h,font=16,color='FFFFFF',bold=False):
 sp=el('p:sp');nv=child(sp,'p:nvSpPr');child(nv,'p:cNvPr',id=id,name=text.replace('\n',' ')[:60]);child(nv,'p:cNvSpPr',txBox='1');child(nv,'p:nvPr')
 pr=child(sp,'p:spPr');xf=child(pr,'a:xfrm');child(xf,'a:off',x=round(x*914400),y=round(y*914400));child(xf,'a:ext',cx=round(w*914400),cy=round(h*914400))
 geo=child(pr,'a:prstGeom',prst='rect');child(geo,'a:avLst');child(pr,'a:noFill');ln=child(pr,'a:ln');child(ln,'a:noFill')
 tb=child(sp,'p:txBody');child(tb,'a:bodyPr',wrap='square');child(tb,'a:lstStyle');p=child(tb,'a:p');r=child(p,'a:r');rp=child(r,'a:rPr',lang='en-US',sz=round(font*100));child(rp,'a:latin',typeface='Arial');child(r,'a:t').text=text
 settext(sp,text,font,color,bold);return sp
def rect(id,x,y,w,h,fill='203F50'):
 sp=textshape(id,'',x,y,w,h)
 pr=sp.find('p:spPr',NS)
 for node in list(pr):
  if node.tag in [q('a:noFill'),q('a:ln')]:pr.remove(node)
 f=child(pr,'a:solidFill');child(f,'a:srgbClr',val=fill)
 line=child(pr,'a:ln',w='9525');lf=child(line,'a:solidFill');child(lf,'a:srgbClr',val='56717E')
 return sp
def arrow(id,x,y,w):
 sp=el('p:cxnSp');nv=child(sp,'p:nvCxnSpPr');child(nv,'p:cNvPr',id=id,name='Rollout connector');child(nv,'p:cNvCxnSpPr');child(nv,'p:nvPr')
 pr=child(sp,'p:spPr');xf=child(pr,'a:xfrm');child(xf,'a:off',x=round(x*914400),y=round(y*914400));child(xf,'a:ext',cx=round(w*914400),cy=0)
 geo=child(pr,'a:prstGeom',prst='line');child(geo,'a:avLst');line=child(pr,'a:ln',w='19050');f=child(line,'a:solidFill');child(f,'a:srgbClr',val='D6E1E5');child(line,'a:tailEnd',type='triangle',w='med',len='med');return sp
def notes(tree,text):
 candidates=tree.xpath('.//p:sp[p:nvSpPr/p:nvPr/p:ph[@type="body"]]',namespaces=NS);assert len(candidates)==1;settext(candidates[0],text,11,'000000',False)
with zipfile.ZipFile(SRC) as z:parts={n:z.read(n) for n in z.namelist()}
trees={n:E.fromstring(parts[f'ppt/slides/slide{n}.xml']) for n in [2,6,13,15]}
# 2: Preserve the illustrative complaint and the service chain, then quantify
# historical delivery delay without presenting it as current complaint volume.
s=trees[2];sp=shape(s,24);settext(sp,'Service breaks when facts or context fail to reach the decision-maker.',16.5,'152E3D',False);bounds(sp,y=5.89,h=.30)
st=s.find('p:cSld/p:spTree',NS)
st.append(textshape(70,'Historical sample: 546,364 non-prebooked orders; 14.8% late; 1.4% >10 min.',.688,6.23,11.95,.31,17.25,'152E3D',True))
st.append(textshape(71,'Meituan INFORMS TSL, 17–24 Oct 2022; delivery-delay shares, not complaint rates.\nThis research was supported by data provided by Meituan.',.688,6.58,11.95,.28,10.25,'587184'))
# 6: Practical model-selection rationale backed by existing implementation,
# developer cost reports and owner-selected, fixed-config evaluation logs.
s=trees[6];settext(shape(s,37),'Demo: DeepSeek Flash — low-cost model already integrated with order tools.\nFormal: GPT-5.6 Sol — available API with native tool calls and per-request usage logs.',15.0,'FFFFFF',False);bounds(shape(s,37),y=6.055,h=.49)
# 13: Keep all observed failure counts, add a proposed, gated three-stage plan.
s=trees[13];st=s.find('p:cSld/p:spTree',NS)
for node in list(st):
 if node.tag in [q('p:nvGrpSpPr'),q('p:grpSpPr')]:continue
 idnode=node.find('.//p:cNvPr',NS)
 if idnode is not None and int(idnode.get('id')) not in [2,3,4,5,6]:st.remove(node)
settext(shape(s,3),'Priorities and proposed rollout',36.0,'FFFFFF',True)
st.append(textshape(70,'Fix observed failures first · 120 real-model trials on synthetic orders',.688,1.82,11.95,.38,17.25,'C5D4DD'))
for x,title,body in [(.688,'Repair explanations','B: 14 false blocks\n6 unclear next steps\n3 unwanted cards'),(4.969,'Validate promises','C: 6 unsupported\nreminder / relay promises'),(9.25,'Resolve policy','C: 9 goodwill cases pending\nRetest affected paths')]:
 idx=80+int(x*3)
 st.append(textshape(idx,title,x,2.44,3.40,.38,20.25,'FFFFFF',True));st.append(textshape(idx+1,body,x,2.96,3.40,.82,17.25,'D8E2E8'))
st.append(textshape(125,'PROPOSED ROLLOUT · FUTURE STAGES AND RELEASE GATES',.688,3.94,11.95,.30,12.75,'F6C34C',True))
nodes=[(.688,'1  Shadow mode','Read-only suggestions;\nhumans decide.','Gate: policy decided;\naffected paths pass.'),(4.969,'2  Limited pilot','Few real orders;\nhuman approval retained.','Gate: no wrong / duplicate\nissues; review checks pass.'),(9.25,'3  Gradual scale','Increase volume;\nmonitor and roll back.','Gate: positive local cost case;\nnet time saved after\nreview and rework.')]
for i,(x,title,body,gate) in enumerate(nodes):
 base=150+i*10;st.append(rect(base,x,4.39,3.40,2.05));st.append(textshape(base+1,title,x+.16,4.55,3.08,.35,19.5,'FFFFFF',True));st.append(textshape(base+2,body,x+.16,5.02,3.08,.48,14.25,'E0E8EC'));st.append(textshape(base+3,gate,x+.16,5.66,3.08,.65,14.25,'F6C34C'))
st.append(arrow(190,4.13,5.37,.63));st.append(arrow(191,8.41,5.37,.63))
st.append(textshape(200,'Later: e-commerce after-sales, with new connectors and revalidated policies.',.688,6.61,11.95,.25,13.5,'D8E2E8'))
# 15: User-confirmed aliases; match all six cover names, no student IDs repeated.
s=trees[15];settext(shape(s,22),'PAN Pan research + official terms',17.25,'587184',False)
frame=shape(s,35);bounds(frame,y=2.04,h=3.88)
table=frame.find('.//a:tbl',NS);rows=table.findall('a:tr',NS);header=copy.deepcopy(rows[0]);model=copy.deepcopy(rows[1])
for row in rows:table.remove(row)
header.set('h',str(round(.43*914400)))
for cell,text in zip(header.findall('a:tc',NS),['Work received','Contributor']):settext(cell,text,15.0,'FFFFFF',True)
table.append(header)
credits=[('Baseline specification, evaluation, slides','LI Binxiong'),('Prototype / B implementation,\ndeployment and demo recordings','LI Zongqian'),('Business, guarantees and cost research','PAN Pan'),('Earlier platform observations','LIN Jingkai'),('Existing trial / QA feedback','WU Yang'),('Trial feedback and presentation recording','Ko Anderson')]
for work,name in credits:
 row=copy.deepcopy(model);row.set('h',str(round(.575*914400)))
 for cell,text in zip(row.findall('a:tc',NS),[work,name]):
  settext(cell,text,14.25,'152E3D',False)
  pr=cell.find('a:tcPr',NS)
  if pr is not None:
   pr.set('marT','45720');pr.set('marB','22860');pr.set('marL','68580');pr.set('marR','45720');pr.set('anchor','ctr')
 table.append(row)
note_additions={
2:'V6 addition: The historical Meituan INFORMS TSL research sample covers 17–24 Oct 2022. Existing team aggregates keep one grabbed/delivered waybill per order with a promised time, then separate non-prebooked orders. N=546,364; share late_any=0.1478; share late_over_10min=0.0141. On-slide rounding is 14.8% and 1.4%. These are delivery-delay shares in that research sample, not 2026 platform complaint rates or measured financial losses. No raw data is redistributed. Source: https://github.com/meituan/Meituan-INFORMS-TSL-Research-Challenge ; work/data/meituan_lateness_stats.json and .py. Required attribution: This research was supported by data provided by Meituan.',
6:'V6 addition: Model selection is explained as a practical study choice: use the already-working DeepSeek tool-calling implementation for the demo, with developer-reported low development/demo cost; formal runs use the owner-selected GPT-5.6 API with the same settings for B and C and preserved request/usage logs. This does not claim a pre-run latency/stability competition or that either model beat alternative models. Existing formal configuration and measured results remain unchanged.',
13:'V6 addition: Proposed rollout only; no shadow run, real-order pilot or expansion has been executed. First resolve the pending goodwill policy, fix the observed explanation/intent/promise defects and pass affected regression paths. Shadow suggestions remain read-only and humans decide. A limited real-order pilot requires validated, authorized production interfaces; human approval remains on every issue. Advance only after no wrong/duplicate issues and reviewed safety checks in the pilot. Gradual scaling needs measured net time savings including review/rework, a positive local cost case and rollback/monitoring. No numerical pilot performance is asserted. Existing 14+6+3 B failures, C6 unsupported promises and C9 pending cases are retained. Later transfer to e-commerce requires new connectors and policy revalidation.',
15:'V6 identity mapping confirmed by the owner on 26 Nov 2026: Jacky=PAN Pan; gaga=Ko Anderson; A=WU Yang (the owner corrected an intermediate Chinese typo). LI Zongqian covers implementation/deployment/demo captures; LIN Jingkai covers earlier platform observations; LI Binxiong covers baseline specification, evaluation evidence and slide integration. Credits record received work, not peer-evaluation scores or claims that every member independently verified all results. Ko Anderson is credited with the group presentation recording under the owner-confirmed single-recorder arrangement. The cover names and student IDs are unchanged.'}
# Keep editing history in edits.json, not in the presentation's spoken notes.
clean_notes={
2:'A late-delivery complaint needs an identified order, verified ownership and timing, and enough context for human review. The historical Meituan INFORMS TSL research sample covers 17–24 Oct 2022. Team aggregates contain 546,364 non-prebooked delivered orders with a promised time. 14.78% were late and 1.41% were more than 10 minutes late, shown as 14.8% and 1.4%. These figures describe delivery delay in a historical research sample, not complaint rates or current platform-wide performance.\n\nSource: https://github.com/meituan/Meituan-INFORMS-TSL-Research-Challenge ; team aggregates work/data/meituan_lateness_stats.json. Lateness is actual arrival minus promised arrival; one delivered waybill is retained per order.\nThis research was supported by data provided by Meituan.',
6:'LangChain connects model and tools; LangGraph manages state and human waits. The demo reuses the working DeepSeek Flash tool-calling implementation at low reported development/demo cost (developer estimate CNY1–5). Formal B/C runs use the owner-selected GPT-5.6 Sol API with identical settings, complete response/usage logs and fixed code 176fbb0. Formal settings: reasoning none, temperature 0.35, 800 output tokens, 30-second timeout, zero retries; automatic approval disabled. C also has intent handling, order-number fallback and food-safety preprocessing, so results compare configured systems.\n\nSource: examples/ord001/evidence/gpt56-formal-20261123/profile.json and the developer runtime/cost intake. No cross-model selection benchmark was performed.',
13:'The proposed rollout follows repairs to the observed defects: B has 14 amount-mention false blocks, 6 unclear next steps and 3 unwanted confirmation cards; C has 6 unsupported reminder/relay promises and 9 goodwill-policy cases pending. Resolve the policy and retest affected paths first.\n\nStage 1, shadow mode: produce read-only suggestions while humans decide. Release gate: the pending policy is decided and affected regression paths pass.\nStage 2, limited pilot: use a small set of authorized real orders only after production interfaces are validated; human approval remains required. Release gate: no wrong or duplicate issues in the pilot and human review checks pass.\nStage 3, gradual scaling: increase volume with monitoring and rollback. Release gate: measured net time savings after review/rework and a positive value case under local costs.\n\nThese are proposed future stages. Later e-commerce transfer needs new connectors and revalidated policies. Source: work/eval/gpt56-complete-review-2026-11-23.md; rollout gates are project recommendations.',
15:'Contributions: LI Binxiong — baseline specification, evaluation evidence and slide integration. LI Zongqian — prototype and B implementation, deployment and demo recordings. PAN Pan — business, guarantees and cost research. LIN Jingkai — earlier platform observations. WU Yang — existing trial and QA feedback. Ko Anderson — trial feedback and the recorded presentation.\n\nSources: PAN Pan business/guarantee/cost research and official terms; 120 formal records and complete-treatment-v1; team platform observations dated 11 Nov 2026; BLS wage data and supplier pricing; Meituan INFORMS TSL historical delivery data.\nCustomer demo: https://ord001-group24.surge.sh/\nReview console: https://ord001-group24.surge.sh/review'}
changed=[]
for n,tree in trees.items():parts[f'ppt/slides/slide{n}.xml']=E.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True);changed.append(f'ppt/slides/slide{n}.xml')
for n,add in note_additions.items():
 path=f'ppt/notesSlides/notesSlide{n}.xml';tree=E.fromstring(parts[path]);notes(tree,clean_notes[n]);parts[path]=E.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True);changed.append(path)
with zipfile.ZipFile(DEST,'w',zipfile.ZIP_DEFLATED) as z:
 for name,data in parts.items():z.writestr(name,data)
with zipfile.ZipFile(SRC) as z0,zipfile.ZipFile(DEST) as z1:
 actual=[n for n in z1.namelist() if z0.read(n)!=z1.read(n)]
 assert set(actual)==set(changed)
 media={n:hashlib.sha256(z1.read(n)).hexdigest() for n in z1.namelist() if n.endswith('.mp4')}
 assert all(z0.read(n)==z1.read(n) for n in media)
(O/'edits.json').write_text(json.dumps({'changed_package_parts':actual,'media_unchanged':media,'credit_rows':credits,'owner_alias_confirmation':'Jacky=PAN Pan; gaga=Ko Anderson; A=WU Yang; typo corrected by owner','slides_modified':[2,6,13,15],'author_source_notes':note_additions},ensure_ascii=False,indent=2)+'\n','utf-8')
print(DEST)
