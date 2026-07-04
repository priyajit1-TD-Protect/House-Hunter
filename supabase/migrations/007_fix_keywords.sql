-- Fix neighbourhood keyword false-matches.
-- Generic directional/common words ('east', 'jones', etc.) caused Toronto
-- addresses like 'Willowdale East' to mis-match to 'Oakville - Bronte'.
-- Remove the dangerous keywords so only distinctive area names remain.

UPDATE neighbourhoods
SET keywords = ARRAY['bronte', 'lakeshore w']
WHERE name = 'Oakville - Bronte';

-- Also tighten any other rows that used overly generic tokens.
UPDATE neighbourhoods
SET keywords = ARRAY['port credit', 'mineola']
WHERE name = 'Mississauga - Port Credit';

UPDATE neighbourhoods
SET keywords = ARRAY['long branch', 'lake promenade']
WHERE name = 'Etobicoke - Long Branch';

UPDATE neighbourhoods
SET keywords = ARRAY['oak ridges', 'north lake', 'bond lake']
WHERE name = 'Richmond Hill - Oak Ridges';
