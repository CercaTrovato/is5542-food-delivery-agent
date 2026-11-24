# IS5542 Group 24 · v4 English Recording Script



## Slide 01 · Food Delivery Complaint Assistant


Hello everyone. We are Group 24, and our project is a Food Delivery Complaint Assistant.

We focus on a practical question: how can an assistant handle a delivery complaint correctly, explain its decision, and help the customer continue when human review is needed? Our course prototype connects conversation, verified order facts, business rules, and human approval. It uses simulated orders and coupons.

I’ll introduce the workflow, show two recorded demonstrations, and then discuss our evaluation and business-value analysis.



## Slide 02 · The anatomy of a complaint


A customer asks, ‘My order is late. Can I claim compensation?’ That sounds simple, but the system first needs to identify the order and the guarantee that applies to it.

The customer needs a clear explanation and a useful next step. The system needs ownership, delivery times, payment, and previous ticket history. A human reviewer also needs the earlier conversation, especially when the customer disputes a decision.

If those facts or that context are lost, even a fluent answer can leave the complaint unresolved. Our workflow keeps the information attached to the same order as responsibility moves between the assistant and the reviewer.



## Slide 03 · Different guarantees, different conditions


Our research shows why identifying the guarantee matters. Meituan’s standard and Black Gold benefits are separate. Taobao also distinguishes merchant-gifted cover from services purchased by the customer.

JD’s on-time coupon guarantee depends on the order label and the latest estimated arrival time. We keep it separate from the historical free-order promotion.

The business principle is to check the order’s entitlement before explaining eligibility. For our prototype, we use one clearly defined demonstration policy, which I’ll explain shortly. This gives us a stable rule to implement and test, while keeping the platform-specific guarantees separate.



## Slide 04 · Complaint handling workflow


The workflow has six steps. The model understands the complaint, and a trusted tool verifies order ownership and facts. The program then evaluates the delay rule. If an application is appropriate, the customer confirms submission before a ticket enters human review. The final reply reads the stored ticket status.

When facts are missing or a decision is disputed, the handoff preserves the order and conversation. A rejected ticket with no compensation issued can be reconsidered if there is verifiable new information or an earlier processing error. The reviewer records the reason and reuses the original ticket.

This makes the customer’s request, the reviewer’s decision, and the system’s actual state traceable through one process.



## Slide 05 · Verified data before compensation


Each trusted field has a specific job. Ownership controls access. Expected and actual delivery times determine the delay. The paid amount sets a compensation ceiling, while ticket and dialogue history preserve context.

Our demo policy requires a delivered order and a delay strictly greater than thirty minutes. Exactly thirty minutes does not qualify. The standard amount is a ten-yuan simulated coupon, issued only after customer confirmation and human approval.

A supervisor can approve an integer amount from one to twenty yuan, within the paid-amount cap. Each order can receive compensation successfully once. These checks control what the system can actually issue.



## Slide 06 · A controlled agent architecture


LangChain connects the language model to tools. LangGraph manages the branches, stored state, and pauses for customer or human input. The model interprets the request and explains the outcome; order tools provide authorized facts, and program rules constrain the action.

We chose this separation because conversation benefits from flexible language understanding, while timing, permission, and payment limits need consistent checks.

The recordings use DeepSeek Flash. The formal comparison uses GPT-5.6 Sol with the same configuration for both modes. C also includes intent handling, order-number fallback, and food-safety preprocessing. The evaluation therefore compares two configured systems, rather than isolating the effect of one rule node.



## Slide 07 · ORD001: confirmation to approval


[Before playback — cue only]


Let’s follow the normal journey. Order O-R-D zero zero one was fifty minutes late, with fifty-eight yuan paid. The recording follows one order and one ticket.


[During playback — cue only]


The assistant checks the order. The customer confirms the request, creating pending ticket T zero zero zero one. A human reviewer approves ten yuan, and the customer then sees the issued simulated coupon.


[After playback — cue only]


The final message reflects the stored approval, so a proposed amount is not confused with an issued coupon.



## Slide 08 · ORD008: reconsideration on the same ticket


[Before playback — cue only]


The second recording shows a disputed decision. Order O-R-D zero zero eight was thirty-one minutes late, with thirty-six yuan paid. The first application was rejected, and no coupon was issued.


[During playback — cue only]


The customer continues through handoff H zero zero zero one. Verifiable new information is provided for review. Supervisor R zero zero two records the reconsideration reason and approves fifteen yuan. The original ticket, T zero zero zero one, is retained, and the customer sees the updated result.


[After playback — cue only]


The important step is a reasoned review of the existing case, with the same payment ceiling and one-compensation limit.



## Slide 09 · Two systems, one shared test set


For the formal evaluation, we used twenty synthetic cases, two modes, and three repeats per case: one hundred and twenty system trials in total. Both modes share the model configuration, authorized facts, tools, customer confirmation, and execution protections.

B reasons over the policy using tool results. C adds explicit rules together with the intent and fallback logic described earlier.

After the runs, we reviewed complete handling using three dimensions: the explanation and next step, agreement between intent and action, and authority and promises. A trial passes only when all three pass. This lets us examine what the customer actually receives, beyond the final ticket-state label.



## Slide 10 · Complete-handling outcomes


Each mode has sixty trials. B passed thirty-seven and failed twenty-three. C passed forty-five, failed six, and has nine trials pending a policy decision. The confirmed pass shares are sixty-one point seven percent and seventy-five percent, using all sixty trials as the denominator.

The pending C responses concern an extra three-yuan goodwill offer whose scope remains undecided. We keep those trials visible rather than counting them as passes.

Both systems matched the expected ticket state in all sixty trials. Yet the fuller review found missing explanations, unwanted confirmation cards, and unsupported promises. A correct database state alone does not establish correct complaint handling.

Average system processing time was about three point six seconds for B and three point three for C. Estimated model cost per scored case was approximately zero point seven three US cents for B and zero point eight seven cents for C.



## Slide 11 · Market comparison


The market comparison looks at order context, eligibility explanations, and human-service or status entries. It uses team observations from November eleventh, together with public terms and our prototype records.

The Meituan and JD samples involved old completed orders. The Taobao order arrived six minutes early. Those conditions matter when interpreting the replies.

The platforms already show order information and service entries. Our prototype focuses on making the connection between verified facts, an explicit rule, customer consent, and the resulting ticket easy to trace. The table compares observed workflows; the different order conditions do not support a ranking of compensation success.



## Slide 12 · Runtime costs and break-even scenario


On the left are observed or reported costs. The formal GPT evaluation used two hundred and fifty-nine model requests, including setup. The token-price estimate was about one US dollar and six cents. The developer estimated one to five yuan for DeepSeek development and demonstrations. Hosting used an existing laptop and free services, with no new cash spend reported for the prototype.

On the right, we ask what labor saving would cover the costs. The illustrative monthly scenario assumes one thousand comparable cases, one hundred US dollars of fixed incremental cost, and a wage reference of twenty-one dollars and fifty-three cents per hour. Model cost per full path is about one point seven seven US cents, calculated from six simulated paths.

Under these inputs, each case would need to save nineteen point seven net human seconds to break even. That is a required threshold, not a measured saving. The next measurement must include review, correction, and rework. Local supplier quotations can help replace the wage assumption once service coverage and billing units are aligned.



## Slide 13 · Priorities from the evaluation


Our next steps come directly from the observed failures. B had fourteen false blocks triggered by amount mentions, six unclear continuation paths, and three unwanted confirmation cards. These need clearer explanations and better agreement between the customer’s intent and the interface action.

C made six unsupported reminder or message-relay promises. Those promises need to match an actual action, or be removed. The nine goodwill cases also require a policy decision before the affected paths are retested.

A later pilot should measure human usability, real-payment behavior, and local labor time and cost. These are the inputs needed to move from a working course prototype toward an operational service.



## Slide 14 · Evaluation definitions


This appendix records the definitions behind the results. Complete handling requires all three review dimensions to pass. Policy-pending trials stay in the denominator. A complete pass in all three repeats is reported separately from ticket-state agreement.



## Slide 15 · Sources and team contributions


Our sources and contributions are listed here, together with the customer and review-console links.

To conclude, the prototype makes complaint decisions traceable from order facts through customer confirmation and human review. The evaluation identifies the specific behaviors and policy questions we need to improve next. Thank you.
