from app.core.security.rate_limiting import RatePolicy, authenticated_rate_limit

READ = RatePolicy("messages:read", 120, 60)
START = RatePolicy("messages:start", 10, 60 * 60)
SEND = RatePolicy("messages:send", 30, 60)


read_limited_user = authenticated_rate_limit(READ)
start_limited_user = authenticated_rate_limit(START)
send_limited_user = authenticated_rate_limit(SEND)
