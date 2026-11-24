from pathlib import Path
import json,win32com.client
S=Path(__file__).parent;O=S/'candidate';out=O/'preview';out.mkdir(exist_ok=True)
pp=win32com.client.DispatchEx('PowerPoint.Application');p=pp.Presentations.Open(str(O/'IS5542-Group24-v4.pptx'),True,False,False)
inventory=[]
try:
 for s in p.Slides:
  s.Export(str(out/f'slide-{s.SlideIndex:02d}.png'),'PNG',1280,720)
  inventory.append({'slide':s.SlideIndex,'shapes':s.Shapes.Count,'media':sum(q.Type==16 for q in s.Shapes),'tables':sum(bool(q.HasTable) for q in s.Shapes)})
 p.SaveAs(str(O/'IS5542-Group24-v4.pdf'),32)
finally:
 p.Close()
 if pp.Presentations.Count==0:pp.Quit()
(S/'render-inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8');print('Rendered',len(inventory),'slides')
