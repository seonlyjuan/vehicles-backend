from app.core.security.rate_limiting import RatePolicy, authenticated_rate_limit

READ = RatePolicy("profiles:read", 120, 60)
UPDATE = RatePolicy("profiles:update", 10, 60 * 60)
EXPORT = RatePolicy("profiles:export", 5, 24 * 60 * 60)
DELETE = RatePolicy("profiles:delete", 3, 24 * 60 * 60)

read_limited_user = authenticated_rate_limit(READ)
update_limited_user = authenticated_rate_limit(UPDATE)
export_limited_user = authenticated_rate_limit(EXPORT)
delete_limited_user = authenticated_rate_limit(DELETE)
