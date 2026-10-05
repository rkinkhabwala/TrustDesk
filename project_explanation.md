Think of TrustDesk as a **very careful new assistant** who has read every one of your company's rulebooks and helps fill out long security forms. Its one strict rule: it never claims anything it can't point to in writing.

## The problem it solves

Imagine a small software company is about to sign a big bank as a customer. Before the bank signs, its security team sends a spreadsheet with **hundreds of questions**:

- "Do your employees use two-step login?"
- "Is our data encrypted?"
- "How fast will you tell us if you get hacked?"

The answers are scattered across the company's internal rulebooks (security policies) and old forms they filled out for other customers. Someone has to dig through all of it, which takes **days**, while the deal waits. And the same questions come back from every new customer, just worded differently.

Why not just ask ChatGPT? Because those rulebooks describe exactly how the company protects itself. Uploading them to an outside AI service is the kind of thing security teams don't allow.

## What TrustDesk does

**1. It reads your rulebooks once.** You give it your company's policies and old answered forms. It organizes them so it can quickly find the right paragraph for any question, a bit like a librarian making an index.

**2. You hand it the customer's form.** It works through the spreadsheet one question at a time.

**3. For each question, it finds the relevant pages and writes a draft answer.** For example:

> **Q:** Do you let customers bring their own encryption keys?
> **A:** No. *"We do not currently support customer-managed encryption keys."*, from the Encryption Policy

Every answer comes with **the exact sentence from your rulebook** it's based on, like a student who has to show their work.

**4. When the rulebooks don't cover something, it says so.** If the bank asks "Do you have cyber insurance?" and nothing in your documents mentions it, TrustDesk doesn't guess. It marks the question **"Needs review"** so a person can answer it.

**5. A person reviews, fixes and approves.** Answers come color-coded:
- 🟢 **Green:** clearly backed by your policies
- 🟡 **Yellow:** partly backed, or based only on an old form, so worth a second look
- 🔴 **Red:** needs a human

You approve or edit, then download the completed spreadsheet to send back.

**6. It gets smarter over time.** Every answer you approve is saved, so the next customer's form goes faster.

## Why "I don't know" is the most important feature

When you tell a customer's security team "Yes, we do that" and it isn't true, that's not a small mistake. It can kill a deal or create legal trouble later. So TrustDesk has a built-in fact-checker that isn't AI at all, just simple, strict rules:

- If the AI quotes a sentence, the fact-checker confirms that sentence **really exists** in your documents, word for word.
- If the quote is made up, or there's no quote at all, the answer is automatically sent to a human.

Even if the AI wants to bluff, it can't get a bluff past the checker.

## Why it runs on your laptop

The AI runs entirely on your own computer, using free open models. Your security policies, which are some of the most sensitive documents a company has, never get uploaded anywhere.

**In one line:** TrustDesk fills out customer security forms by finding the right sentence in your own company rulebooks, shows its proof for every answer, admits when it doesn't know, and keeps everything on your own computer.