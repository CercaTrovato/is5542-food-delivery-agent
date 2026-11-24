from pathlib import Path
import win32com.client,json
S=Path(__file__).parent;out=S/'candidate';renders=out/'preview';renders.mkdir(exist_ok=True)
ppt=out/'IS5542-Group24-REVIEW-v3.pptx'
pp=win32com.client.DispatchEx('PowerPoint.Application');p=pp.Presentations.Open(str(ppt),True,False,False)
inv=[]
try:
 for s in p.Slides:
  s.Export(str(renders/f'slide-{s.SlideIndex:02d}.png'),'PNG',1280,720)
  sh=[]
  for q in s.Shapes:
   item={'id':q.Id,'name':q.Name,'type':q.Type,'x':round(q.Left/.75,2),'y':round(q.Top/.75,2),'width':round(q.Width/.75,2),'height':round(q.Height/.75,2)}
   if q.HasTextFrame and q.TextFrame.HasText:item['text']=q.TextFrame.TextRange.Text
   if q.HasTable:item['table']=[[q.Table.Cell(r,c).Shape.TextFrame.TextRange.Text for c in range(1,q.Table.Columns.Count+1)] for r in range(1,q.Table.Rows.Count+1)]
   if q.Type==16:item['media_length_ms']=q.MediaFormat.Length
   sh.append(item)
  inv.append({'slide':s.SlideIndex,'shapes':sh})
 p.SaveAs(str(out/'IS5542-Group24-REVIEW-v3.pdf'),32)
finally:p.Close();pp.Quit()
(S/'slide-inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2),encoding='utf-8')
print('Rendered',len(inv),'slides and PDF')
print('Media:',[(s['slide'],q['media_length_ms']) for s in inv for q in s['shapes'] if 'media_length_ms' in q])
