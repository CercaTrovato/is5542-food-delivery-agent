from pathlib import Path
import json,zipfile,hashlib,shutil,sys,subprocess
from xml.etree import ElementTree as E
S=Path(__file__).parent;A=Path('D:/上课资料/CityU/IS5542_GenAI_in_Business/assignment/graded/A01-genai-project');R=Path('E:/app-data/codex/scratchpad/is5542-final-ppt-20261124/repo');O=S/'candidate';O.mkdir(exist_ok=True)
sys.path.insert(0,'D:/上课资料/CityU/_meta/tools');import integrity_check
integrity_check.ROOT=str(A);integrity_check.MANIFEST=str(S/'integrity-manifest.json')
try:integrity_check.snapshot('is5542-cover-roster-20261126')
except ValueError as e:
 if 'mount' not in str(e):raise
files=[A/n for n in ['assignment.json','coordination.json','timeline.json','notes/supervision-report.md']]+[R/n for n in ['progress/assignment.json','progress/coordination.json','progress/timeline.json','progress/daily-plan.json','notes/supervision-report.md','notes/current-plan.md','TIMELINE.md','work/presentation/README.md']]
baseline={};(S/'baselines').mkdir(exist_ok=True)
for i,p in enumerate(files):
 b=p.read_bytes();q=S/'baselines'/f'{i:02d}-{p.name}';q.write_bytes(b);baseline[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'backup':str(q)}
(S/'baseline.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2),encoding='utf-8')
src=A/'submission/IS5542-Group24-v4.pptx';dst=O/'IS5542-Group24-v5.pptx';assert hashlib.sha256(src.read_bytes()).hexdigest()=='914088e104f6c4fd45a9f9076d90a5decd3b1783c44e5a4b355feca686b24a6a';shutil.copy2(src,dst)
members=[['李宾雄','LI Binxiong','60234350'],['李宗谦','LI Zongqian','60582017'],['吴阳','WU Yang','60114989'],['林敬凯','LIN Jingkai','60835535'],['高鎧宏','Ko Anderson','60310560'],['潘攀','PAN Pan','60621441']]
(S/'members.json').write_text(json.dumps({'source':'User supplied all six names and student IDs on 2026-11-26; Ko Anderson retained as supplied. Other names rendered in Hanyu Pinyin, surname first.','members':members},ensure_ascii=False,indent=2),encoding='utf-8')
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with zipfile.ZipFile(src) as z:root=E.fromstring(z.read('ppt/slides/slide1.xml'))
shapes=[]
for s in root.findall('.//p:sp',ns):
 ident=s.find('p:nvSpPr/p:cNvPr',ns);text='\n'.join(''.join(t.text or '' for t in p.findall('.//a:t',ns)) for p in s.findall('.//a:p',ns));shapes.append((ident.get('id'),text))
ops=[]
def settext(match,props):
 sid=next(i for i,t in shapes if match in t);ops.append({'command':'set','path':f'/slide[1]/shape[@id={sid}]','props':props})
settext('Food Delivery',{'x':'64px','y':'118px','width':'500px','height':'200px','size':'42pt'})
settext('Correct and safe handling',{'x':'66px','y':'331px','width':'500px','height':'62px','size':'19pt'})
settext('Simulated orders and coupons',{'x':'66px','y':'402px','width':'500px','height':'25px','size':'14pt'})
# Reposition the existing zero-height horizontal divider, stored as a regular shape.
for q in root.findall('.//p:sp',ns):
 ext=q.find('.//a:xfrm/a:ext',ns)
 if ext is not None and ext.get('cy')=='0' and not q.findall('.//a:t',ns):
  sid=q.find('p:nvSpPr/p:cNvPr',ns).get('id');ops.append({'command':'set','path':f'/slide[1]/shape[@id={sid}]','props':{'y':'442px'}})
def add(text,x,y,w,h,size,color,name):ops.append({'command':'add','path':'/slide[1]','type':'shape','props':{'name':name,'text':text,'x':f'{x}px','y':f'{y}px','width':f'{w}px','height':f'{h}px','font':'Arial','size':f'{size}pt','color':color,'fill':'none','line':'none','valign':'middle','margin':'0pt','autoFit':'none','spaceBefore':'0pt','spaceAfter':'0pt','lineSpacing':'1x'}})
add('GROUP MEMBERS',66,454,280,23,12.75,'FFBD45','Roster header')
add('STUDENT ID',370,454,180,23,12.75,'D9E5EC','Student ID header')
for i,(_,name,sid) in enumerate(members):
 y=486+i*31;add(name,66,y,280,30,18,'FFFFFF',f'Member {i+1} name');add(sid,370,y,180,30,18,'D9E5EC',f'Member {i+1} ID')
(S/'cover-update.json').write_text(json.dumps(ops,ensure_ascii=False,indent=2),encoding='utf-8')
subprocess.run(['officecli','open',str(dst)],check=True)
subprocess.run(['officecli','batch',str(dst),'--input',str(S/'cover-update.json'),'--stop-on-error','--json'],check=True)
subprocess.run(['officecli','close',str(dst)],check=True)
# OfficeCLI normalizes shared XML parts while saving. Retain the requested
# slide1 edit and restore all other parts byte-for-byte from the v4 source.
with zipfile.ZipFile(dst) as made:cover_xml=made.read('ppt/slides/slide1.xml')
tmp=dst.with_name(dst.name+'.scope-preserved')
with zipfile.ZipFile(src) as old,zipfile.ZipFile(tmp,'w') as clean:
 for part in old.infolist():clean.writestr(part,cover_xml if part.filename=='ppt/slides/slide1.xml' else old.read(part.filename))
tmp.replace(dst)
print(dst)
