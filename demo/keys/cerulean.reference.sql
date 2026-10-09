-- Identity
SELECT community_id FROM directory__communities WHERE name = :community_name;

-- Answer
WITH paid AS (
  SELECT invoice_id, SUM(amount_cents) AS paid_cents
  FROM accounting__payments GROUP BY invoice_id
)
SELECT i.invoice_id, i.vendor_id, v.name AS vendor_name,
       i.total_cents - COALESCE(paid.paid_cents, 0) AS outstanding_cents
FROM accounting__invoices AS i
LEFT JOIN paid ON paid.invoice_id = i.invoice_id
JOIN directory__vendors AS v
  ON v.community_id = i.community_id AND v.vendor_id = i.vendor_id
WHERE i.community_id = :community_id AND i.status <> 'V'
  AND i.total_cents - COALESCE(paid.paid_cents, 0) > 0
ORDER BY i.invoice_id;
