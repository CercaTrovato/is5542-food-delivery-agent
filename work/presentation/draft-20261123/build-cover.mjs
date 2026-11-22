export async function buildCover({presentation}) {
  // A new Spaces presentation may contain one empty starter slide.
  for(const s of [...presentation.slides.items])if(s.shapes.items.length===0&&s.tables.items.length===0)presentation.slides.delete(s.id);
  const s=presentation.slides.add({width:1280,height:720});s.background.fill='#FFF9ED';
  function t(text,x,y,w,h,size,color){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=text;a.text.style={fontFamily:'Arial',fontSize:size,color};return a;}
  t('IS5542   /   GROUP 24   /   DRAFT',72,58,1100,40,20,'#8A641C');
  t('Food Delivery\nComplaint Assistant',72,172,1136,180,64,'#262723');
  t('Correct and safe handling of complex complaints',76,385,1050,70,32,'#575A51');
  t('Course prototype with simulated orders and coupons',76,592,1080,36,21,'#62665D');
  t('Members: [official English names and student IDs]',76,642,1080,30,18,'#777B71');
  return {slideCount:presentation.slides.items.length};
}
