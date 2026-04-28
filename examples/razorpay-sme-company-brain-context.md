# Razorpay Super App — Context Brief

**Source:** Personal experience of a small D2C brand founder (Once Upon Me).
**Decision under consideration:** Should Razorpay build a company brain for SMEs that powers AI agents across finance, compliance, CRM, growth, and operations?

---

## The founder's journey (lived experience)

When someone starts a business and begins selling something, the first thing they need is payments. Razorpay is usually the first go-to step for that.

But once they start receiving payments, they also need to:

- issue invoices
- issue receipts
- manage compliance
- file GST
- handle multiple things around invoicing and accounting

That is what I thought the Razorpay Invoices product would do, but apparently, that is not what it does. It helps you create invoices, but it does not cover the full accounting and compliance layer.

**That is where Razorpay loses a client.**

That is when I shifted to Zoho, and I have been using Zoho Books since then. Once we started acquiring more customers, I started using Zoho Books for accounting and issuing invoices to customers.

Zoho now has my data. It has my accounting data.

The next thing I needed was some sort of CRM. When you start looking for a CRM, Zoho has Zoho CRM. Zoho also keeps pitching its payment product, which helps businesses move away from Razorpay.

At this point, Zoho has a lot of my data. Razorpay only gives me the transaction. I just map the Razorpay payment ID with customers in my database or Zoho database.

**That makes Razorpay very replaceable.**

I can shift from one payment aggregator to another — maybe Paytm, maybe Zoho Payments, or maybe someone who gives me a lower rate.

---

## The thesis

The first stop for any new business is Razorpay. In the agent-tech era, Razorpay is in the best position to go much deeper.

Since the first payments happen on Razorpay, it can start helping businesses maintain customer data as well. If Razorpay can provide every business with a **brain — a contextual graph or knowledge graph** of that business — it can become the operating layer for accounting, growth, marketing, CRM, and more.

That is how it can become a super app.

It can start with basic things like accounting and CRM. But it does not have to look like traditional software in this era.

**What does an accounting product look like when AI agents are doing most of the work?**

Earlier, tools like Zoho Books were built for people and accountants to manually enter data. Now, AI agents can enter and manage that data. That means the product can be reimagined from the ground up.

You can have an AI accountant that does most of the accounting work.

---

## Proposed architecture

- **Core layer:** a business knowledge graph (the "company brain")
- **Tool layer:** accounting, CRM, compliance, marketing, ops — built on top of the graph
- **Agent layer:** AI agents that operate the tools
  - Accounting agent
  - CRM agent
  - Data entry agent
  - Growth / marketing agent
  - Customer support agent

Businesses may be allowed to choose the model they want to use. Or Razorpay could simply provide the smartest model available for each function.

---

## Why now

In this era, it may be easier for Razorpay to become a super app and challenge legacy businesses like Zoho. Legacy SaaS was built for human data entry; agent-native products start from a different premise.

**Razorpay is probably one of the most equipped companies today to become the business brain for small businesses** — because it owns the very first transaction and the trust that comes with it.

---

## Key signals embedded in this context

- Razorpay's current product (Invoices) stops at invoice generation; does not cover accounting + compliance.
- Customers churn from Razorpay's surface area to Zoho once they need books + GST.
- Zoho cross-sells its own payments product back into the customer, threatening Razorpay's core.
- Razorpay's payments-only position makes it commoditizable on rate.
- The founder's own journey: Razorpay → Zoho Books → Zoho CRM → potentially Zoho Payments.
- Agent-era reframe: products built for human data entry can be rebuilt for agent-native operation.

---

## Scope restrictions for this run

- **Do NOT query the user's personal wiki** (no `wiki-query`, no OnceUponMe business context lookup) for this decision. This is a strategic decision about Razorpay, not about Once Upon Me operations. Ground only via web search and the content of this context file.
