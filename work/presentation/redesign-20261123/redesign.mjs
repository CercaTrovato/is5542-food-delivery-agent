// Execute within the existing Spaces Artifact Session, preserving the 15 slide IDs.
export async function redesign({presentation,input}) {
 const C={navy:'#132432',navy2:'#203B4C',ink:'#142A38',muted:'#627584',line:'#D7E1E7',paper:'#F7F9FA',white:'#FFFFFF',gold:'#FFBD45',pale:'#FFF0CF',blue:'#E8F0F5',light:'#D9E5EC'};
 const H='Bahnschrift', B='Calibri';
 const T=(s,v,x,y,w,h,z=28,color=C.ink,bold=false)=>{const a=s.shapes.add({geometry:'textbox',name:v.slice(0,65),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=v;a.text.insets=0;a.text.style={fontFamily:bold?H:B,fontSize:z,color,bold,verticalAlignment:'middle'};return a;};
 const R=(s,x,y,w,h,fill,line='none',radius=0)=>s.shapes.add({geometry:radius?'roundRect':'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:line==='none'?0:1.3},borderRadius:radius});
 const L=(s,x,y,w,color=C.line)=>s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:0},fill:'none',line:{fill:color,width:1.3}});
 const V=(s,x,y,h,color=C.line)=>s.shapes.add({geometry:'line',position:{left:x,top:y,width:0,height:h},fill:'none',line:{fill:color,width:1.3}});
 const I=(s,name,x,y,size=48,color=C.ink)=>s.images.add({path:input.assetRoot+'/icons-png/'+name+'-'+(color===C.gold?'gold':'ink')+'.png',alt:'Lucide '+name+' icon',fit:'contain',position:{left:x,top:y,width:size,height:size}});
 const A=(s,from,to,fs='right',ts='left',color=C.muted,kind='straight')=>s.shapes.connect(from,to,{kind,fromSide:fs,toSide:ts,line:{fill:color,width:2.5},tail:{type:'triangle',width:'med',length:'med'}});
 const N=(s,title,x,y,w,h=100,fill=C.white,icon=null,z=27)=>{const box=R(s,x,y,w,h,fill,C.line,10);if(icon){I(s,icon,x+18,y+(h-36)/2,36);T(s,title,x+70,y+10,w-86,h-20,z);}else{const q=T(s,title,x+16,y+8,w-32,h-16,z);q.text.style={fontFamily:B,fontSize:z,color:C.ink,alignment:'center',verticalAlignment:'middle'};}return box;};
 const tab=(s,values,x,y,width,widths,heights,z=24)=>{const a=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width,height:heights.reduce((a,b)=>a+b,0),values,columnWidths:widths});a.styleOptions={headerRow:false,bandedRows:false};a.borders.assign({fill:C.line,width:1});a.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({margins:{left:15,right:15,top:6,bottom:6},textStyle:{fontFamily:B,fontSize:z,color:C.ink,bold:false},anchor:'center'});for(let r=0;r<values.length;r++){a.rows[r].height=heights[r];for(let c=0;c<values[0].length;c++){const cell=a.getCell(r,c);cell.fill=r===0?C.navy:(r%2?C.white:C.paper);cell.text.style={fontFamily:B,fontSize:z,color:r===0?C.white:C.ink,bold:false};}}return a;};
 function base(n,title,chapter,dark=false){const s=presentation.slides.getItem(n-1);for(const a of [...s.shapes.items])a.delete();for(const a of [...s.images.items])a.delete();for(const a of [...s.tables.items])presentation.delete(a.toSnapshot().aid);s.background.fill=dark?C.navy:C.paper;T(s,chapter.toUpperCase(),64,29,1100,29,18,dark?C.gold:C.muted,true);T(s,title,64,73,1152,83,54,dark?C.white:C.ink,true);L(s,64,666,1152,dark?'#4C6271':C.line);T(s,'IS5542  /  GROUP 24  /  DRAFT',64,680,900,22,15,dark?C.light:C.muted);T(s,String(n).padStart(2,'0'),1177,680,40,22,15,dark?C.light:C.muted);return s;}
 for(const n of input.slides){let s;
  if(n===1){
   s=base(n,'','Course project',true);for(const a of [...s.shapes.items])a.delete();
   s.images.add({path:input.hero,fit:'cover',alt:'AI-generated illustrative scene of unbranded takeaway packaging and a phone. Not application evidence.',position:{left:0,top:0,width:1280,height:720}});
   R(s,0,0,605,720,C.navy);T(s,'IS5542  /  GROUP 24',64,53,500,40,23,C.gold,true);
   T(s,'Food Delivery\nComplaint\nAssistant',62,159,541,257,68,C.white,true);
   T(s,'Correct and safe handling\nof complex complaints',66,452,480,92,31,C.light);
   L(s,66,589,463,'#557080');T(s,'Simulated orders and coupons',66,607,480,37,23,C.white);
   T(s,'DRAFT  ·  Member details pending',66,658,480,30,19,C.light);
   s.speakerNotes.append('\nVisual: OpenAI ImageGen, created 23 Nov 2026. Illustrative restaurant still life, not a photograph of the team or operational evidence.');
  }
  if(n===2){
   s=base(n,'The anatomy of a complaint','01  Business problem');
   T(s,'“My order is late. Can I claim compensation?”',66,179,1140,62,36,C.ink);
   T(s,'Illustrative complaint from team research',66,243,1148,27,19,C.muted);
   const a=N(s,'Customer\nquestion',80,297,255,122,C.white,'user-round',30);
   const b=N(s,'Verified\norder facts',511,297,255,122,C.pale,'receipt-text',30);
   const c=N(s,'Accountable\nreview',942,297,255,122,C.white,'headset',30);
   A(s,a,b);A(s,b,c);
   T(s,'Which order?',350,268,155,35,23,C.muted);T(s,'Which benefit?',782,268,175,35,23,C.muted);
   T(s,'A clear explanation\nand a next step',80,455,285,98,28);
   T(s,'Ownership, timing,\npayment and history',511,455,315,98,28);
   T(s,'Enough context\nto decide and respond',942,455,285,98,28);
   T(s,'Service breaks when facts or context fail to reach the person making the decision.',66,601,1147,48,28,C.ink);
  }
  if(n===3){
   s=base(n,'Different guarantees, different conditions','01  Market context');
   T(s,'Guarantee versions reported in team research',66,174,1136,42,26,C.muted);
   const rows=[['Meituan','Standard','Black Gold','Entitlement +\ndelivery promise'],['Taobao Instant\nCommerce','Merchant-gifted','Purchased by\ncustomer','Applicable service +\ntiming rule'],['JD Food Delivery','Specified-label promotion',null,'Order label +\nlatest arrival estimate']];
   rows.forEach((r,i)=>{let y=244+i*119;I(s,'receipt-text',67,y+20,43);T(s,r[0],128,y,258,91,29,C.ink,true);const q=N(s,r[1],427,y+9,r[2]?232:500,72,C.white,null,25);if(r[2])N(s,r[2],695,y+9,232,72,C.white,null,25);T(s,r[3],963,y+8,257,81,25);if(i<2)L(s,66,y+105,1148);});
   T(s,'Identify the order’s guarantee before explaining eligibility.',66,615,1148,40,30,C.ink,true);
   s.speakerNotes.append('\nVisual structure groups guarantee variants without adding official policy certification or merging their amounts.');
  }
  if(n===4){
   s=base(n,'Complaint handling workflow','02  Proposed service');
   const xs=[66,466,866];['MODEL + TRUSTED TOOLS','PROGRAM + CUSTOMER','HUMAN + ACTUAL STATE'].forEach((v,i)=>T(s,v,xs[i],184,350,37,22,C.muted,true));
   V(s,433,222,335);V(s,833,222,335);
   const a=N(s,'1  Understand\n    the complaint',80,246,326,106,C.white,'bot');
   const b=N(s,'2  Verify order\n    ownership and facts',80,426,326,106,C.white,'database',25);
   const c=N(s,'3  Evaluate\n    the delay rule',480,426,326,106,C.pale,'workflow');
   const d=N(s,'4  Customer\n    confirms submission',480,246,326,106,C.pale,'circle-check',25);
   const e=N(s,'5  Human\n    reviews the ticket',880,246,326,106,C.white,'headset',26);
   const f=N(s,'6  Read the\n    actual ticket status',880,426,326,106,C.white,'clipboard-list',25);
   A(s,a,b,'bottom','top');A(s,b,c);A(s,c,d,'top','bottom');A(s,d,e);A(s,e,f,'bottom','top');
   I(s,'git-branch',68,589,40);T(s,'Missing facts or a dispute: explain the reason, preserve context and route to human service.',127,581,1085,66,27);
  }
  if(n===5){
   s=base(n,'Verified data before compensation','02  Data and policy');
   I(s,'database',67,201,49);T(s,'Trusted inputs',134,199,430,58,32,C.ink,true);
   const rows=[['Order owner / status','Access and delivery'],['Expected / actual time','Delay calculation'],['Paid amount','Amount ceiling'],['Ticket / dialogue history','Context and current state']];
   rows.forEach((r,i)=>{const y=283+i*77;T(s,r[0],66,y,276,53,25,C.ink);T(s,r[1],355,y,235,53,25,C.muted);L(s,66,y+65,524);});
   V(s,632,206,393);
   T(s,'DEMO-V1',691,204,500,36,22,C.muted,true);T(s,'Delivered',691,253,490,52,34,C.ink,true);
   T(s,'> 30 min',688,315,505,103,76,C.ink,true);T(s,'Exactly 30 minutes does not qualify.',692,423,502,45,25,C.muted);
   I(s,'ticket',691,503,47);T(s,'10 yuan',758,491,428,63,47,C.ink,true);T(s,'Standard simulated coupon',758,557,445,42,25,C.muted);
   T(s,'Confirmation + human approval. Payment caps every issue; an invalid amount blocks issue.',66,616,1146,38,25,C.ink);
  }
  if(n===6){
   s=base(n,'A controlled agent architecture','02  Technical design',true);
   T(s,'LangChain: model and tool connection',66,173,1136,38,24,C.light);
   function dn(title,sub,icon,x,y){const q=R(s,x,y,326,137,C.navy2,'#587080',10);I(s,icon,x+20,y+23,39,C.gold);T(s,title,x+76,y+16,235,45,29,C.white,true);T(s,sub,x+20,y+75,287,52,25,C.light);return q;}
   const a=dn('Language model','Understands and explains','bot',66,238);
   const b=dn('Order tools','Retrieve authorized facts','database',477,238);
   const c=dn('Policy check','Rules and confirmation','workflow',888,238);
   const d=dn('Ticket store','Persist the order-level state','ticket',888,434);
   const e=dn('Human reviewer','Record approval or reason','headset',477,434);
   const f=dn('Customer reply','Display the actual outcome','message-square',66,434);
   A(s,a,b,'right','left',C.gold);A(s,b,c,'right','left',C.gold);A(s,c,d,'bottom','top',C.gold);A(s,d,e,'left','right',C.gold);A(s,e,f,'left','right',C.gold);
   T(s,'LangGraph: branches, saved state and human waits',66,590,1148,41,27,C.white,true);
   T(s,'Reported: openai:deepseek-flash / live. Model configuration and new review guards await validation.',66,635,1148,28,21,C.light);
  }
  if(n===7){
   s=base(n,'ORD001: the complete service journey','03  Demonstration');
   R(s,66,202,807,392,C.navy);I(s,'circle-play',414,312,90,C.gold);T(s,'Verified recording pending',160,439,620,55,34,C.white,true);
   T(s,'Query the same order. Follow the same ticket.',127,511,684,46,25,C.light);
   const stages=[['01','Query order'],['02','Confirm request'],['03','Pending review'],['04','Human approval'],['05','Actual status']];
   V(s,935,246,286,C.line);stages.forEach((r,i)=>{let y=211+i*75;R(s,908,y+9,53,46,C.paper);T(s,r[0],917,y+9,50,40,27,C.muted,true);T(s,r[1],983,y,235,64,28,C.ink,true);});
   T(s,'Run version  __________       Model  __________       Capture date  __________',66,619,1148,41,24,C.muted);
  }
  if(n===8){
   s=base(n,'Human review with explicit boundaries','03  Exception handling');
   const a=N(s,'Rejected, with no\ncompensation issued',66,207,449,91,C.white,'ticket',27);
   const b=N(s,'Verifiable new facts\nor a prior processing error',66,337,449,91,C.pale,'search',26);
   const c=N(s,'Human reason recorded\non the original ticket',66,467,449,91,C.white,'clipboard-list',26);
   A(s,a,b,'bottom','top');A(s,b,c,'bottom','top');
   R(s,574,207,640,351,C.navy);I(s,'circle-play',850,300,82,C.gold);T(s,'Reconsideration capture pending',623,426,550,48,29,C.white,true);
   I(s,'shield-check',67,603,38);T(s,'R002 only',118,598,212,47,26,C.ink,true);I(s,'banknote',368,603,38);T(s,'1–20 whole yuan, within payment',420,598,445,47,25,C.ink);I(s,'lock-keyhole',912,603,38);T(s,'Once per order',963,598,251,47,26,C.ink,true);
  }
  if(n===9){
   s=base(n,'A fair test of decision methods','04  Evaluation design');
   T(s,'Same model, authorized facts, tools and test cases',66,174,1148,49,30,C.ink,true);
   const common=N(s,'Shared scenario set',459,241,360,67,C.pale,'clipboard-list',27);
   const b=R(s,88,360,480,145,C.white,C.line,10);I(s,'bot',109,382,42);T(s,'B   Basic tool agent',171,372,375,49,31,C.ink,true);
   const c=R(s,711,360,480,145,C.white,C.line,10);I(s,'workflow',732,382,42);T(s,'C   Explicit-rule agent',794,372,375,49,31,C.ink,true);
   A(s,common,b,'left','top',C.muted,'elbow');A(s,common,c,'right','top',C.muted,'elbow');
   T(s,'Model reasons over the policy',112,438,443,45,27,C.muted);T(s,'Program evaluates the policy',734,438,443,45,27,C.muted);
   const guard=N(s,'Shared execution guards, confirmation and human review',159,547,960,64,C.pale,'shield-check',27);
   A(s,b,guard,'bottom','top',C.muted,'elbow');A(s,c,guard,'bottom','top',C.muted,'elbow');
   T(s,'PLAN  10 scenarios × 2 modes × 3 repeats = 60 system runs',66,626,1148,35,27,C.ink,true);
  }
  if(n===10){
   s=base(n,'Internal evaluation results','04  Evidence pending');
   I(s,'list-checks',66,179,40);T(s,'Matched runs and version-bound retests will populate this table.',124,170,1090,53,27,C.muted);
   tab(s,[['Metric','Agent B','Agent C','Evidence'],['Correct handling (k/N)','','',''],['Unsafe proposals (k/N)','','',''],['Incorrect executed actions (k/N)','','',''],['Repeat consistency (k/G)','','',''],['System time (seconds)','','',''],['Model cost (currency/run)','','','']],66,234,1148,[524,176,176,272],[46,42,42,42,42,42,42],25);
   tab(s,[['Retest area','Version','Result','Evidence'],['Review guards / handoff / order isolation','','','']],66,546,1148,[524,176,176,272],[42,66],24);
  }
  if(n===11){
   s=base(n,'Market comparison','04  Comparable evidence pending');
   tab(s,[['Service','Order\nselection','Eligibility\nexplanation','Human service\n/ status'],['Meituan','','',''],['Taobao Instant\nCommerce','','',''],['JD Food Delivery','','',''],['Our prototype','','','']],66,216,869,[260,180,200,229],[78,79,90,79,79],25);
   I(s,'scan-eye',990,218,49);T(s,'Each finding\nneeds context',984,288,230,89,31,C.ink,true);
   T(s,'Evidence type\n\nDate + order conditions\n\nObserved limits',985,411,231,213,26,C.muted);
  }
  if(n===12){
   s=base(n,'Value hypotheses and cost inputs','04  Business value');
   T(s,'VALUE TO TEST',66,182,500,36,21,C.muted,true);
   const a=N(s,'Correct handling\nand safe actions',66,244,496,94,C.pale,'shield-check',30);
   const b=N(s,'Less repeated explanation\nand better handoffs',66,385,496,94,C.white,'headset',28);A(s,a,b,'bottom','top');
   T(s,'Potential reduction in handling effort',66,499,496,69,27,C.muted);
   T(s,'12-MONTH VALUE INPUTS',657,182,556,36,21,C.muted,true);
   tab(s,[['Input','Value / source'],['Attributed benefits',''],['Model + service operation',''],['Human review + maintenance',''],['Setup + integration','']],657,244,557,[367,190],[48,62,62,62,62],24);
   R(s,66,583,1148,74,C.navy);T(s,'ROI =',89,602,100,39,28,C.white,true);T(s,'Benefits − operating costs − setup cost',228,589,935,29,24,C.white);L(s,228,622,921,'#A8BDCB');T(s,'Operating costs + setup cost',228,628,935,27,24,C.white);
  }
  if(n===13){
   s=base(n,'Validation and next steps','05  Limitations and next steps',true);
   I(s,'package-check',67,179,44,C.gold);T(s,'Current scope: simulated orders and coupons. New guards await acceptance.',130,173,1086,56,29,C.light);
   const phases=[['01','Freeze + retest','Code, model and policy\nAffected boundaries','lock-keyhole'],['02','Record + compare','Two real demo captures\nMatched B/C runs','circle-play'],['03','Assess value','Market evidence\nCost and time inputs','scale'],['LATER','Adapt + validate','New domain interfaces\nNew policy and tests','git-branch']];
   L(s,143,347,996,'#617A8B');phases.forEach((r,i)=>{let x=66+i*294;R(s,x+66,315,68,65,C.navy);I(s,r[3],x+77,326,45,C.gold);T(s,r[0],x,266,270,35,22,C.light,true);T(s,r[1],x,402,274,50,31,C.white,true);const b=T(s,r[2],x,482,274,104,27,C.light);b.text.style={fontFamily:B,fontSize:27,color:C.light,verticalAlignment:'top'};});
   T(s,'Broader application: e-commerce after-sales support',66,617,1148,39,27,C.white);
  }
  if(n===14){
   s=base(n,'Measurement definitions','Appendix A');
   tab(s,[['Measure','Definition','Evidence retained'],['Correct handling','Expected outcome met / scored runs','Input, expected result,\nfinal state'],['Unsafe proposals','Disallowed model proposal / scored runs','Raw output and\nproposed tool action'],['Executed errors','Incorrect action performed / scored runs','Tool log, ticket\nand issue record'],['Repeat consistency','Groups with 3 matching outcomes / completed groups','All repeats,\nincluding failures'],['Time and cost','System time per run. Human wait and billed usage recorded separately.','Timestamps, tokens\nand price source']],66,184,1148,[254,524,370],[48,76,76,76,82,92],25);
   T(s,'Run ID  ______       Code / model / policy  ______       Raw evidence  ______',66,637,1148,25,22,C.muted);
  }
  if(n===15){
   s=base(n,'Sources and team contributions','Appendix B');
   const sr=[['book-open','Business research','Jacky’s supplied material\n22 Nov 2026'],['shield-check','Confirmed demo rules','demo-v1 + human-review-v1\n23 Nov 2026'],['file-text','Code + teacher template','Source links in speaker notes']];
   sr.forEach((r,i)=>{let y=203+i*130;I(s,r[0],66,y+6,43);T(s,r[1],129,y,410,43,29,C.ink,true);T(s,r[2],129,y+51,410,66,25,C.muted);});
   tab(s,[['Work received','Identity to confirm'],['Business research','Jacky'],['Prototype code','Developer'],['Trial feedback','A + gaga'],['Earlier market observations','Lin'],['Synthesis and slides','Name / ID pending']],591,201,623,[362,261],[48,53,53,53,64,53],24);
   T(s,'Official names, IDs and contribution wording pending',591,548,623,62,24,C.muted);
   T(s,'I used OpenAI Codex to assist with this assignment.',66,620,1148,35,25,C.ink);
  }
  if(n!==1)s.speakerNotes.append('\nVisual assets: Lucide official icons (ISC license), https://lucide.dev/icons/ . Retrieved 23 Nov 2026.');
 }
 return {updated:input.slides,slideCount:presentation.slides.items.length};
}
