// Source for the saved Spaces deck. Run this callback in Artifact Session.
// No model calls, application tests, or generated measurement data.
export async function buildBatch({ presentation, input }) {
  const C={bg:'#FFFDF7',ink:'#292D27',muted:'#62685F',gold:'#D49B25',pale:'#FFF0BD',line:'#D7DCCE',green:'#E7EEE3',dark:'#344437'};
  const base='https://github.com/CercaTrovato/is5542-food-delivery-agent/blob/';
  const doc=base+'c666f1daba06bfdce577f32f1959e0e8d6ba3240/';
  const code=base+'29171c8c42671e3de84f2f0940a85867fa98ce1a/';
  function text(s,str,x,y,w,h,size=26,color=C.ink,bold=false){
    const a=s.shapes.add({geometry:'textbox',name:str.slice(0,48),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
    a.text=str;a.text.insets=0;a.text.style={fontFamily:'Arial',fontSize:size,color,bold,verticalAlignment:'middle'};return a;
  }
  function line(s,x,y,w,color=C.line){return s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:0},fill:'none',line:{fill:color,width:1.4,style:'solid'}});}
  function node(s,str,x,y,w=170,h=104,fill=C.pale,size=24){const a=s.shapes.add({geometry:'roundRect',name:str.replaceAll('\n',' '),position:{left:x,top:y,width:w,height:h},fill,line:{fill:C.line,width:1},borderRadius:12});a.text=str;a.text.insets=12;a.text.style={fontFamily:'Arial',fontSize:size,color:C.ink,alignment:'center',verticalAlignment:'middle'};return a;}
  function arrow(s,a,b,from='right',to='left'){return s.shapes.connect(a,b,{kind:'straight',fromSide:from,toSide:to,line:{fill:'#7C886F',width:2.3},tail:{type:'triangle',width:'med',length:'med'}});}
  function table(s,values,x,y,width,heights,widths,size=24){
    const a=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width,height:heights.reduce((x,y)=>x+y,0),values,columnWidths:widths});
    a.styleOptions={headerRow:false,bandedRows:false};
    a.borders.assign({fill:C.line,width:1,style:'solid'});
    a.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({fill:C.bg,textStyle:{fontFamily:'Arial',fontSize:size,color:C.ink,bold:false},margins:{left:14,right:14,top:10,bottom:10},anchor:'center'});
    for(let r=0;r<values.length;r++){a.rows[r].height=heights[r];for(let c=0;c<values[0].length;c++){const cell=a.getCell(r,c);cell.fill=r===0?C.pale:C.bg;cell.text.style={fontFamily:'Arial',fontSize:size,color:C.ink,bold:false};}}
    return a;
  }
  function slide(n,title,sub=''){
    const s=presentation.slides.add({width:1280,height:720});s.background.fill=C.bg;
    text(s,title,64,48,1152,80,44,C.ink,true);
    if(sub)text(s,sub,66,134,1148,40,23,C.muted);
    text(s,'IS5542 Group 24 · DRAFT',66,674,650,23,16,C.muted);
    text(s,String(n).padStart(2,'0'),1163,674,53,23,16,C.muted);
    return s;
  }
  function notes(s,narrative,refs){s.speakerNotes.text=narrative+'\n\nSources:\n'+refs.join('\n');}
  if(input.removeEmpty){for(const s of [...presentation.slides.items])if(s.shapes.items.length===0&&s.tables.items.length===0)presentation.slides.delete(s.id);const s=presentation.slides.getItem(0);notes(s,'Our project focuses on correct and safe handling of complex delivery complaints. We use simulated orders and coupons in a course prototype. Official member names and student IDs remain to be confirmed.',[doc+'notes/current-plan.md',doc+'work/presentation/deck-plan.json']);}
  for(let n=input.from;n<=input.to;n++){
    let s;
    if(n===2){
      s=slide(n,'The complaint and the people affected');
      text(s,'“My order is late.\nCan I claim compensation?”',66,192,540,145,38,C.ink);
      text(s,'Illustrative request based on team research',66,347,540,35,18,C.muted);
      text(s,'Customer',683,192,500,42,29,C.dark,true);
      text(s,'Needs the right order, an explanation of eligibility and a clear next step.',683,244,500,106,27);
      text(s,'Customer service and reviewers',683,385,500,48,29,C.dark,true);
      text(s,'Need verified facts and the complaint history before making a decision.',683,444,500,105,27);
      line(s,66,584,1148);
      text(s,'The business task: connect a complaint to an accountable order-level outcome.',66,607,1148,45,27,C.dark);
      notes(s,'A delay complaint can involve entitlement questions, missing information or a dispute. Jacky’s research distinguishes the customer’s request from the order facts and the compensation decision. We aim to reduce repeated explanations and preserve context, but we have not quantified those benefits.',[doc+'work/research/jacky-business-rules-2026-11-22.md']);
    }
    if(n===3){
      s=slide(n,'Current platform approaches','Guarantee versions described in Jacky’s team research');
      table(s,[['Platform','Guarantee variants','Order details that matter'],['Meituan','Standard and Black Gold\non-time guarantees','Entitlement, delivery promise\nand the applicable benefit'],['Taobao Instant Commerce','Merchant-gifted cover and\ncustomer-purchased cover','Which service applies and\nwhich timing rule it uses'],['JD Food Delivery','Promotion for orders carrying\na specified eligibility label','Order label and the\nlatest estimated arrival time']],66,199,1148,[54,100,100,100],[240,440,468],25);
      text(s,'Design implication: identify the applicable guarantee before explaining eligibility.',66,583,1148,45,27,C.dark);
      text(s,'Source: team research, 22 Nov 2026. Primary-source locators are pending.',66,638,1148,25,18,C.muted);
      notes(s,'This page summarizes the distinctions reported in Jacky’s supplied research. It does not certify current platform terms. The five source rows describe separate guarantee versions. Exact amounts, boundary conditions and exclusions need their original official URL or screenshot locator before final use. The material does not establish a market performance ranking.',[doc+'work/research/jacky-business-rules-2026-11-22.md',doc+'work/spec/market-compensation-rules.md']);
    }
    if(n===4){
      s=slide(n,'The proposed service workflow','Target workflow under demo-v1 and human-review-v1');
      const labels=['Understand\nthe complaint','Verify the\norder','Apply the\ndelay rule','Customer\nconfirms','Human\nreviews','Show actual\nstatus'];
      const owners=['MODEL','TRUSTED TOOL','PROGRAM','CUSTOMER','REVIEWER','SYSTEM'];
      const ns=labels.map((v,i)=>{text(s,owners[i],66+i*195,203,170,30,17,C.muted);return node(s,v,66+i*195,249,170,104,i===4?C.green:C.pale,25);});
      for(let i=0;i<5;i++)arrow(s,ns[i],ns[i+1]);
      text(s,'Missing facts or ineligible order',66,418,525,42,28,C.dark,true);
      text(s,'Explain the reason and offer an appropriate human-service route.',66,475,525,92,25);
      text(s,'Reconsideration after rejection',684,418,530,42,28,C.dark,true);
      text(s,'New verifiable facts or a prior error allow a human recheck of an uncompensated ticket.',684,475,530,92,25);
      text(s,'Same order, same history. One successful compensation per order.',66,609,1148,43,27,C.dark);
      notes(s,'The main path is the selected course workflow: verified facts, explicit eligibility, customer confirmation and human review. Reconsideration needs relevant verifiable new information or a prior processing error, a written human reason, and no prior successful compensation. Dissatisfaction alone is insufficient. New review guards are a confirmed specification awaiting implementation alignment and retesting. The static reference code also has an optional STP auto-approval path. The recorded configuration must confirm manual review for this selected demonstration.',[doc+'work/spec/human-review-boundaries.md',code+'examples/ord001/ord001_web_graphs.py']);
    }
    if(n===5){
      s=slide(n,'Data and compensation policy','The prototype uses simulated orders and simulated coupons');
      text(s,'Data used by the service',66,195,520,45,29,C.dark,true);
      table(s,[['Input','Purpose'],['Order ownership and status','Verify access and delivery'],['Expected / actual arrival','Calculate delay'],['Paid amount','Cap any coupon amount'],['Dialogue and ticket history','Preserve context and state']],66,253,540,[48,63,63,63,63],[285,255],22);
      text(s,'Delivered and more than 30 minutes late',675,195,535,96,34,C.dark,true);
      text(s,'Exactly 30 minutes does not qualify.',675,305,535,42,25);
      text(s,'10 yuan standard coupon',675,376,535,49,34,C.dark,true);
      text(s,'Customer confirmation and human approval are required. The paid amount caps every issue.',675,441,535,108,25);
      text(s,'If the standard amount exceeds payment, refer to the supervisor. Missing payment blocks issue.',66,596,1148,61,23,C.muted);
      notes(s,'demo-v1 requires a delivered order and a delay strictly greater than 30 minutes. The default simulated coupon is 10 yuan. human-review-v1 adds role and amount guards: R002 alone may change the amount to an integer from 1 to 20 yuan, never above trusted payment, with a reason. If the default exceeds payment, the system must not automatically reduce it. Missing or unverifiable payment, or no legal positive integer amount, blocks issue. Order facts enter through trusted tools. Public policy research supplies design context rather than customer training records. Static source shows model prompting with verified facts, not evidence of a training or fine-tuning pipeline.',[doc+'work/spec/human-review-policy.json',doc+'work/research/jacky-business-rules-2026-11-22.md',code+'examples/ord001/ord001_web_graphs.py']);
    }
    if(n===6){
      s=slide(n,'Model, tools and workflow control','Static architecture reference. New review guards still require validation.');
      const a=node(s,'Customer\nrequest',66,215,205,105,C.bg,25);
      const b=node(s,'Language model\nunderstands intent',367,215,240,105,C.pale,25);
      const c=node(s,'Trusted order tool\nchecks facts',671,215,240,105,C.green,25);
      const d=node(s,'Rule evaluation\nand confirmation',982,215,230,105,C.pale,24);
      arrow(s,a,b);arrow(s,b,c);arrow(s,c,d);
      const e=node(s,'Ticket store\nrecords state',982,395,230,105,C.green,25);
      const f=node(s,'Human review\nrecords a decision',671,395,240,105,C.green,25);
      const g=node(s,'Customer response\nuses actual state',367,395,240,105,C.bg,25);
      arrow(s,d,e,'bottom','top');arrow(s,e,f,'left','right');arrow(s,f,g,'left','right');
      text(s,'LangChain connects model and tools. LangGraph manages branches, state and human waits.',66,546,1148,64,25,C.dark);
      text(s,'Reported configuration: openai:deepseek-flash / live. Parameters and selection evidence: pending.',66,623,1148,40,21,C.muted);
      notes(s,'The source uses LangChain messages and a tool node, and LangGraph state graphs with interrupts for confirmation and review. This explains the architectural choice: language interpretation stays with the model while business calculations and persistent state remain explicit. The developer reported openai:deepseek-flash in live mode. Request parameters, returned model identity, resource/cost evidence and any actual alternative-model comparison remain missing. We do not claim RAG, fine-tuning or speech understanding. The optional STP path in reference code must not be silently treated as the selected manual-approval demo. human-review-v1 implementation guards await acceptance.',[code+'examples/ord001/ord001_web_graphs.py',code+'examples/ord001/ord001_web_service.py',doc+'notes/team/progress-2026-11-22.md']);
    }
    if(n===7){
      s=slide(n,'ORD001 demonstration','Planned recording sequence');
      const frame=s.shapes.add({geometry:'rect',name:'ORD001 recording placeholder',position:{left:66,top:200,width:790,height:394},fill:'#F4F5EF',line:{fill:C.line,width:2,style:'dashed'}});
      text(s,'ORD001 recording',126,324,670,50,36,C.muted);
      text(s,'[Add verified screen capture]',126,391,670,45,27,C.muted);
      const st=['1   Query ORD001','2   Confirm request','3   Show pending ticket','4   Reviewer approves','5   Display actual status'];
      st.forEach((v,i)=>text(s,v,899,222+i*69,315,48,25,C.ink));
      text(s,'Run version: ______    Model: ______    Recorded on: ______',66,624,1148,33,22,C.muted);
      notes(s,'The recording must follow the same order and ticket from lookup through confirmation, pending review, the human decision and the customer-visible result. The placeholder contains no runtime claim. Use the accepted version and configuration, including simulated orders/coupons and manual approval. Preserve the real state transitions and record the model and date with the capture. Customer entry: https://ord001-group24.surge.sh/ . Review entry: https://ord001-group24.surge.sh/review .',[doc+'work/presentation/ppt-framework.md',doc+'work/eval/developer-handoff.md']);
    }
    if(n===8){
      s=slide(n,'Reconsideration and human service','Confirmed policy. Demonstration and boundary retest evidence are pending.');
      s.shapes.add({geometry:'rect',name:'Reconsideration recording placeholder',position:{left:66,top:202,width:592,height:356},fill:'#F4F5EF',line:{fill:C.line,width:2,style:'dashed'}});
      text(s,'Original ticket and history',111,305,505,50,33,C.muted);
      text(s,'[Add verified screen capture]',111,376,505,45,26,C.muted);
      text(s,'Eligible for reconsideration',712,202,500,44,29,C.dark,true);
      text(s,'Rejected, with no coupon issued. Verifiable new facts or a prior error. A human records the reason.',712,258,500,126,25);
      text(s,'Amount authority',712,414,500,43,29,C.dark,true);
      text(s,'R002 supervisor only. Integer 1–20 yuan, within the paid amount, with a written reason.',712,470,500,107,25);
      text(s,'After issue: no reopening, top-up or second compensation. Repeat requests return the existing status.',66,604,1148,57,24,C.dark);
      notes(s,'R001 handles the standard amount, R002 may change the amount within the confirmed guards, and R003 is read-only. Customers and the AI cannot set an amount directly. Reconsideration reuses the original ticket and preserves the rejection history. Human judgement confirms relevant new evidence or an earlier processing error. Repeated dissatisfaction alone does not qualify. Every issue, including the standard amount, is capped by trusted payment. Deduplication applies across sessions and reviewers for the same order. Different orders remain independent. No new approval tier, post-issue top-up or real refund integration is included.',[doc+'work/spec/human-review-boundaries.md',doc+'work/eval/human-review-boundary-checks.md']);
    }
    if(n===9){
      s=slide(n,'Evaluation design','A matched comparison of business decision methods');
      table(s,[['Condition','Basic tool agent B','Explicit-rule agent C'],['Business decision','Model follows policy in the prompt','Program evaluates the policy'],['Shared capabilities','Tools, multi-turn dialogue, confirmation, tickets and human review','Tools, multi-turn dialogue, confirmation, tickets and human review']],66,201,1148,[52,70,115],[256,446,446],24);
      text(s,'Same model, authorized order facts, tools and execution guards',66,478,1148,45,29,C.dark,true);
      text(s,'Both modes use demo-v1 and human-review-v1. Log model proposals, safety blocks and actual actions separately.',66,535,1148,68,25);
      text(s,'Planned: 10 scenarios × 2 modes × 3 repeats = 60 system runs',66,621,1148,40,27,C.dark);
      notes(s,'The fair baseline B has tools, multiple turns, confirmation, tickets and human review. The old single-turn function is not the formal baseline. Only the business decision method changes between B and C. Order authorization, amount authority, deduplication and the other common execution guards remain identical. The 60 runs are planned system trials, not a count of model calls or completed measurements. Record actual model invocation per run, retain failures, and bind every record to the same code, model configuration and policy version.',[doc+'work/presentation/deck-plan.json',doc+'notes/current-plan.md',doc+'work/spec/human-review-policy.json']);
    }
    if(n===10){
      s=slide(n,'Internal evaluation results','Awaiting matched runs and version-bound retest evidence');
      table(s,[['Metric','B','C','Evidence'],['Correct handling (k/N)','','',''],['Unsafe proposals (k/N)','','',''],['Incorrect executed actions (k/N)','','',''],['Repeat consistency (k/G)','','',''],['System time (seconds)','','',''],['Model cost (currency/run)','','','']],66,194,1148,[42,39,39,39,39,39,39],[518,175,175,280],22);
      s.tables.items[0].cells.block({row:0,column:0,rowCount:7,columnCount:4}).assign({margins:{left:14,right:14,top:5,bottom:5}});
      text(s,'Targeted repair evidence',66,495,1148,38,26,C.dark,true);
      table(s,[['Area','Version','Retest result','Evidence'],['Review guards / handoff / order isolation','','','']],66,544,1148,[42,59],[518,175,175,280],22);
      notes(s,'All results are intentionally blank in this draft. Fill numerator and denominator from matched records, not old development experiments or team trial summaries. The November 22 summary of eight marked rows lacks exact runtime binding and does not establish compliance with the later human-review-v1 boundaries. Keep model suggestions, common safety-layer interventions and actual issued actions separate. Log latency, human wait and cost with consistent definitions. The repair summary can be split into rows once the underlying version-bound evidence arrives.',[doc+'work/eval/team-retest-2026-11-22.md',doc+'work/eval/human-review-boundary-checks.md',doc+'work/presentation/deck-plan.json']);
    }
    if(n===11){
      s=slide(n,'Comparison with market products','Evidence and comparison findings are pending');
      table(s,[['Service','Order selection','Eligibility explanation','Human service / status'],['Meituan','','',''],['Taobao Instant Commerce','','',''],['JD Food Delivery','','',''],['Our prototype','','','']],66,202,1148,[66,78,78,78,78],[280,260,300,308],24);
      text(s,'Each finding needs an evidence type, observation date and order conditions.',66,607,1148,43,25,C.dark);
      notes(s,'This table intentionally leaves all comparison outcomes blank. Separate official material, third-party cases, member observations and actual prototype runs. Only compare like-for-like evidence. A missing order or inaccessible flow is unobserved, not a failed capability. Do not infer real compensation, speed or broad superiority from a no-order consultation. Jacky’s rule summary supports the background page but does not replace Lin’s workflow evidence.',[doc+'work/research/market-comparison.md',doc+'work/spec/competitor-evidence.md',doc+'work/presentation/material-checklist.md']);
    }
    if(n===12){
      s=slide(n,'Business value and cost','Value hypotheses to test, with numerical inputs left blank');
      text(s,'Primary business outcome',66,197,500,45,29,C.dark,true);
      text(s,'Correct handling and safe actions in complex complaints.',66,256,500,90,29);
      text(s,'Supporting outcomes',66,382,500,45,29,C.dark,true);
      text(s,'Less repeated explanation.\nMore complete human handoffs.\nLower handling effort.',66,444,500,128,25);
      table(s,[['12-month inputs','Value / source'],['Attributed savings and benefits',''],['Model and service operation cost',''],['Human review and maintenance',''],['One-time setup and integration','']],619,204,595,[49,69,69,69,69],[376,219],22);
      text(s,'12-month ROI =',66,609,244,46,25,C.dark);
      text(s,'Benefits − operating costs − setup cost',344,589,820,31,23,C.dark);
      line(s,344,630,820,C.dark);
      text(s,'Operating costs + setup cost',344,637,820,30,23,C.dark);
      notes(s,'The business value remains a hypothesis until measured. Define the comparison period and attributable baseline. Benefits can include avoided handling time or supported incremental value, without double counting. Include model usage, service costs, review, maintenance and implementation. Free token resources do not imply zero long-run cost. The displayed 12-month ROI uses total incremental cost over that period, including one-time setup, as its denominator. The same cost set is subtracted in the numerator. All quantities must be supported before calculating. Record system time separately from human waiting time.',[doc+'work/presentation/deck-plan.json',doc+'work/presentation/material-checklist.md']);
    }
    if(n===13){
      s=slide(n,'Limitations and next steps');
      text(s,'Current scope',66,196,485,45,31,C.dark,true);
      text(s,'Simulated orders and coupons\n\nLimited complaint scenarios\n\nNew review guards await acceptance\n\nNo measured market or ROI conclusion',66,263,495,300,28);
      text(s,'Next evidence to complete',664,196,550,45,31,C.dark,true);
      const acts=['1   Freeze the code, model and policy versions','2   Retest the affected boundaries and record demos','3   Run the matched B/C comparison','4   Complete market evidence and cost inputs'];
      acts.forEach((v,i)=>text(s,v,664,264+i*83,550,67,26));
      line(s,66,610,1148);
      text(s,'Later application: e-commerce after-sales support, with new interfaces, policies and validation.',66,631,1148,34,23,C.muted);
      notes(s,'The next work closes the existing demonstration and evidence gaps. It does not expand this batch into a payment integration or a full delivery app. A later pilot would need trusted business interfaces, identity and permission controls, authoritative policies, broader failure cases and continued quality/cost monitoring. Transfer to another business domain needs new rules and validation. Do not conclude deployment readiness from one successful demonstration.',[doc+'notes/current-plan.md',doc+'work/presentation/deck-plan.json']);
    }
    if(n===14){
      s=slide(n,'Evaluation definitions and case evidence','Appendix A');
      table(s,[['Measure','Definition','Evidence to retain'],['Correct handling','Runs meeting the expected outcome / all scored runs','Input, expected result, final state'],['Unsafe proposals','Runs with a disallowed model proposal / all scored runs','Raw output and proposed tool action'],['Executed errors','Runs with an incorrect actual action / all scored runs','Tool log, ticket and issue record'],['Repeat consistency','Scenario-mode groups with 3 matching outcomes / completed groups','All repeats, including failures'],['Time and cost','System time per run. Human wait and billed usage recorded separately.','Timestamps, tokens, price source']],66,193,1148,[47,70,70,70,78,79],[240,493,415],22);
      text(s,'Run ID: ______    Code / model / policy: ______    Raw evidence: ______',66,629,1148,34,22,C.muted);
      notes(s,'N is the number of scored runs for each mode. G is the number of completed scenario-mode groups with the planned three repeats. Do not discard failed runs. Stable wrong answers can be consistent, so consistency must be read with correctness. Freeze the outcome scoring rule before running the formal comparison. Unsafe proposals and executed errors use different evidence and must not be merged. Time boundaries and cost units must match across modes. These definitions specify how to fill the result table and are not measured results.',[doc+'work/presentation/deck-plan.json',doc+'work/spec/human-review-policy.json']);
    }
    if(n===15){
      s=slide(n,'Sources, contributions and AI assistance','Appendix B');
      text(s,'Source register',66,190,460,43,29,C.dark,true);
      text(s,'Jacky’s business and policy research\n22 Nov 2026\n\nConfirmed demo and human-review rules\n23 Nov 2026\n\nPrototype source and teacher template\nLinks and locators in speaker notes',66,252,478,266,24);
      text(s,'Official platform source locators: [pending]',66,559,478,54,21,C.muted);
      table(s,[['Work received','Contributor identity'],['Business and rule material','Jacky [official name / ID]'],['Prototype code','Developer [official name / ID]'],['Trial feedback','A + gaga [official names / IDs]'],['Earlier market observations','Lin [official name / ID]'],['Project synthesis and slides','[official name / ID]']],593,196,621,[48,59,59,69,68,59],[319,302],21);
      text(s,'I used OpenAI Codex to assist with this assignment.',66,633,1148,33,23,C.muted);
      notes(s,'The table describes material received rather than certifying final contribution shares or assigning speakers. Formal English names, IDs and contribution wording require the team’s confirmation. Earlier market observations remain distinct from the pending current comparison. Teacher source: IS5542 Project Template.pptx, pages 2 and 5–8, supplied course file. The template permits the team’s own visual design and gives 2/7/4/2 minute structure guidance. It does not establish the current video cap. Research and implementation source links are below. Project system model information is on slide 6 and is separate from the production-assistance declaration.',[doc+'work/research/jacky-business-rules-2026-11-22.md',doc+'work/spec/human-review-boundaries.md',code+'examples/ord001/ord001_web_graphs.py',doc+'notes/team/progress-2026-11-22.md',doc+'notes/任务说明.md']);
    }
  }
  return {slideCount:presentation.slides.items.length,added:[input.from,input.to]};
}
