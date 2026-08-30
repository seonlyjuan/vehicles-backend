from app.core.security.rate_limiting import RatePolicy, authenticated_rate_limit

READ = RatePolicy("safety:read", 60, 60)
BLOCK = RatePolicy("safety:block", 20, 60 * 60)
REPORT = RatePolicy("safety:report", 10, 60 * 60)

read_limited_user = authenticated_rate_limit(READ)
block_limited_user = authenticated_rate_limit(BLOCK)
report_limited_user = authenticated_rate_limit(REPORT)

