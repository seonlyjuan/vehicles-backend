from app.core.security.rate_limiting import RatePolicy, authenticated_rate_limit

READ = RatePolicy("legal:read", 30, 60)

read_limited_user = authenticated_rate_limit(READ)
