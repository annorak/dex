SELECT i.invoice_id, i.vendor_id, v.name AS vendor_name,
       i.balance_cents AS outstanding_cents, 'USD' AS currency
FROM invoices AS i
JOIN vendors AS v ON v.vendor_id = i.vendor_id
WHERE i.community_id = :community_id AND i.status = 'O' AND i.balance_cents > 0
ORDER BY i.invoice_id;
