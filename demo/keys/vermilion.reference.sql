-- Identity
SELECT t.account_id, t.traveler_id
FROM clients__travelers AS t
JOIN clients__accounts AS a ON a.account_id = t.account_id
WHERE a.name = :account_name AND t.name = :traveler_name;

-- Answer
SELECT r.reservation_id, r.account_id, r.traveler_id,
       t.name AS traveler_name, r.depart_date
FROM bookings__reservations AS r
JOIN clients__travelers AS t
  ON t.account_id = r.account_id AND t.traveler_id = r.traveler_id
WHERE r.account_id = :account_id AND r.traveler_id = :traveler_id
  AND r.status = 'C' AND r.depart_date > :after_date
ORDER BY r.depart_date, r.reservation_id;
