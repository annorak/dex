# dex

dex is where oak, the agent, learns how a company handles a routine office task. oak tests itself against past work and proposes each new case for a person to approve. This folder holds the app for the first task: paying vendor invoices at HOA management companies.

## What is AI and what is code

oak works each case in ten steps. Two of the steps are AI calls: reading the invoice email and drafting the approval email. The rest are ordinary code, and so is the pattern finder that turns replay misses into questions.

In the demo, the two AI steps use pre-written answers, and no model is called. With your own files, oak reads invoices from your spreadsheet columns and fills the email from a template. Only two buttons call Claude: Read an email with oak, and Rewrite with oak.
