-- Fraser Institute school ratings for GTA neighbourhoods.
-- Run AFTER 004_enrichment.sql (which creates the schools table).

TRUNCATE TABLE schools RESTART IDENTITY;

INSERT INTO schools (name, fraser_rating, city, lat, lng, keywords) VALUES
  ('Maurice Cody PS', 8.4, 'Toronto', 43.7018, -79.3862, ARRAY['davisville','balliol','merton','soudan']),
  ('Hodgson MS', 8.1, 'Toronto', 43.6987, -79.3855, ARRAY['mount pleasant','broadway','belsize']),
  ('Bessborough Dr PS', 8.6, 'Toronto', 43.7086, -79.3667, ARRAY['leaside','bessborough','moore','bayview']),
  ('Keele St PS', 8.3, 'Toronto', 43.6655, -79.4655, ARRAY['high park','glenlake','indian road']),
  ('Swansea PS', 8.0, 'Toronto', 43.6478, -79.4842, ARRAY['swansea','windermere','clendenan']),
  ('Fern Ave PS', 7.8, 'Toronto', 43.6440, -79.4497, ARRAY['roncesvalles','sorauren','fermanagh']),
  ('Withrow Ave PS', 7.6, 'Toronto', 43.6694, -79.3494, ARRAY['riverdale','broadview','withrow','langley']),
  ('Duke of Connaught PS', 7.4, 'Toronto', 43.6690, -79.3235, ARRAY['greenwood','coxwell','dingwall','fulton']),
  ('Lambton-Kingsway JMS', 8.7, 'Etobicoke', 43.6520, -79.5150, ARRAY['kingsway','montgomery','humbertown']),
  ('John English JMS', 7.8, 'Etobicoke', 43.6155, -79.4990, ARRAY['mimico','lakeshore blvd','royal york']),
  ('Islington JMS', 8.2, 'Etobicoke', 43.6450, -79.5240, ARRAY['islington','burnhamthorpe']),
  ('Park Lawn JMS', 8.5, 'Etobicoke', 43.6220, -79.4880, ARRAY['sunnylea','park lawn','berry rd']),
  ('Lorne Park PS', 8.9, 'Mississauga', 43.5230, -79.6300, ARRAY['lorne park','indian rd','watersedge']),
  ('Riverside PS', 8.3, 'Mississauga', 43.5560, -79.5820, ARRAY['port credit','mineola','high st']),
  ('Vista Heights PS', 8.1, 'Mississauga', 43.5820, -79.7020, ARRAY['streetsville','queen st s','britannia']),
  ('Credit Valley PS', 8.4, 'Mississauga', 43.5490, -79.7150, ARRAY['erin mills','credit valley','sawmill']),
  ('Hillcrest PS', 8.0, 'Mississauga', 43.5140, -79.6180, ARRAY['clarkson','southdown','meadowwood']),
  ('New Central PS', 8.7, 'Oakville', 43.4470, -79.6680, ARRAY['old oakville','reynolds','trafalgar']),
  ('Abbey Park HS', 8.6, 'Oakville', 43.4280, -79.7180, ARRAY['glen abbey','abbey','pilgrims']),
  ('Bronte Creek PS', 8.4, 'Oakville', 43.4020, -79.7150, ARRAY['bronte','lakeshore w','jones']),
  ('Joshua Creek PS', 8.8, 'Oakville', 43.4650, -79.6720, ARRAY['joshua creek','grand oak','river oaks']),
  ('Pleasantville PS', 8.8, 'Richmond Hill', 43.8720, -79.4380, ARRAY['mill pond','trench','mill st']),
  ('Bayview Hill ES', 9.0, 'Richmond Hill', 43.8560, -79.4020, ARRAY['bayview hill','sixteenth']),
  ('Oak Ridges PS', 8.3, 'Richmond Hill', 43.9450, -79.4560, ARRAY['oak ridges','north lake','bond lake']),
  ('Beynon Fields PS', 8.6, 'Richmond Hill', 43.9280, -79.4420, ARRAY['jefferson','gamble','shaftsbury']);